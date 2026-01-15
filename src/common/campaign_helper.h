#pragma once

#include "openfhe.h"
#include <getopt.h>
#include <iostream>
#include <string>
#include <cstdlib>
#include <cstdint>

using namespace lbcrypto;

inline const char* to_string(SecretKeyAttackMode mode) {
    switch (mode) {
        case SecretKeyAttackMode::Disabled:
            return "Disabled";
        case SecretKeyAttackMode::CompleteInjection:
            return "CompleteInjection";
        case SecretKeyAttackMode::RealOnly:
            return "RealOnly";
        case SecretKeyAttackMode::ImaginaryOnly:
            return "ImaginaryOnly";
    }
    return "Unknown";
}

inline std::ostream& operator<<(std::ostream& os, SecretKeyAttackMode mode) {
    return os << to_string(mode);
}

struct CampaignArgs {
    std::string library = "openfhe";
    std::string stage = "none";
    uint32_t logN = 3;
    uint32_t logQ = 60;
    uint32_t logDelta = 50;
    uint32_t logSlots = 2;
    uint32_t mult_depth = 0;
    uint64_t seed = 42;
    uint64_t seed_input = 42;
    uint32_t num_limbs = 0;
    uint32_t logMin = 0;
    uint32_t logMax = 0;
    bool withNTT = true;
    SecretKeyAttackMode attackMode = SecretKeyAttackMode::CompleteInjection;
    double thresholdBitsSKA = 5.0;
    std::string results_dir = "../results";
    bool verbose = false;

    void print(std::ostream& os = std::cout) const {
        os << "Campaign Configuration:\n"
           << "  Library: " << library << '\n'
           << "  logN: " << logN << '\n'
           << "  logQ: " << logQ << '\n'
           << "  logDelta: " << logDelta << '\n'
           << "  logSlots: " << logSlots<< '\n'
           << "  Mult depth: " << mult_depth << '\n'
           << "  Seed: " << seed << '\n'
           << "  Seed-input: " << seed_input << '\n'
           << "  Num limbs: " << num_limbs << '\n'
           << "  logMin: " << logMin << '\n'
           << "  logMax: " << logMax << '\n'
           << "  WithNTT: " << withNTT << '\n'
           << "  Stage: " << stage << '\n'
           << "  AttackModeSKA: " << attackMode << '\n'
           << "  thresholdBitsSKA: " << thresholdBitsSKA << '\n'
           << "  Results dir: " << results_dir << '\n';
    }
};

void print_usage(const char* program_name);

const CampaignArgs parse_arguments(int argc, char* argv[]);
