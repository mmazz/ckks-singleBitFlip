#ifndef CAMPAIGN_LOGGER_HPP
#define CAMPAIGN_LOGGER_HPP

#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <chrono>
#include <iomanip>
#include <mutex>
#include <filesystem>
#include <ctime>
#include <zlib.h>


namespace fs = std::filesystem;

struct CampaignMetadata {
    uint32_t campaign_id;
    std::string library;
    std::string timestamp;

    // Parámetros CKKS
    uint32_t logN;              // Ring dimension
    uint32_t logQ;              // Ring dimension
    uint32_t logDelta;          // Scaling factor bits
    uint32_t logSlots;          // Scaling factor bits
    uint32_t mult_depth;
    uint64_t seed;
    uint64_t seed_input;
    uint32_t num_limbs;      // Para RNS
    uint32_t withNTT;      // Para RNS

    // Golden reference
    double golden_norm;

    // Resultados
    uint64_t total_bitflips;
    uint32_t num_stages;

    std::string to_csv_row() const {
        std::stringstream ss;
        ss << campaign_id << ","
           << library << ","
           << timestamp << ","
           << logN << ","
           << logQ << ","
           << logDelta << ","
           << logSlots << ","
           << mult_depth << ","
           << seed << ","
           << seed_input << ","
           << withNTT << ","
           << num_limbs << ","
           << std::scientific << std::setprecision(6) << golden_norm << ","
           << total_bitflips << ","
           << num_stages;
        return ss.str();
    }

    static std::string csv_header() {
        return "campaign_id,library,timestamp,logN,logDelta,logSlots"
               "mult_depth,seed,seed_input,withNTT,num_limbs,golden_norm,"
               "total_bitflips,num_stages";
    }
};

// ============================================================================
// BitflipResult: Una sola observación de bit flip
// ============================================================================
struct BitflipResult {
    uint32_t limb;
    uint32_t coeff;
    uint32_t bit;
    std::string stage;      // "encrypt", "mul", "add", etc.
    double norm2;
    double rel_error;
    bool is_sdc;

    std::string to_csv_row() const {
        std::stringstream ss;
        ss << limb << ","
           << coeff << ","
           << (int)bit << ","
           << stage << ","
           << std::scientific << std::setprecision(6) << norm2 << ","
           << rel_error << ","
           << (is_sdc ? "1" : "0");
        return ss.str();
    }

    static std::string csv_header() {
        return "limb,coeff,bit,stage,norm2,rel_error,is_sdc";
    }
};

// ============================================================================
// CampaignLogger: Maneja escritura eficiente con buffer
// ============================================================================
class CampaignLogger {
private:
    uint32_t campaign_id_;
    std::string data_filepath_;
    std::ofstream data_file_;

    // Buffer para escritura eficiente
    std::vector<std::string> buffer_;
    size_t buffer_size_;
    size_t flush_threshold_;

    // Thread safety para campañas paralelas
    std::mutex write_mutex_;

    // Estadísticas
    uint64_t total_entries_;
    uint64_t sdc_count_;

    void flush_buffer() {
        if (buffer_.empty()) return;

        std::lock_guard<std::mutex> lock(write_mutex_);

        for (const auto& line : buffer_) {
            data_file_ << line << "\n";
        }
        data_file_.flush();

        buffer_.clear();
    }

public:
    CampaignLogger(uint32_t campaign_id,
                   const std::string& results_dir = "results/data",
                   size_t flush_threshold = 10000)
        : campaign_id_(campaign_id),
          buffer_size_(0),
          flush_threshold_(flush_threshold),
          total_entries_(0),
          sdc_count_(0)
    {
        // Crear directorio si no existe
        fs::create_directories(results_dir);

        // Abrir archivo de datos
        std::stringstream ss;
        ss << results_dir << "/campaign_"
           << std::setfill('0') << std::setw(4) << campaign_id
           << ".csv";
        data_filepath_ = ss.str();

        data_file_.open(data_filepath_, std::ios::out);

        if (!data_file_.is_open()) {
            throw std::runtime_error("Cannot open file: " + data_filepath_);
        }

        // Escribir header
        data_file_ << BitflipResult::csv_header() << "\n";

        buffer_.reserve(flush_threshold);
    }

    void log_bitflip(const BitflipResult& result) {
        buffer_.push_back(result.to_csv_row());
        total_entries_++;

        if (result.is_sdc) {
            sdc_count_++;
        }

        // Flush periódico
        if (buffer_.size() >= flush_threshold_) {
            flush_buffer();
        }
    }

    // Para el loop anidado: log directo sin crear struct
    void log_bitflip(uint32_t limb,  uint32_t coeff,
                     uint32_t bit, const std::string& stage,
                     double norm2, double rel_error, bool is_sdc = false)
    {
        BitflipResult result{limb,  coeff, bit, stage,
                            norm2, rel_error, is_sdc};
        log_bitflip(result);
    }

    uint64_t get_total_entries() const { return total_entries_; }
    uint64_t get_sdc_count() const { return sdc_count_; }

    ~CampaignLogger() {
        flush_buffer();
        data_file_.close();

        // Comprimir el archivo CSV
        compress_csv();
    }

private:
    void compress_csv() {
        // Comprimir usando gzip
        std::string cmd = "gzip -f " + data_filepath_;
        int ret = system(cmd.c_str());

        if (ret == 0) {
            std::cout << "Compressed: " << data_filepath_ << ".gz" << std::endl;
        } else {
            std::cerr << "Warning: Failed to compress " << data_filepath_ << std::endl;
        }
    }
};

// ============================================================================
// CampaignRegistry: Mantiene el registro global de campañas
// ============================================================================
class CampaignRegistry {
private:
    std::string registry_filepath_;
    std::mutex registry_mutex_;

public:
    CampaignRegistry(const std::string& results_dir = "results")
        : registry_filepath_(results_dir + "/campaigns.csv")
    {
        fs::create_directories(results_dir);

        // Crear archivo si no existe
        if (!fs::exists(registry_filepath_)) {
            std::ofstream file(registry_filepath_);
            file << CampaignMetadata::csv_header() << "\n";
            file.close();
        }
    }

    uint32_t register_campaign(const CampaignMetadata& metadata) {
        std::lock_guard<std::mutex> lock(registry_mutex_);

        std::ofstream file(registry_filepath_, std::ios::app);
        file << metadata.to_csv_row() << "\n";
        file.close();

        return metadata.campaign_id;
    }

    uint32_t get_next_campaign_id() {
        std::lock_guard<std::mutex> lock(registry_mutex_);

        std::ifstream file(registry_filepath_);
        std::string line;
        uint32_t max_id = 0;

        // Saltar header
        std::getline(file, line);

        while (std::getline(file, line)) {
            if (line.empty()) continue;

            size_t pos = line.find(',');
            if (pos != std::string::npos) {
                uint32_t id = std::stoul(line.substr(0, pos));
                if (id > max_id) max_id = id;
            }
        }

        return max_id + 1;
    }
};

// ============================================================================
// Helper: Obtener timestamp actual
// ============================================================================
inline std::string get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);

    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t_now), "%Y-%m-%dT%H:%M:%S");
    return ss.str();
}

#endif // CAMPAIGN_LOGGER_HPP
