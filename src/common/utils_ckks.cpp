#include "utils_ckks.h"
#include <cmath>
#include <algorithm>
#include <stdexcept>

void printVector(const std::vector<double>& v,
                 const std::string& name,
                 size_t max_elems)
{
    if (!name.empty())
        std::cout << name << " (" << v.size() << "): ";

    size_t n = std::min(v.size(), max_elems);

    std::cout << "[ ";
    for (size_t i = 0; i < n; ++i) {
        std::cout << v[i];
        if (i + 1 < n) std::cout << ", ";
    }

    if (n < v.size())
        std::cout << ", ...";

    std::cout << " ]\n";
}

void printVector(const std::vector<cdouble>& v,
                 const std::string& name,
                 size_t max_elems)
{
    if (!name.empty())
        std::cout << name << " (" << v.size() << "): ";

    size_t n = std::min(v.size(), max_elems);

    std::cout << "[ ";
    for (size_t i = 0; i < n; ++i) {
        std::cout << v[i];
        if (i + 1 < n) std::cout << ", ";
    }

    if (n < v.size())
        std::cout << ", ...";

    std::cout << " ]\n";
}

std::vector<uint32_t> bitsToFlipGenerator(const CampaignArgs& args)
{
    std::vector<uint32_t> res;
    res.reserve(10);

    const uint32_t logQ         = args.logQ;
    const uint32_t logDelta     = args.logDelta;
    const uint32_t maxBits      = args.bitPerCoeff;
    const uint32_t M            = maxBits - 1;

    auto clamp = [&](uint32_t v) {
        return std::min(v, M);
    };

    auto push_unique = [&](uint32_t v) {
        v = clamp(v);
        if (std::find(res.begin(), res.end(), v) == res.end())
            res.push_back(v);
    };
    // zone 1
    push_unique(0);
    push_unique(logDelta / 4);
    push_unique(logDelta / 2);
    if (logDelta > 0)
        push_unique(logDelta - 1);

    // zone 2
    push_unique(logDelta);
 //   if(logQ>=120){
        push_unique((logDelta + logQ) / 6);
        push_unique((logDelta + logQ) / 4);
        push_unique((logDelta + logQ) / 3);
        push_unique(logQ-logDelta);
 //   }
    push_unique((logDelta + logQ) / 2);

    if (logQ > 0)
        push_unique(logQ);
    push_unique(logQ+1);

    push_unique((logQ + M) / 2);
    push_unique(M);

    return res;
}



CKKSAccuracyMetrics EvaluateCKKSAccuracy(
    const std::vector<double>& golden,
    const std::vector<double>& ckks,
    double zero_eps
) {
    if (golden.size() != ckks.size())
        throw std::invalid_argument("EvaluateCKKSAccuracy: size mismatch");

    if (golden.empty())
        throw std::invalid_argument("EvaluateCKKSAccuracy: empty vectors");

    double l2_diff_sq   = 0.0;
    double l2_golden_sq = 0.0;

    double linf_abs_error = 0.0;
    double linf_rel_error = 0.0;

    for (size_t i = 0; i < golden.size(); ++i) {
        const double g    = golden[i];
        const double abs_g    = std::abs(g);

        const double diff = ckks[i] - g;
        const double abs_diff = std::abs(diff);

        l2_diff_sq   += diff * diff;
        l2_golden_sq += g * g;

        linf_abs_error = std::max(linf_abs_error, abs_diff);

        if (abs_g > zero_eps) {
            linf_rel_error = std::max(linf_rel_error, abs_diff / abs_g);
        }
    }

    const double denom = std::max(std::sqrt(l2_golden_sq), zero_eps);

    const double l2_rel_error =  std::sqrt(l2_diff_sq) / denom;

    const double bits_precision = (l2_rel_error > 0.0) ? -std::log2(l2_rel_error)
                                    : std::numeric_limits<double>::infinity();

    return {
        l2_rel_error,
        linf_rel_error,
        linf_abs_error,
        bits_precision
    };
}

SlotErrorStats categorize_slots_relative(
    const std::vector<double>& golden,
    const std::vector<double>& output,
    size_t size,
    const RelativeErrorThresholds& thr
) {
    if (golden.size() < size || output.size() < size)
        throw std::invalid_argument("categorize_slots_relative: size mismatch");

    SlotErrorStats stats;

    for (size_t i = 0; i < size; ++i) {
        const double g    = golden[i];
        const double diff = std::abs(output[i] - g);

        double rel_err;

        // -------------------------
        // Caso A: golden ≈ 0
        // -------------------------
        if (std::abs(g) < thr.zero_eps) {
            // usamos error absoluto normalizado
            rel_err = diff;
        } else {
            rel_err = diff / std::abs(g);
        }

        // -------------------------
        // Clasificación
        // -------------------------
        if (rel_err > thr.failed)
            stats.failed++;
        else if (rel_err > thr.corrupted)
            stats.corrupted++;
        else if (rel_err > thr.degraded)
            stats.degraded++;
        else
            stats.correct++;
    }

    return stats;
}

bool AcceptCKKSResult(
    const CKKSAccuracyMetrics& m,
    double max_l2_rel_error,
    double max_linf_abs_error,
    double min_bits_precision
) {
    return (m.l2_rel_error   <= max_l2_rel_error) &&
           (m.linf_abs_error <= max_linf_abs_error) &&
           (m.bits_precision >= min_bits_precision);
}



double percentile(std::vector<double>& v, double p) {
    double pos = p * (v.size() - 1);
    size_t idx = static_cast<size_t>(pos);
    double frac = pos - idx;

    if (idx + 1 < v.size())
        return v[idx] * (1.0 - frac) + v[idx + 1] * frac;
    else
        return v[idx];
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


