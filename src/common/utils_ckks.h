#pragma once
#include <random>

#include <iostream>
#include <getopt.h>
#include <cstring>


double compute_norm2(const std::vector<double>& v1, const std::vector<double>& v2);


std::vector<double> uniform_dist(uint32_t batchSize, int64_t  logMin, int64_t logMax, uint64_t seed, bool verbose=false);

