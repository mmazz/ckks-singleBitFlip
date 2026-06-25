#pragma once
#include <string>
#include <cstdint>
#include <limits>
#include <chrono>
#include <sys/file.h>
#include "campaign_helper.h"

struct CampaignStartRecord {
    uint32_t campaign_id;
    CampaignArgs args;
};

struct CampaignEndRecord {
    uint32_t campaign_id;
    uint64_t total_bitflips;
    uint64_t sdc_count;
    uint64_t duration_seconds;
    double l2_P95;
    double l2_P99;
    std::string duration;
};

class CampaignRegistry {
public:
    explicit CampaignRegistry(const CampaignArgs& args);

    // Mantenidos por compatibilidad con codigo existente que ya los llame.
    // Internamente el constructor ya NO los usa por separado: hace un unico
    // pase combinado (ver scanCsv) para no leer el archivo dos veces bajo lock.
    uint32_t findCampaignId(const std::string& csvFile, const std::string& key);
    uint32_t allocate_campaign_id();

    std::string makeCampaignKey(const CampaignArgs& args);
    void register_end(const CampaignEndRecord& rec);

    uint32_t campaign_id;

    static std::string csvEscape(const std::string& field);
private:
    static constexpr uint32_t kInvalidId = std::numeric_limits<uint32_t>::max();

    std::string start_csv_;
    std::string end_csv_;
    std::string lockfile_;

    // RAII: toma flock exclusivo al construirse y SIEMPRE lo libera al
    // destruirse (incluso si algo lanza una excepcion mientras el lock
    // esta tomado). Reemplaza al par manual lock_file()/unlock_file().
    class FileLock {
    public:
        explicit FileLock(const std::string& path);
        ~FileLock();
        FileLock(const FileLock&) = delete;
        FileLock& operator=(const FileLock&) = delete;
    private:
        int fd_ = -1;
    };

    struct ScanResult {
        uint32_t existing_id = kInvalidId;
        uint32_t max_id = 0;
    };

    // Un solo pase por el CSV: busca `key` y de paso calcula el mayor
    // campaign_id existente, para poder asignar el siguiente sin tener
    // que volver a recorrer el archivo. Tolera lineas corruptas/parciales
    // (las ignora en vez de tirar una excepcion no atrapada).
    static ScanResult scanCsv(const std::string& csvFile, const std::string& key);


    void ensureCsvFilesExist();
};
