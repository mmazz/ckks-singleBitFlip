#include "campaign_logger.h"
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <cstdlib>

namespace fs = std::filesystem;

std::string BitflipResult::header() {
    return "limb,coeff,bit,stage,l2_norm,rel_error,is_sdc";
}

std::string BitflipResult::row() const {
    std::ostringstream ss;
    ss << limb << "," << coeff << "," << bit << ","
       << stage << "," << norm2 << ","
       << rel_error << "," << (is_sdc ? 1 : 0);
    return ss.str();
}

CampaignLogger::CampaignLogger(uint32_t id,
                               const std::string& dir,
                               size_t flush_th)
    : flush_threshold_(flush_th)
{
    fs::create_directories(dir);
    std::ostringstream path;
    path << dir << "/campaign_" << std::setw(6)
         << std::setfill('0') << id << ".csv";
    file_.open(path.str());
    file_ << BitflipResult::header() << "\n";
}

CampaignLogger::~CampaignLogger() {
    close();
}

void CampaignLogger::log(const BitflipResult& r) {
    std::lock_guard<std::mutex> g(mtx_);
    buffer_.push_back(r.row());
    total_++;
    if (r.is_sdc) sdc_++;

    if (buffer_.size() >= flush_threshold_)
        flush();
}

void CampaignLogger::log(uint32_t limb, uint32_t coeff, uint32_t bit,
         const std::string& stage, double norm2, double rel_error, bool is_sdc)
    {
        BitflipResult r{
            limb,
            coeff,
            bit,
            stage,
            norm2,
            rel_error,
            is_sdc
        };
        log(r);
    }

void CampaignLogger::flush() {
    for (auto& l : buffer_)
        file_ << l << "\n";
    buffer_.clear();
    file_.flush();
}

void CampaignLogger::close() {
    flush();
    file_.close();
}

