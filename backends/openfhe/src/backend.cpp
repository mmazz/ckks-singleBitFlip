#include "backend_interface.h"
#include "openfhe.h"
#include "attack_mode.h"
#include "utils_ckks.h"
using namespace lbcrypto;



struct OpenFHEContext final : BackendContext {
    CryptoContext<DCRTPoly> cc;
    KeyPair<DCRTPoly> keys;
    std::vector<double> baseInput;
    std::vector<double> goldenOutput;
    PRNG* prng;
};

const std::vector<double>& get_reference_output(const BackendContext* bctx)
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

static void bitFlip(Plaintext &ptxt, bool withNTT, size_t i, size_t j, size_t bit){
    if(!withNTT)
        ptxt->GetElement<DCRTPoly>().SwitchFormat();

    NativeInteger& x = ptxt->GetElement<DCRTPoly>().GetAllElements()[i][j];
    uint64_t val = x.ConvertToInt();  // Extrae como uint64_t
    val ^= (1ULL << bit);               // Aplica XOR
    x = NativeInteger(val);

    if(!withNTT)
        ptxt->GetElement<DCRTPoly>().SwitchFormat();
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
    params.SetScalingTechnique(FIXEDMANUAL);
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


IterationResult run_iteration(BackendContext* bctx,
              const CampaignArgs& args,
              std::optional<IterationArgs> iterArgs)
{
    auto& ctx = static_cast<OpenFHEContext&>(*bctx);

    ctx.prng->ResetToSeed();
    Plaintext result_bitFlip;
    Plaintext ptxt = ctx.cc->MakeCKKSPackedPlaintext(ctx.baseInput);

    if (iterArgs && args.stage == "encode") {
        bitFlip(ptxt, args.withNTT,
                iterArgs->limb,
                iterArgs->coeff,
                iterArgs->bit);
    }

    Ciphertext<DCRTPoly> c = ctx.cc->Encrypt(ctx.keys.publicKey, ptxt);
    Ciphertext<DCRTPoly> c_clean;
    if(args.doAdd || args.doMul)
        c_clean = ctx.cc->Encrypt(ctx.keys.publicKey, ptxt);

    if (iterArgs) {
        if (args.stage == "encrypt_c0") {
            bitFlip(c, args.withNTT, 0,
                    iterArgs->limb,
                    iterArgs->coeff,
                    iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            bitFlip(c, args.withNTT, 1,
                    iterArgs->limb,
                    iterArgs->coeff,
                    iterArgs->bit);
        }
    }

    if(args.doAdd)
        ctx.cc->EvalAddInPlace(c,c_clean);
    for (uint32_t i = 0; i < args.doMul; ++i)
        c = ctx.cc->EvalMult(c,c_clean);
    if(args.doRot){
        int32_t rotIndex = static_cast<int32_t>(1ULL << (args.doRot - 1));
        c = ctx.cc->EvalRotate(c, rotIndex);
    }
    ctx.cc->Decrypt(ctx.keys.secretKey, c, &result_bitFlip);

    bool detected = SDCConfigHelper::WasSDCDetected(result_bitFlip);

    result_bitFlip->SetLength(1 << args.logSlots);

    return {result_bitFlip->GetRealPackedValue(), detected};
}



