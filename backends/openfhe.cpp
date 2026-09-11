#include "openfhe.h"
#include "backend_interface.h"
#include "attack_mode.h"
#include "constants-defs.h"
#include "metrics.h"
#include "args.h"
using namespace lbcrypto;

struct OpenFHEContext final : BackendContext {
    CryptoContext<DCRTPoly> cc;
    KeyPair<DCRTPoly> keys;
    std::vector<double> baseInput;
    std::vector<double> goldenOutput;
    PRNG* prng;
};
std::vector<double> get_reference_output(const BackendContext* bctx)
{
    auto& ctx = static_cast<const OpenFHEContext&>(*bctx);
    return ctx.goldenOutput;
}

static void bitFlip(Ciphertext<DCRTPoly> &c, bool withNTT, size_t k, size_t i, size_t j, size_t bit){
    if(!withNTT)
        c->GetElements()[k].SwitchFormat();

    NativeInteger& x = c->GetElements()[k].GetAllElements()[i][j];
    uint64_t val = x.ConvertToInt();  // Extrae como uint64_t
    val ^= (1ULL << bit);               // Aplica XOR
    x = NativeInteger(val);

    if(!withNTT)
        c->GetElements()[k].SwitchFormat();
}



void backend_prepare_args(CampaignArgs& args){
    args.library = "openfhe";
}

SecretKeyAttackMode to_openfhe_attack_mode(AttackModeSKA mode)
{
    using OF = SecretKeyAttackMode;
    switch (mode) {
        case AttackModeSKA::Disabled:
            return OF::Disabled;
        case AttackModeSKA::CompleteInjection:
            return OF::CompleteInjection;
        case AttackModeSKA::RealOnly:
            return OF::RealOnly;
        case AttackModeSKA::ImaginaryOnly:
            return OF::ImaginaryOnly;
    }
    throw std::logic_error("Invalid AttackModeSKA");
}

std::string toLower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c){ return std::tolower(c); });
    return s;
}

ScalingTechnique toScalingTechnique(const std::string& s) {
    std::string key = toLower(s);

    if (key == "fixedauto") return ScalingTechnique::FIXEDAUTO;
    if (key == "fixedmanual") return ScalingTechnique::FIXEDMANUAL;
    if (key == "flexibleauto") return ScalingTechnique::FLEXIBLEAUTO;
    if (key == "flexibleautoext") return ScalingTechnique::FLEXIBLEAUTOEXT;

    throw std::invalid_argument("Unknown scaling technique: " + s);
}

BackendContext* setup_campaign(const CampaignArgs& args)
{

    if (args.openfhe_attack_mode || args.openfhe_threshold_bits)
    {
        auto attackModeOF =
            args.openfhe_attack_mode
                ? to_openfhe_attack_mode(*args.openfhe_attack_mode)
                : SecretKeyAttackMode::CompleteInjection;

        double threshold = args.openfhe_threshold_bits.value_or(5.0);

        auto cfg = SDCConfigHelper::MakeConfig(
            false, // Disable execption
            attackModeOF,
            threshold
        );

        SDCConfigHelper::SetGlobalConfig(cfg);
    }
    CCParams<CryptoContextCKKSRNS> params;
    params.SetMultiplicativeDepth(args.mult_depth);
    params.SetScalingModSize(args.logDelta);
    params.SetFirstModSize(args.logQ);
    params.SetBatchSize(1 << args.logSlots);
    params.SetRingDim(1 << args.logN);
    params.SetScalingTechnique(toScalingTechnique(args.scaleTech));

    params.SetSecurityLevel(HEStd_NotSet);
    auto* ctx = new OpenFHEContext();

    ctx->prng = &lbcrypto::PseudoRandomNumberGenerator::GetPRNG();
    ctx->prng->SetSeed(args.seed);
    ctx->cc = GenCryptoContext(params);
    ctx->cc->Enable(PKE);
    ctx->cc->Enable(KEYSWITCH);
    ctx->cc->Enable(LEVELEDSHE);

    ctx->keys = ctx->cc->KeyGen();
    if(args.doMul)
        ctx->cc->EvalMultKeyGen(ctx->keys.secretKey);

    if(args.doRot>0){
        int32_t rotIndex = static_cast<int32_t>(1ULL << (args.doRot - 1));
        ctx->cc->EvalAtIndexKeyGen(ctx->keys.secretKey, {rotIndex});
    }

    compute_plain_io(args, ctx->baseInput, ctx->goldenOutput);

    return ctx;
}

void destroy_campaign(BackendContext* ctx) {
    delete ctx;
}
   static int count_diff(const DCRTPoly& a, const DCRTPoly& b) {
       const auto& ta = a.GetAllElements();
       const auto& tb = b.GetAllElements();
       int n = 0;
       for (size_t i = 0; i < ta.size(); ++i)
           for (size_t j = 0; j < ta[i].GetLength(); ++j)
               n += (ta[i][j] != tb[i][j]);
       return n;
   }

   static void inject(DCRTPoly& p, bool withNTT, Injector& inj) {
       const Format orig = p.GetFormat();
       p.SetFormat(withNTT ? Format::EVALUATION : Format::COEFFICIENT);
       auto& towers = p.GetAllElements();

       if (inj.probing()) {
           uint32_t qbits = 0;
           for (const auto& t : towers) qbits = std::max<uint32_t>(qbits, t.GetModulus().GetMSB());
           inj.record_probe(uint32_t(towers.size()), qbits);
       } else {
           const FaultSpec& f = inj.spec();
           const DCRTPoly before = p;
           auto& t = towers.at(f.limb);
           if (f.coeff >= t.GetLength()) throw std::out_of_range("coeff fuera de rango");
           const uint64_t a = t[f.coeff].ConvertToInt();
           const uint64_t b = a ^ inj.mask64();
           t[f.coeff] = NativeInteger(b);
           inj.record_flip(__builtin_popcountll(a ^ b), count_diff(before, p));
       }
       p.SetFormat(orig);
   }

IterationResult run_iteration(BackendContext* bctx,
              const CampaignArgs& args,Injector& inj)
{
    auto& ctx = static_cast<OpenFHEContext&>(*bctx);

    ctx.prng->ResetToSeed();
    Plaintext result_bitFlip;
    Plaintext ptxt = ctx.cc->MakeCKKSPackedPlaintext(ctx.baseInput);
    Plaintext ptxt_clean;
if (inj.here("encode")) inject(ptxt->GetElement<DCRTPoly>(), args.withNTT, inj);

    Ciphertext<DCRTPoly> c = ctx.cc->Encrypt(ctx.keys.publicKey, ptxt);
    Ciphertext<DCRTPoly> c_clean;

    if(args.doAdd || args.doMul){
        ptxt_clean = ctx.cc->MakeCKKSPackedPlaintext(ctx.baseInput);
        c_clean = ctx.cc->Encrypt(ctx.keys.publicKey, ptxt_clean);
    }

    if(args.doPlainMul){
        ptxt_clean = ctx.cc->MakeCKKSPackedPlaintext(ctx.baseInput);
    }

if (inj.here("encrypt_c0")) inject(c->GetElements()[0], args.withNTT, inj);
if (inj.here("encrypt_c1")) inject(c->GetElements()[1], args.withNTT, inj);

    for (uint32_t i = 0; i < args.doAdd; ++i)
        c = ctx.cc->EvalAdd(c, c_clean);

    for (uint32_t i = 0; i < args.doPlainMul; ++i)
        c = ctx.cc->EvalMult(c, ptxt_clean);

    for (uint32_t i = 0; i < args.doMul; ++i)
        c = ctx.cc->EvalMult(c, c_clean);

    if(args.doScalarMul>0){
        double scalar = static_cast<double>(args.doScalarMul);
        c = ctx.cc->EvalMult(c, scalar);
    }

    if(args.doRot){
        int32_t rotIndex = static_cast<int32_t>(1ULL << (args.doRot - 1));
        c = ctx.cc->EvalRotate(c, rotIndex);
    }
if (inj.here("decrypt_c0")) inject(c->GetElements()[0], args.withNTT, inj);
if (inj.here("decrypt_c1")) inject(c->GetElements()[1], args.withNTT, inj);

    ctx.cc->Decrypt(ctx.keys.secretKey, c, &result_bitFlip);

    bool detected = SDCConfigHelper::WasSDCDetected(result_bitFlip);

    result_bitFlip->SetLength(1 << args.logSlots);

    return {result_bitFlip->GetRealPackedValue(), detected};
}


