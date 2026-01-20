#include "utils_ckks.h"

double percentile(std::vector<double>& v, double p) {
    double pos = p * (v.size() - 1);
    size_t idx = static_cast<size_t>(pos);
    double frac = pos - idx;

    if (idx + 1 < v.size())
        return v[idx] * (1.0 - frac) + v[idx + 1] * frac;
    else
        return v[idx];
}


bool AcceptCKKSResult(const CKKSAccuracyMetrics& m, double max_rel_error ,
                      double max_abs_error, double min_bits)
{
    return (m.l2_rel_error < max_rel_error) &&
           (m.linf_abs_error < max_abs_error) &&
           (m.bits_precision >= min_bits);
}


double compute_rel_norm2(const std::vector<double>& v1,
                         const std::vector<double>& v2)
{
    double num = 0.0, den = 0.0;
    for (size_t i = 0; i < v1.size(); ++i) {
        double diff = v1[i] - v2[i];
        num += diff * diff;
        den += v1[i] * v1[i];
    }
    return std::sqrt(num) / std::sqrt(den);
}


SlotErrorStats categorize_slots(
    const std::vector<double>& input,
    const std::vector<double>& output,
    size_t size,
    double rel_eps,   // 1%
    double rel_mid,   // 10%
    double rel_high,   // 1000%
    double abs_eps // near-zero cutoff
) {
    if (input.size() < size || output.size() < size) {
        throw std::invalid_argument("categorize_slots: vector size mismatch");
    }

    SlotErrorStats stats;

    for (size_t i = 0; i < size; ++i) {
        const double x = input[i];
        const double y = output[i];

        const double diff = std::fabs(x - y);
        const double abs_x = std::fabs(x);

        // Case 1: reference value is near zero → use absolute error
        if (abs_x < abs_eps) {
            if (diff > rel_mid) {
                stats.undecryptable++;
            } else {
                stats.decryptable++;
            }
            continue;
        }

        // Case 2: standard relative error
        const double rel_err = diff / abs_x;

        if (rel_err > rel_high) {
            stats.undecryptable++;
        } else if (rel_err > rel_mid) {
            stats.maybenot++;
        } else if (rel_err > rel_eps) {
            stats.maybe++;
        } else {
            stats.decryptable++;
        }
    }

    return stats;
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
        throw std::invalid_argument("logMin < logMax (except the case 0,0 for range [-1,1]).");
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


