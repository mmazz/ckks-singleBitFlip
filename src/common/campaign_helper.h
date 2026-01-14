#pragma once
#include <getopt.h>
#include <iostream>
#include <string>
#include <cstdlib>
#include <cstdint>

struct CampaignArgs {
    std::string library = "openfhe";
    std::string stage = "all";
    uint32_t N = 16384;
    uint32_t delta = 50;
    uint32_t mult_depth = 5;
    uint64_t seed = 42;
    uint64_t seed_input = 42;
    uint32_t num_limbs = 3;
    std::string results_dir = "results";
    bool verbose = false;
};

void print_usage(const char* program_name);

CampaignArgs parse_arguments(int argc, char* argv[]);
