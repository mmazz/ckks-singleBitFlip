#pragma once
#include <fstream>
#include <vector>
#include <mutex>
#include <string>
#include <cstdint>

struct BitflipResult {
    uint32_t limb;
    uint32_t coeff;
    uint32_t bit;
    std::string stage;
    double norm2;
    double rel_error;
    bool is_sdc;

    static std::string header();
    std::string row() const;
};

class CampaignLogger {
public:
    CampaignLogger(uint32_t campaign_id,
                   const std::string& results_dir,
                   size_t flush_threshold = 10000);

    void log(const BitflipResult& r);
    void log(uint32_t limb, uint32_t coeff, uint32_t bit,
         const std::string& stage, double norm2, double rel_error, bool is_sdc);

    void flush();
    void close();

    uint64_t total() const { return total_; }
    uint64_t sdc() const { return sdc_; }
    ~CampaignLogger();

private:
    std::ofstream file_;
    std::vector<std::string> buffer_;
    std::mutex mtx_;
    size_t flush_threshold_;
    uint64_t total_ = 0;
    uint64_t sdc_ = 0;
};

