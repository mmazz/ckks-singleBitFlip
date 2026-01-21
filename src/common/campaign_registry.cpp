#include "campaign_registry.h"
#include <filesystem>
#include <fstream>
#include <fcntl.h>
#include <unistd.h>
#include <chrono>
#include <iomanip>

namespace fs = std::filesystem;

CampaignRegistry::CampaignRegistry(const std::string& results_dir) {
    fs::create_directories(results_dir);
    start_csv_ = results_dir + "/campaigns_start.csv";
    end_csv_   = results_dir + "/campaigns_end.csv";
    lockfile_  = results_dir + "/.registry.lock";

    if (!fs::exists(start_csv_)) {
        std::ofstream f(start_csv_);
        f << "campaign_id,library,stage,bitPerCoeff,logN,logQ,logDelta,logSlots,"
             "mult_depth,seed,seed_input,withNTT,num_limbs,"
             "logMin,logMax,doAdd,doMul,doRot,flipType,timestamp_start\n";
    }

    if (!fs::exists(end_csv_)) {
        std::ofstream f(end_csv_);
        f << "campaign_id,total_bitflips,sdc_count,"
             "duration_seconds,l2_P95, l2_P99, timestamp_end\n";
    }
}

void CampaignRegistry::lock_file(int& fd) {
    fd = open(lockfile_.c_str(), O_CREAT | O_RDWR, 0666);
    flock(fd, LOCK_EX);
}

void CampaignRegistry::unlock_file(int fd) {
    flock(fd, LOCK_UN);
    close(fd);
}

uint32_t CampaignRegistry::allocate_campaign_id() {
    int fd;
    lock_file(fd);

    std::ifstream f(start_csv_);
    std::string line;
    uint32_t max_id = 0;
    std::getline(f, line);
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        max_id = std::max(max_id, (uint32_t)std::stoul(line));
    }

    unlock_file(fd);
    return max_id + 1;
}

void CampaignRegistry::register_start(const CampaignStartRecord& r) {
    std::cout << "lock"<< std::endl;
    int fd;
    lock_file(fd);
    std::cout << "lock"<< std::endl;

    std::ofstream f(start_csv_, std::ios::app);
    f << r.campaign_id << ","
      << r.args.library << ","
      << r.args.stage<< ","
      << r.args.bitPerCoeff<< ","
      << r.args.logN << ","
      << r.args.logQ << ","
      << r.args.logDelta << ","
      << r.args.logSlots << ","
      << r.args.mult_depth << ","
      << r.args.seed << ","
      << r.args.seed_input << ","
      << (r.args.withNTT ? 1 : 0) << ","
      << r.args.num_limbs << ","
      << r.args.logMin << ","
      << r.args.logMax << ","
      << (r.args.doAdd? 1 : 0) << ","
      << (r.args.doMul? 1 : 0) << ","
      << r.args.doRot << ","
      << r.args.flipType << ","
      << r.timestamp_start << "\n";

    unlock_file(fd);
}

void CampaignRegistry::register_end(const CampaignEndRecord& r) {
    int fd;
    lock_file(fd);

    std::ofstream f(end_csv_, std::ios::app);
    f << r.campaign_id << ","
      << r.total_bitflips << ","
      << r.sdc_count << ","
      << r.duration_seconds << ","
      << r.duration_seconds << ","
      << r.l2_P95<< ","
      << r.l2_P99<< ","
      << r.timestamp_end << "\n";

    unlock_file(fd);
}

