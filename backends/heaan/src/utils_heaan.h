#pragma once
#include <NTL/ZZ.h>

using namespace NTL;
#include "campaign_helper.h"
#include "utils_ckks.h"
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <random>
#include <optional>
using namespace lbcrypto;
    Context cc(args.logN, args.logQ);
    Scheme scheme(sk, context);
    int h = 12; // arreglar
    SecretKey sk(args.logN, h);

    std::vector<double> input =
        uniform_dist(1 << args.logSlots, args.logMin, args.logMax, args.seed_input, false);
    inputPTR = input.data();


struct CKKSExperimentContext{
   const Context cc;
   const Scheme scheme;
   const SecretKey sk;
   const double* baseInput;
};

struct IterationArgs{
    uint32_t limb;
    uint32_t coeff;
    uint32_t bit;
    IterationArgs(uint64_t l, uint64_t c, uint64_t b)
        : limb(l), coeff(c), bit(b) {}
};

struct IterationResult {
    std::vector<double> values;
    bool detected;
};

void bitFlip(Ciphertext<DCRTPoly> &c, bool withNTT, size_t k, size_t i, size_t j, size_t bit);
void bitFlip(Plaintext &ptxt, bool withNTT, size_t i, size_t j, size_t bit);


CKKSExperimentContext setup_campaign(const CampaignArgs& args);

complex<double>* run_iteration(const CKKSExperimentContext & ctx, const CampaignArgs& args, std::optional<IterationArgs> iterArgs)



