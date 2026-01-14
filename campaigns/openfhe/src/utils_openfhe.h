#pragma once

#include "openfhe.h"
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

struct CampaignContext {
    CryptoContext<DCRTPoly> cc;
    KeyPair<DCRTPoly> keys;
    std::vector<double> baseInput;
};

struct IterationArgs{
    uint64_t limb;
    uint64_t coeff;
    uint64_t bit;
    IterationArgs(uint64_t l, uint64_t c, uint64_t b)
        : limb(l), coeff(c), bit(b) {}
};

struct IterationResult {
    std::vector<double> values;
    bool detected;
};

void bitFlip(Ciphertext<DCRTPoly> &c, bool withNTT, size_t k, size_t i, size_t j, size_t bit);
void bitFlip(Plaintext &ptxt, bool withNTT, size_t i, size_t j, size_t bit);


CampaignContext setup_campaign(const CampaignArgs& args, PRNG& prng);


IterationResult run_iteration(const CampaignContext& ctx, const CampaignArgs& args, PRNG& prng, std::optional<IterationArgs> iterArgs = std::nullopt);


