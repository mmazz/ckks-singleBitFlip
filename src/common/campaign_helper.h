#pragma once
#include "attack_mode.h"
#include <chrono>
#include <iomanip>
#include <string>
#include <cstdint>
#include <iostream>

#include <optional>
#include <vector>

inline std::string timestamp_now() {
    auto t = std::chrono::system_clock::to_time_t(
        std::chrono::system_clock::now());
    std::ostringstream ss;
    ss << std::put_time(std::localtime(&t), "%Y-%m-%dT%H:%M:%S");
    return ss.str();
}

struct IterationArgs{
    uint32_t limb;
    uint32_t coeff;
    uint32_t bit;
    IterationArgs(uint64_t l, uint64_t c, uint64_t b)
        : limb(l), coeff(c), bit(b) {}
};



struct CampaignArgs {
    std::string library = "none";
    std::string stage = "none";

    uint32_t bitPerCoeff = 64;
    uint32_t logN = 3;
    uint32_t logQ = 60;
    uint32_t logDelta = 50;
    uint32_t logSlots = 2;
    uint32_t mult_depth = 0;
    uint32_t num_limbs = 1;
    uint32_t logMin = 0;
    uint32_t logMax = 0;

    uint32_t seed = 0;
    uint32_t seed_input = 0;

    bool withNTT = false;
    bool doAdd = false;
    uint32_t doMul = 0;
    uint32_t doRot = 0;
    bool isExhaustive = true;
    bool verbose = false;
    std::string results_dir = "../../results";

// OpenFHE-only

    std::optional<AttackModeSKA> openfhe_attack_mode = AttackModeSKA::CompleteInjection;
    std::optional<double> openfhe_threshold_bits = 5.0;
    bool logSlots_provided = false;

    void print(std::ostream& os = std::cout) const;
};

void print_usage(const char* program_name);
CampaignArgs parse_arguments(int argc, char* argv[]);

/**
 * Contexto mínimo de una campaña viva
 * (lo usa main.cpp)
 */
struct CampaignContext {
    uint32_t campaign_id;
    CampaignArgs args;
};
