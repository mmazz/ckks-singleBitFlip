#pragma once
#include <vector>
#include <optional>
#include "campaign_helper.h"
#include "utils_ckks.h"
#include <algorithm>
#include <functional>
#include <cstddef>
#include <complex>

using cdouble = std::complex<double>;
struct CampaignArgs;

inline void rotate_left(std::vector<double>& v, size_t rot) {
    if (v.empty()) return;
    rot %= v.size();
    std::rotate(v.begin(), v.begin() + rot, v.end());
}

inline void rotate_left(std::vector<cdouble>& v, size_t rot) {
    if (v.empty()) return;
    rot %= v.size();
    std::rotate(v.begin(), v.begin() + rot, v.end());
}

inline void compute_plain_io(const CampaignArgs& args,
                             std::vector<double>& base,
                             std::vector<double>& golden) {
    base = uniform_dist(
        1 << args.logSlots,
        args.logMin,
        args.logMax,
        args.seed_input,
        false
    );

    if(args.verbose)
        printVector(base, "Flat input", 10);

    golden = base;
    if (args.doAdd) {
        std::transform(
            golden.begin(), golden.end(),
            base.begin(),
            golden.begin(),
            std::plus<double>()
        );
    }

    std::cout << "doPlainMul "  << args.doPlainMul << std::endl;
    for (uint32_t i = 0; i < args.doPlainMul+args.doMul; ++i) {
        std::transform(
            golden.begin(), golden.end(),
            base.begin(),
            golden.begin(),
            std::multiplies<double>()
        );
    }

    if (args.doScalarMul > 0) {
        double scalar = args.doScalarMul;
        std::transform(
            golden.begin(), golden.end(),
            golden.begin(),
            [scalar](double x) { return x * scalar; }
        );
    }

    if (args.doRot > 0) {
        size_t rot = 1ULL << (args.doRot - 1);
        rotate_left(golden, rot);
    }

    if(args.verbose)
        printVector(golden, "Golden output", 10);
}

inline void compute_plain_io(const CampaignArgs& args,
                             std::vector<cdouble>& base,
                             std::vector<cdouble>& golden) {
   std::vector<double> real_base = uniform_dist(
        1 << args.logSlots,
        args.logMin,
        args.logMax,
        args.seed_input,
        false
    );

   std::vector<double> imag_base = uniform_dist(
        1 << args.logSlots,
        args.logMin,
        args.logMax,
        args.seed_input+1,
        false
    );
    base.resize(real_base.size());

    // Its good for [-1,1] so the norm of the data is <1
    constexpr double inv_sqrt2 = 0.7071067811865475;
    std::transform(
        real_base.begin(), real_base.end(),
        imag_base.begin(),
        base.begin(),
        [](double re, double im) {
            return cdouble{re* inv_sqrt2, im* inv_sqrt2};
        }
    );

    if (args.verbose)
        printVector(base, "Flat complex input", 10);

    golden = base;

    if (args.doAdd) {
        std::transform(
            golden.begin(), golden.end(),
            base.begin(),
            golden.begin(),
            std::plus<cdouble>()
        );
    }
    const uint32_t nMul = args.doPlainMul + args.doMul;
    for (uint32_t i = 0; i < nMul; ++i) {
        std::transform(
            golden.begin(), golden.end(),
            base.begin(),
            golden.begin(),
            std::multiplies<cdouble>()
        );
    }

    if (args.doScalarMul > 0) {
        double scalar = static_cast<double>(args.doScalarMul);
        std::transform(
            golden.begin(), golden.end(),
            golden.begin(),
            [scalar](const cdouble& x) { return x * scalar; }
        );
    }

    if (args.doRot > 0) {
        size_t rot = 1ULL << (args.doRot - 1);
        rotate_left(golden, rot);
    }

    if (args.verbose)
        printVector(golden, "Golden complex output", 10);
}

struct IterationResult {
    std::vector<double> values;
    bool detected;
};

struct BackendContext {
    virtual ~BackendContext() = default;
};

std::vector<double>
get_reference_output(const BackendContext* ctx);

std::vector<double>
get_reference_output_complex(const BackendContext* ctx);

BackendContext* setup_campaign(const CampaignArgs& args);

IterationResult run_iteration(
    BackendContext* ctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs = std::nullopt
);
IterationResult run_iteration_boot(
    BackendContext* ctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs = std::nullopt
);
IterationResult run_iteration_multiBit(
    BackendContext* bctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs);
void destroy_campaign(BackendContext* ctx);
