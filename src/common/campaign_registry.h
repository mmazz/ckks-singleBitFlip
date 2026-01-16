#pragma once
#include <string>
#include <cstdint>
#include <sys/file.h>
#include "campaign_helper.h"

struct CampaignStartRecord {
    uint32_t campaign_id;
    CampaignArgs args;
    std::string timestamp_start;
};

struct CampaignEndRecord {
    uint32_t campaign_id;
    uint64_t total_bitflips;
    uint64_t sdc_count;
    uint64_t duration_seconds;
    std::string timestamp_end;
};

class CampaignRegistry {
public:
    explicit CampaignRegistry(const std::string& results_dir);

    uint32_t allocate_campaign_id();
    void register_start(const CampaignStartRecord& rec);
    void register_end(const CampaignEndRecord& rec);

private:
    std::string start_csv_;
    std::string end_csv_;
    std::string lockfile_;

    void lock_file(int& fd);
    void unlock_file(int fd);
};
