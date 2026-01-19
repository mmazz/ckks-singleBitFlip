#pragma once
#include <vector>
#include <optional>
#include "campaign_helper.h"
#include "utils_ckks.h"

struct IterationResult {
    std::vector<double> values;
    bool detected;
};

struct BackendContext {
    virtual ~BackendContext() = default;
};

const std::vector<double>&
get_reference_input(const BackendContext* ctx);

BackendContext* setup_campaign(const CampaignArgs& args);

IterationResult run_iteration(
    BackendContext* ctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs = std::nullopt
);

void destroy_campaign(BackendContext* ctx);
