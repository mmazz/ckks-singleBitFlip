#include "openfhe.h"
#include "utils_openfhe.h"


void bitFlip(Ciphertext<DCRTPoly> &c, bool withNTT, size_t k, size_t i, size_t j, size_t bit){
    if(!withNTT)
        c->GetElements()[k].SwitchFormat();

    NativeInteger& x = c->GetElements()[k].GetAllElements()[i][j];
    uint64_t val = x.ConvertToInt();  // Extrae como uint64_t
    val ^= (1ULL << bit);               // Aplica XOR
    x = NativeInteger(val);

    if(!withNTT)
        c->GetElements()[k].SwitchFormat();
}
void bitFlip(Plaintext &ptxt, bool withNTT, size_t i, size_t j, size_t bit){
    if(!withNTT)
        ptxt->GetElement<DCRTPoly>().SwitchFormat();

    NativeInteger& x = ptxt->GetElement<DCRTPoly>().GetAllElements()[i][j];
    uint64_t val = x.ConvertToInt();  // Extrae como uint64_t
    val ^= (1ULL << bit);               // Aplica XOR
    x = NativeInteger(val);

    if(!withNTT)
        ptxt->GetElement<DCRTPoly>().SwitchFormat();
}


CampaignContext setup_campaign(const CampaignArgs& args, PRNG& prng) {
    prng.SetSeed(args.seed);
    CCParams<CryptoContextCKKSRNS> params;
    params.SetMultiplicativeDepth(args.mult_depth);
    params.SetScalingModSize(args.logDelta);
    params.SetFirstModSize(args.logQ);
    params.SetBatchSize(args.logSlots);
    params.SetRingDim(1 << args.logN);
    params.SetScalingTechnique(FIXEDMANUAL);
    params.SetSecurityLevel(HEStd_NotSet);

    auto cc = GenCryptoContext(params);
    cc->Enable(PKE);
    cc->Enable(LEVELEDSHE);

    auto keys = cc->KeyGen();

    std::vector<double> input =
        uniform_dist(4, -1, 1, args.seed_input, false);

    return {cc, keys, input};
}

IterationResult run_iteration(const CampaignContext& ctx, const CampaignArgs& args, PRNG& prng, std::optional<IterationArgs> iterArgs)
{
    prng.ResetToSeed();
    Plaintext result_bitFlip;

    Plaintext ptxt1 = ctx.cc->MakeCKKSPackedPlaintext(ctx.baseInput);
    if (iterArgs && args.stage == "encode") {
        bitFlip(ptxt1, args.withNTT,
                iterArgs->limb, iterArgs->coeff, iterArgs->bit);
    }

    Ciphertext<DCRTPoly> c = ctx.cc->Encrypt(ctx.keys.publicKey, ptxt1);

    if (iterArgs && args.stage == "encrypt_c0") {
        bitFlip(c, args.withNTT, 0,
                iterArgs->limb, iterArgs->coeff, iterArgs->bit);
    }
    if (iterArgs && args.stage == "encrypt_c1") {
        bitFlip(c, args.withNTT, 1,
                iterArgs->limb, iterArgs->coeff, iterArgs->bit);
    }

    ctx.cc->Decrypt(ctx.keys.secretKey, c, &result_bitFlip);

    bool detected = SDCConfigHelper::WasSDCDetected(result_bitFlip);
    result_bitFlip->SetLength(args.logSlots);


    std::vector<double> result_bitFlip_vec = result_bitFlip->GetRealPackedValue();


    return IterationResult{result_bitFlip_vec, detected};
}

