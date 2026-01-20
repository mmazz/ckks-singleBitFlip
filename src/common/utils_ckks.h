#pragma once
#include <random>

#include <iostream>
#include <getopt.h>
#include <cstring>
#include <cmath>
#include <stdexcept>
#include <algorithm>
#include <vector>
#include <stdexcept>

struct CKKSAccuracyMetrics {
    double l2_rel_error;     // ||y - g||₂ / ||g||₂
    double linf_abs_error;   // max |y_i - g_i|
    double bits_precision;  // -log2(l2_rel_error)
};

double percentile(std::vector<double>& v, double p);


inline CKKSAccuracyMetrics EvaluateCKKSAccuracy(const std::vector<double>& golden,
                             const std::vector<double>& ckks, double zero_eps= 1e-12)
{
    if (golden.size() != ckks.size())
        throw std::invalid_argument("Vectors must have the same size");

    if (golden.empty())
        throw std::invalid_argument("Vectors must not be empty");

    double l2_diff_sq = 0.0;
    double l2_golden_sq = 0.0;
    double linf_error = 0.0;

    for (size_t i = 0; i < golden.size(); ++i) {
        const double diff = ckks[i] - golden[i];

        l2_diff_sq   += diff * diff;
        l2_golden_sq += golden[i] * golden[i];

        linf_error = std::max(linf_error, std::abs(diff));
    }

    // Evita división por cero si el golden es (casi) nulo
    double denom = std::max(std::sqrt(l2_golden_sq), zero_eps);
    double l2_rel_error = std::sqrt(l2_diff_sq) / denom;

    // bits efectivos de precisión
    double bits_precision;
    if (l2_rel_error <= 0.0) {
        bits_precision = std::numeric_limits<double>::infinity();
    } else {
        bits_precision = -std::log2(l2_rel_error);
    }

    return {
        l2_rel_error,
        linf_error,
        bits_precision
    };
}

class BitSelectorExponential {
public:
    BitSelectorExponential(int max_bit = 64, double alpha = 0.15)
        : max_bit_(max_bit),
          dist_(0.0, 1.0),
          rng_(std::random_device{}())
    {
        weights_.resize(max_bit_ + 1);
        double sum = 0.0;
        for (int b = 0; b <= max_bit_; ++b) {
            weights_[b] = std::exp(alpha * b);
            sum += weights_[b];
        }
        for (double& w : weights_) w /= sum;
    }

    int sample() {
        double r = dist_(rng_);
        double acc = 0.0;
        for (int b = 0; b <= max_bit_; ++b) {
            acc += weights_[b];
            if (r <= acc) return b;
        }
        return max_bit_;
    }

private:
    int max_bit_;
    std::vector<double> weights_;
    std::uniform_real_distribution<double> dist_;
    std::mt19937 rng_;
};

class BitSelectorStratified {
public:
    BitSelectorStratified()
        : dist_(0.0, 1.0),
          rng_(std::random_device{}())
    {}

    int sample() {
        double r = dist_(rng_);

        if (r < 0.20) {
            return rand_range(0, 20);     // LSB
        } else if (r < 0.50) {
            return rand_range(21, 40);    // MID
        } else {
            return rand_range(41, 64);    // MSB
        }
    }

private:
    int rand_range(int a, int b) {
        std::uniform_int_distribution<int> d(a, b);
        return d(rng_);
    }

    std::uniform_real_distribution<double> dist_;
    std::mt19937 rng_;
};

bool AcceptCKKSResult(const CKKSAccuracyMetrics& m, double max_rel_error = 1e-6,
                      double max_abs_error = 1e-6, double min_bits = 20.0);

double compute_rel_norm2(const std::vector<double>& v1, const std::vector<double>& v2);

std::vector<double> uniform_dist(uint32_t batchSize, int64_t  logMin, int64_t logMax, uint64_t seed, bool verbose=false);



struct SlotErrorStats {
    uint64_t undecryptable = 0;
    uint64_t maybenot = 0;
    uint64_t maybe = 0;
    uint64_t decryptable = 0;

    uint64_t total() const {
        return undecryptable + maybenot + maybe + decryptable;
    }

    double frac_undecryptable() const {
        return total() ? double(undecryptable) / total() : 0.0;
    }

    double frac_maybenot() const {
        return total() ? double(maybenot) / total() : 0.0;
    }

    double frac_maybe() const {
        return total() ? double(maybe) / total() : 0.0;
    }

    double frac_decryptable() const {
        return total() ? double(decryptable) / total() : 0.0;
    }
};

/**
 * Slot usability metric for CKKS-style approximate arithmetic.
 *
 * @param input      Golden reference vector
 * @param output     Faulty output vector
 * @param size       Number of slots to consider
 * @param rel_eps    Threshold below which we consider a slot decryptable
 * @param rel_mid    Threshold for moderate degradation
 * @param rel_high   Threshold for severe degradation
 * @param abs_eps    Absolute threshold for near-zero reference values
 */

SlotErrorStats categorize_slots(
    const std::vector<double>& input,
    const std::vector<double>& output,
    size_t size,
    double rel_eps   = 1e-2,   // 1%
    double rel_mid   = 1e-1,   // 10%
    double rel_high  = 10.0,   // 1000%
    double abs_eps   = 1e-12   // near-zero cutoff
);



