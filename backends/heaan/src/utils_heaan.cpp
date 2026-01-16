
#include "utils_heaan.h"



CKKSExperimentContext setup_campaign(const CampaignArgs& args) {
    NTL::ZZ seed = ZZ(args.seed);
    NTL::SetSeed(seed);
    std::srand(args.seed)
    Context cc(args.logN, args.logQ);
    Scheme scheme(sk, context);
    int h = 12; // arreglar
    SecretKey sk(args.logN, h);

    std::vector<double> input =
        uniform_dist(1 << args.logSlots, args.logMin, args.logMax, args.seed_input, false);
    inputPTR = input.data();

    return {cc, scheme, sk, inputPTR};
}



complex<double>* run_iteration(const CKKSExperimentContext & ctx, const CampaignArgs& args, std::optional<IterationArgs> iterArgs)
{
    NTL::ZZ seed = ZZ(args.seed);
    NTL::SetSeed(seed);
    std::srand(args.seed)
    Plaintext plain = ctx.scheme.encode(ctx.baseInput, 1 << args.logSlots, args.logDelta, args.logQ);
    if (iterArgs && args.stage == "encode") {
        SwitchBit(plain.mx[iterArgs.coeff], iterArgs.bit);
    }

    Ciphertext cipher = scheme.encryptMsg(plain, args.seed);

    if (iterArgs && args.stage == "encrypt_c0") {
        SwitchBit(cipher.bx[iterArgs.coeff], iterArgs.bit);
    }
    if (iterArgs && args.stage == "encrypt_c1") {
        SwitchBit(cipher.ax[iterArgs.coeff], iterArgs.bit);
    }

    Plaintext decrypt_plain = scheme.decryptMsg(sk, multCipher);
    if (iterArgs && args.stage == "decrypt") {
        SwitchBit(decrypt_plain.mx[iterArgs.coeff], iterArgs.bit);
    }
    complex<double>* result_bitFlip_vec= scheme.decode(golden_plain);

    return result_bitFlip_vec;
}

