#pragma once
#include "campaign_helper.h"
#include <random>

#include <iostream>
#include <getopt.h>
#include <cstring>
#include <cmath>
#include <stdexcept>
#include <algorithm>
#include <vector>
#include <stdexcept>
#include <random>
#include <utility>
#include <stdexcept>

struct CKKSAccuracyMetrics {
    double l2_rel_error;     // ||y - g||₂ / ||g||₂
    double linf_rel_error;   // max_i |y_i - g_i| / |g_i|   (g_i != 0)
    double linf_abs_error;   // max_i |y_i - g_i|
    double bits_precision;   // -log2(l2_rel_error)
};

struct CKKSBaseline {
    CKKSAccuracyMetrics metrics;
};


struct ErrorThresholds {
    double abs_zero;        // qué se considera "cero" en golden

    double baseline_abs;    // baseline.linf_abs_error
    double baseline_rel;    // baseline.linf_rel_error

    double good;            // multiplicador (≈ 1–2)
    double bad;             // multiplicador (≈ 5)
    double fail;            // multiplicador (≈ 50)
};

inline uint32_t random_int(int a, int b) {
    static thread_local std::mt19937 rng{std::random_device{}()};
    std::uniform_int_distribution<int> dist(a, b);
    return (uint32_t)dist(rng);
}

struct SlotErrorStats {
    uint64_t failed     = 0;
    uint64_t corrupted  = 0;
    uint64_t degraded   = 0;
    uint64_t correct    = 0;

    uint64_t total() const {
        return failed + corrupted + degraded + correct;
    }
};

// -----------------------------
// API
// -----------------------------
CKKSAccuracyMetrics EvaluateCKKSAccuracy(
    const std::vector<double>& golden,
    const std::vector<double>& ckks,
    double zero_eps = 1e-15
);

inline ErrorThresholds thresholds_from_baseline(
    const CKKSBaseline& baseline,
    double abs_zero = 1e-15,
    double good = 1.5,
    double bad  = 5.0,
    double fail = 50.0
) {
    return {
        .abs_zero     = abs_zero,
        .baseline_abs = baseline.metrics.linf_abs_error,
        .baseline_rel = baseline.metrics.linf_rel_error,
        .good         = good,
        .bad          = bad,
        .fail         = fail
    };
}

SlotErrorStats categorize_slots(
    const std::vector<double>& golden,
    const std::vector<double>& output,
    size_t size,
    const ErrorThresholds& thr
);

bool AcceptCKKSResult(const CKKSAccuracyMetrics& m, double max_rel_error = 1e-6,
                      double max_abs_error = 1e-6, double min_bits = 20.0);


std::vector<uint32_t> bitsToFlipGenerator(const CampaignArgs& args);
inline std::vector<size_t> bit_attack_list(const CampaignArgs& args)
{
    std::vector<size_t> res;

    const size_t logDelta = args.logDelta;
    const size_t logQ     = args.logQ;
    const size_t B        = args.bitPerCoeff;

    auto sample_zone = [&](size_t lo, size_t hi, size_t k)
    {
        if (hi <= lo || k == 0) return;

        if (hi - lo <= k) {
            for (size_t b = lo; b < hi; ++b)
                res.push_back(b);
            return;
        }

        double step = double(hi - lo) / double(k);
        for (size_t i = 0; i < k; ++i) {
            size_t b = lo + size_t(i * step);
            res.push_back(b);
        }
    };

    size_t k0 = 2;
    size_t k1 = std::max<size_t>(4, logDelta / 10);
    size_t k2 = 2;

    // Zona baja
    sample_zone(0, logDelta, k0);

    // Zona crítica
    sample_zone(logDelta, logQ, k1);

    // Zona alta
    sample_zone(logQ, B, k2);

    std::sort(res.begin(), res.end());
    res.erase(std::unique(res.begin(), res.end()), res.end());

    return res;
}

double percentile(std::vector<double>& v, double p);



double compute_rel_norm2(const std::vector<double>& v1, const std::vector<double>& v2);

std::vector<double> uniform_dist(uint32_t batchSize, int64_t  logMin, int64_t logMax, uint64_t seed, bool verbose=false);


