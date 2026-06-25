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
CampaignRegistry::CampaignRegistry(const CampaignArgs& args, std::chrono::high_resolution_clock::time_point start_time) {

    const std::string& results_dir = args.results_dir;

    fs::create_directories(results_dir);

    start_csv_ = results_dir + "/campaigns_start.csv";
    end_csv_   = results_dir + "/campaigns_end.csv";
    lockfile_  = results_dir + "/.registry.lock";


    int fd;
    lock_file(fd);


    // Crear archivos y headers antes de buscar IDs
    if (!fs::exists(start_csv_)) {
        std::ofstream f(start_csv_);

        f << "campaign_id,library,stage,logN,logQ,bitPerCoeff,logDelta,logSlots,"
             "withNTT,mult_depth,doAdd,doPlainMul,doMul,doScalarMul,doRot,doBoot,op_index,"
             "op_step,seed,seed_input,"
             "isComplex,logMin,logMax,isExhaustive,dnum,scaleTech\n";
    }


    if (!fs::exists(end_csv_)) {
        std::ofstream f(end_csv_);

        f << "campaign_id,total_bitflips,sdc_count,"
             "duration_seconds,l2_P95,l2_P99,duration\n";
    }


    auto key = makeCampaignKey(args);


    auto existing_id = findCampaignId(start_csv_, key);


    if (existing_id != INVALID_CAMPAIGN_ID) {

        if (args.existing_policy == ExistingCampaignPolicy::Fail) {

            unlock_file(fd);

            throw std::runtime_error(
                "Campaign already exists id=" +
                std::to_string(existing_id));
        }


        this->campaign_id = existing_id;

    }
    else {

        this->campaign_id = allocate_campaign_id();


        // IMPORTANTE:
        // Registrar acá mientras el lock sigue tomado
        // para que el próximo proceso vea este ID.

        std::ofstream f(start_csv_, std::ios::app);
        f << this->campaign_id
          << "," << key
          << "\n";
    }


    unlock_file(fd);
}

uint32_t CampaignRegistry::findCampaignId(
    const std::string& csvFile,
    const std::string& key)
{
    std::ifstream file(csvFile);
    if (!file.is_open())
        return INVALID_CAMPAIGN_ID;

    std::string line;

    // header
    std::getline(file, line);

    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        auto comma = line.find(',');
        if (comma == std::string::npos)
            continue;

        uint32_t campaignId =
            std::stoul(line.substr(0, comma));

        std::string existingKey =
            line.substr(comma + 1);

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

uint32_t CampaignRegistry::allocate_campaign_id()
{
    std::ifstream f(start_csv_);

    std::string line;

    uint32_t max_id = 0;

    std::getline(f,line); // header

    while(std::getline(f,line))
    {
        if(line.empty())
            continue;

        auto comma = line.find(',');

        if(comma == std::string::npos)
            continue;

        uint32_t id =
            std::stoul(line.substr(0,comma));

        max_id = std::max(max_id,id);
    }

    return max_id + 1;
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
      << r.duration<< "\n";

    unlock_file(fd);
}

