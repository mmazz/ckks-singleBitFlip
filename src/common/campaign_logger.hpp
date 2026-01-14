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
    std::string timestamp_start;
    std::string timestamp_end;

    // Parámetros CKKS
    uint32_t logN;
    uint32_t logQ;
    uint32_t logDelta;
    uint32_t logSlots;
    uint32_t mult_depth;
    uint64_t seed;
    uint64_t seed_input;
    bool withNTT;
    uint32_t num_limbs;
    uint32_t logMin;
    uint32_t logMax;

    // Golden reference
    double golden_norm;

    // Resultados
    uint64_t total_bitflips;
    uint64_t sdc_count;
    uint32_t num_stages;

    // Performance
    uint64_t duration_seconds;
    double bitflips_per_second;

    // Archivos
    std::string data_file;

    std::string to_csv_row() const {
        std::stringstream ss;
        ss << campaign_id << ","
           << library << ","
           << timestamp_start << ","
           << timestamp_end << ","
           << logN << ","
           << logQ << ","
           << logDelta << ","
           << logSlots << ","
           << mult_depth << ","
           << seed << ","
           << seed_input << ","
           << (withNTT ? "1" : "0") << ","
           << num_limbs << ","
           << logMin << ","
           << logMax << ","
           << std::scientific << std::setprecision(6) << golden_norm << ","
           << total_bitflips << ","
           << sdc_count << ","
           << num_stages << ","
           << duration_seconds << ","
           << std::fixed << std::setprecision(2) << bitflips_per_second << ","
           << data_file;
        return ss.str();
    }

    static std::string csv_header() {
        return "campaign_id,library,timestamp_start,timestamp_end,logN,logQ,logDelta,logSlots,"
               "mult_depth,seed,seed_input,withNTT,num_limbs,logMin,logMax,"
               "golden_norm,total_bitflips,sdc_count,num_stages,"
               "duration_seconds,bitflips_per_second,data_file";
    }
};

struct BitflipResult {
    uint32_t limb;
    uint32_t coeff;
    uint32_t bit;
    std::string stage;
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
inline std::string get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);

    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t_now), "%Y-%m-%dT%H:%M:%S");
    return ss.str();
}

class CampaignRegistry {
private:
    std::string registry_filepath_;
    std::mutex registry_mutex_;

    // NUEVO: Leer todas las campañas del CSV
    std::vector<CampaignMetadata> read_all_campaigns() {
        std::vector<CampaignMetadata> campaigns;
        std::ifstream file(registry_filepath_);
        std::string line;

        // Saltar header
        std::getline(file, line);

        while (std::getline(file, line)) {
            if (line.empty()) continue;

            CampaignMetadata meta;
            std::stringstream ss(line);
            std::string token;

            // Parse CSV line
            std::getline(ss, token, ','); meta.campaign_id = std::stoul(token);
            std::getline(ss, meta.library, ',');
            std::getline(ss, meta.timestamp_start, ',');
            std::getline(ss, meta.timestamp_end, ',');
            std::getline(ss, token, ','); meta.logN = std::stoul(token);
            std::getline(ss, token, ','); meta.logDelta = std::stoul(token);
            std::getline(ss, token, ','); meta.logSlots = std::stoul(token);
            std::getline(ss, token, ','); meta.mult_depth = std::stoul(token);
            std::getline(ss, token, ','); meta.seed = std::stoull(token);
            std::getline(ss, token, ','); meta.seed_input = std::stoull(token);
            std::getline(ss, token, ','); meta.withNTT = (token == "1");
            std::getline(ss, token, ','); meta.num_limbs = std::stoul(token);
            std::getline(ss, token, ','); meta.golden_norm = std::stod(token);
            std::getline(ss, token, ','); meta.total_bitflips = std::stoull(token);
            std::getline(ss, token, ','); meta.sdc_count = std::stoull(token);
            std::getline(ss, token, ','); meta.num_stages = std::stoul(token);
            std::getline(ss, token, ','); meta.duration_seconds = std::stoull(token);
            std::getline(ss, token, ','); meta.bitflips_per_second = std::stod(token);
            std::getline(ss, meta.data_file);

            campaigns.push_back(meta);
        }

        return campaigns;
    }

    // NUEVO: Escribir todas las campañas al CSV
    void write_all_campaigns(const std::vector<CampaignMetadata>& campaigns) {
        std::ofstream file(registry_filepath_);
        file << CampaignMetadata::csv_header() << "\n";

        for (const auto& campaign : campaigns) {
            file << campaign.to_csv_row() << "\n";
        }

        file.close();
    }

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

    // NUEVO: Actualizar campaña existente con función custom
    bool update_campaign(uint32_t campaign_id,
                        const std::function<void(CampaignMetadata&)>& updater) {
        std::lock_guard<std::mutex> lock(registry_mutex_);

        // Leer todas las campañas
        auto campaigns = read_all_campaigns();

        // Buscar y actualizar
        bool found = false;
        for (auto& campaign : campaigns) {
            if (campaign.campaign_id == campaign_id) {
                updater(campaign);  // Aplicar actualización
                found = true;
                break;
            }
        }

        if (!found) {
            return false;
        }

        // Reescribir todo el archivo
        write_all_campaigns(campaigns);

        return true;
    }

    // NUEVO: Finalizar campaña (conveniente)
    bool finalize_campaign(uint32_t campaign_id,
                          uint64_t total_bitflips,
                          uint64_t sdc_count,
                          uint64_t duration_seconds) {
        return update_campaign(campaign_id, [&](CampaignMetadata& meta) {
            meta.timestamp_end = get_timestamp();
            meta.total_bitflips = total_bitflips;
            meta.sdc_count = sdc_count;
            meta.duration_seconds = duration_seconds;

            if (duration_seconds > 0) {
                meta.bitflips_per_second = (double)total_bitflips / duration_seconds;
            }
        });
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

    // NUEVO: Obtener metadata de una campaña
    bool get_campaign(uint32_t campaign_id, CampaignMetadata& out_meta) {
        std::lock_guard<std::mutex> lock(registry_mutex_);

        auto campaigns = read_all_campaigns();

        for (const auto& campaign : campaigns) {
            if (campaign.campaign_id == campaign_id) {
                out_meta = campaign;
                return true;
            }
        }

        return false;
    }
};


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

    // NUEVO: Registry y timestamp
    CampaignRegistry* registry_ptr_;
    std::chrono::steady_clock::time_point start_time_;

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
    // Constructor actualizado con registry opcional
    CampaignLogger(uint32_t campaign_id,
                   const std::string& results_dir = "results/data",
                   size_t flush_threshold = 10000,
                   CampaignRegistry* registry = nullptr)  // <-- NUEVO PARÁMETRO
        : campaign_id_(campaign_id),
          buffer_size_(0),
          flush_threshold_(flush_threshold),
          total_entries_(0),
          sdc_count_(0),
          registry_ptr_(registry),                       // <-- NUEVO
          start_time_(std::chrono::steady_clock::now())  // <-- NUEVO
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
    void log_bitflip(uint32_t limb, uint32_t coeff,
                     uint32_t bit, const std::string& stage,
                     double norm2, double rel_error, bool is_sdc = false)
    {
        BitflipResult result{limb, coeff, bit, stage,
                            norm2, rel_error, is_sdc};
        log_bitflip(result);
    }

    uint64_t get_total_entries() const { return total_entries_; }
    uint64_t get_sdc_count() const { return sdc_count_; }

    // NUEVO: Obtener duración actual
    uint64_t get_elapsed_seconds() const {
        auto now = std::chrono::steady_clock::now();
        return std::chrono::duration_cast<std::chrono::seconds>(
            now - start_time_
        ).count();
    }

    // NUEVO: Forzar actualización del registro (opcional)
    void update_registry() {
        if (registry_ptr_) {
            registry_ptr_->finalize_campaign(
                campaign_id_,
                total_entries_,
                sdc_count_,
                get_elapsed_seconds()
            );
        }
    }

    ~CampaignLogger() {
        flush_buffer();
        data_file_.close();

        // NUEVO: Auto-actualizar registro si está disponible
        if (registry_ptr_) {
            std::cout << "Auto-updating campaign registry..." << std::endl;

            bool updated = registry_ptr_->finalize_campaign(
                campaign_id_,
                total_entries_,
                sdc_count_,
                get_elapsed_seconds()
            );

            if (updated) {
                std::cout << "✓ Registry updated" << std::endl;
            } else {
                std::cerr << "✗ Failed to update registry" << std::endl;
            }
        }

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


#endif // CAMPAIGN_LOGGER_HPP
