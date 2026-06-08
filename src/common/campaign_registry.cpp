#include "campaign_registry.h"
#include <filesystem>
#include <fstream>
#include <fcntl.h>
#include <unistd.h>
#include <chrono>
#include <iomanip>

namespace fs = std::filesystem;
constexpr uint32_t INVALID_CAMPAIGN_ID =
    std::numeric_limits<uint32_t>::max();

std::string CampaignRegistry::makeCampaignKey(const CampaignArgs& args)
{
    std::ostringstream oss;

    oss << args.library << ","
        << args.stage << ","
        << args.logN << ","
        << args.logQ << ","
        << args.bitPerCoeff << ","
        << args.logDelta << ","
        << args.logSlots << ","
        << (args.withNTT ? 1 : 0) << ","
        << args.mult_depth << ","
        << (args.doAdd ? 1 : 0) << ","
        << args.doPlainMul << ","
        << args.doMul << ","
        << args.doScalarMul << ","
        << args.doRot << ","
        << args.doBoot << ","
        << args.op_index << ","
        << args.op_step << ","
        << args.seed << ","
        << args.seed_input << ","
        << args.isComplex << ","
        << args.logMin << ","
        << args.logMax << ","
        << args.isExhaustive << ","
        << args.dnum << ","
        << args.scaleTech;

    return oss.str();
}

CampaignRegistry::CampaignRegistry(const CampaignArgs& args) {
    const std::string& results_dir = args.results_dir;
    fs::create_directories(results_dir);
    start_csv_ = results_dir + "/campaigns_start.csv";
    end_csv_   = results_dir + "/campaigns_end.csv";
    lockfile_  = results_dir + "/.registry.lock";


    auto key = makeCampaignKey(args);
    auto campaign_id = findCampaignId(start_csv_, key);
    auto policy = args.existing_policy;
    if (campaign_id != INVALID_CAMPAIGN_ID) {
        if (policy == ExistingCampaignPolicy::Fail)
        {
            throw std::runtime_error(
                "Campaign with those parameters already exists. campaign_id=" +
                std::to_string(campaign_id));
        }else{
            this->campaign_id = campaign_id;
        }
    }
    else{
        this->campaign_id = this->allocate_campaign_id();
    }
    if (!fs::exists(start_csv_)) {
        std::ofstream f(start_csv_);
        f << "campaign_id,library,stage,logN,logQ,bitPerCoeff,logDelta,logSlots,"
             "withNTT,mult_depth,doAdd,doPlainMul,doMul,doScalarMul,doRot,doBoot,op_index,"
             "op_step,seed,seed_input,"
             "isComplex,logMin,logMax,isExhaustive,dnum,scaleTech,timestamp_start\n";

    }

    if (!fs::exists(end_csv_)) {
        std::ofstream f(end_csv_);
        f << "campaign_id,total_bitflips,sdc_count,"
             "duration_seconds,l2_P95, l2_P99, timestamp_end\n";
    }
}

uint32_t CampaignRegistry::findCampaignId(const std::string& csvFile,
                    const std::string& key)
{
    std::ifstream file(csvFile);
    if (!file.is_open())
        return -1;

    std::string line;

    // Saltear header
    std::getline(file, line);

    while (std::getline(file, line))
    {
        // campaign_id
        auto firstComma = line.find(',');
        if (firstComma == std::string::npos)
            continue;

        long campaignId =
            std::stol(line.substr(0, firstComma));

        // quitar campaign_id al inicio
        // quitar timestamp_start al final
        auto lastComma = line.rfind(',');
        if (lastComma == std::string::npos || lastComma <= firstComma)
            continue;

        std::string existingKey =
            line.substr(firstComma + 1,
                        lastComma - firstComma - 1);

        if (existingKey == key)
            return campaignId;
    }

    return INVALID_CAMPAIGN_ID;
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

    auto key = makeCampaignKey(r.args);
    f << r.campaign_id << "," << key << ","
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
      << r.l2_P95<< ","
      << r.l2_P99<< ","
      << r.timestamp_end << "\n";

    unlock_file(fd);
}

