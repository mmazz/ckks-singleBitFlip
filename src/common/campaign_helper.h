#pragma once

#include "openfhe.h"
#include <string>
#include <cstdint>
#include <iostream>

using namespace lbcrypto;
inline std::string timestamp_now() {
    auto t = std::chrono::system_clock::to_time_t(
        std::chrono::system_clock::now());
    std::ostringstream ss;
    ss << std::put_time(std::localtime(&t), "%Y-%m-%dT%H:%M:%S");
    return ss.str();
}

inline const char* to_string(SecretKeyAttackMode mode) {
    switch (mode) {
        case SecretKeyAttackMode::Disabled: return "Disabled";
        case SecretKeyAttackMode::CompleteInjection: return "CompleteInjection";
        case SecretKeyAttackMode::RealOnly: return "RealOnly";
        case SecretKeyAttackMode::ImaginaryOnly: return "ImaginaryOnly";
    }
    return "Unknown";
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
    std::string results_dir = "../../results";
    bool verbose = false;

    void print(std::ostream& os = std::cout) const;
};

void print_usage(const char* program_name);
const CampaignArgs parse_arguments(int argc, char* argv[]);

/**
 * Contexto mínimo de una campaña viva
 * (lo usa main.cpp)
 */
struct CampaignContext {
    uint32_t campaign_id;
    CampaignArgs args;
};
