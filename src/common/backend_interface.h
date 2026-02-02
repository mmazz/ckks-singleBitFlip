#pragma once
#include <vector>
#include <optional>
#include "campaign_helper.h"
#include "utils_ckks.h"
#include <algorithm>
#include <functional>
#include <cstddef>

struct CampaignArgs;

inline void rotate_left(std::vector<double>& v, size_t rot) {
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

    /* MUL: multiplicative depth */
    for (uint32_t i = 0; i < args.doPlainMul+args.doMul; ++i) {
        std::transform(
            golden.begin(), golden.end(),
            base.begin(),
            golden.begin(),
            std::multiplies<double>()
        );
    }


    if (args.doRot > 0) {
        size_t rot = 1ULL << (args.doRot - 1);
        rotate_left(golden, rot);
    }
    if(args.verbose)
        printVector(golden, "Golden output", 10);


}

struct IterationResult {
    std::vector<double> values;
    bool detected;
};

struct BackendContext {
    virtual ~BackendContext() = default;
};

const std::vector<double>&
get_reference_output(const BackendContext* ctx);

BackendContext* setup_campaign(const CampaignArgs& args);

IterationResult run_iteration(
    BackendContext* ctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs = std::nullopt
);

void destroy_campaign(BackendContext* ctx);
