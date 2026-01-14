#pragma once
#include <getopt.h>
#include <iostream>
#include <string>
#include <cstdlib>
#include <cstdint>


struct CampaignArgs {
    std::string library = "openfhe";
    std::string stage = "all";
    uint32_t logN = 14;
    uint32_t logQ = 60;
    uint32_t logDelta = 50;
    uint32_t logSlots = 4;
    uint32_t mult_depth = 5;
    uint64_t seed = 42;
    uint64_t seed_input = 42;
    uint32_t num_limbs = 3;
    bool withNTT = true;
    std::string results_dir = "results";
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
           << "  WithNTT: " << withNTT << '\n'
           << "  Stage: " << stage << '\n'
           << "  Results dir: " << results_dir << '\n';
    }
};

void print_usage(const char* program_name);

const CampaignArgs parse_arguments(int argc, char* argv[]);
