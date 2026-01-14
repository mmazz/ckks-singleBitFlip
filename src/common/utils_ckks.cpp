#include "utils_ckks.h"
#include <vector>
#include <random>
#include <cmath>
#include <iostream>
#include <stdexcept>

double compute_norm2(const std::vector<double>& v1, const std::vector<double>& v2) {
    double sum = 0.0;
    for (size_t i = 0; i < v1.size(); ++i) {
        double diff = v1[i] - v2[i];
        sum += diff * diff;
    }
    return std::sqrt(sum);
}




// if logMin=logMax=0 it samples from [-1,1]
std::vector<double> uniform_dist(uint32_t batchSize,
                                 int64_t logMin,
                                 int64_t logMax,
                                 uint64_t seed,
                                 bool verbose)
{
    std::vector<double> input(batchSize);

    // Caso especial: ambos cero → [-1, 1]
    const bool specialSymmetric = (logMin == 0 && logMax == 0);

    if (!specialSymmetric && logMin >= logMax) {
        throw std::invalid_argument("Se requiere que logMin < logMax (excepto el caso 0,0).");
    }

    if (verbose) {
        std::cout << "Parameters: batchSize=" << batchSize
                  << ", logMin=" << logMin
                  << ", logMax=" << logMax
                  << ", seed=" << seed << std::endl;
    }

    std::mt19937_64 gen(seed);

    double min_val, max_val;

    if (specialSymmetric) {
        min_val = -1.0;
        max_val =  1.0;
    } else {
        min_val = std::pow(2.0, static_cast<double>(logMin));
        max_val = std::pow(2.0, static_cast<double>(logMax));
    }

    if (verbose) {
        std::cout << "Range = [" << min_val << ", " << max_val << "]" << std::endl;
    }

    std::uniform_real_distribution<double> dist(min_val, max_val);

    for (uint32_t i = 0; i < batchSize; ++i) {
        input[i] = dist(gen);
        if (verbose)
            std::cout << input[i] << ", ";
    }

    if (verbose)
        std::cout << std::endl;

    return input;
}


