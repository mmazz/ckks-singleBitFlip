#include "campaign_registry.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <stdexcept>
#include <type_traits>

namespace fs = std::filesystem;

namespace {

template <typename... Ts>
std::string joinCsvFields(const Ts&... fields)
{
    std::ostringstream oss;
    bool first = true;

    auto append = [&](const auto& value) {
        if (!first) oss << ',';
        first = false;

        using ValueT = std::decay_t<decltype(value)>;
        if constexpr (std::is_same_v<ValueT, std::string>) {
            oss << CampaignRegistry::csvEscape(value);
        } else {
            oss << value;
        }
    };

    (append(fields), ...);
    return oss.str();
}

} // namespace

CampaignRegistry::FileLock::FileLock(const std::string& path)
{
    fd_ = open(path.c_str(), O_CREAT | O_RDWR, 0666);
    if (fd_ < 0) {
        throw std::runtime_error(
            "CampaignRegistry: no se pudo abrir el lockfile '" + path +
            "' (errno=" + std::to_string(errno) + ")");
    }

    if (flock(fd_, LOCK_EX) != 0) {
        int err = errno;
        close(fd_);
        fd_ = -1;
        throw std::runtime_error(
            "CampaignRegistry: no se pudo tomar flock sobre '" + path +
            "' (errno=" + std::to_string(err) + ")");
    }
}

CampaignRegistry::FileLock::~FileLock()
{
    if (fd_ >= 0) {
        flock(fd_, LOCK_UN);
        close(fd_);
    }
}

std::string CampaignRegistry::csvEscape(const std::string& field)
{
    bool needsQuoting = field.find_first_of(",\"\n\r") != std::string::npos;
    if (!needsQuoting)
        return field;

    std::string escaped = "\"";
    for (char c : field) {
        if (c == '"')
            escaped += "\"\"";
        else
            escaped += c;
    }
    escaped += "\"";
    return escaped;
}

std::string CampaignRegistry::makeCampaignKey(const CampaignArgs& args)
{
    return joinCsvFields(
        args.library, args.stage, args.logN, args.logQ, args.bitPerCoeff,
        args.logDelta, args.logSlots, args.withNTT, args.mult_depth,
        args.doAdd, args.doPlainMul, args.doMul, args.doScalarMul,
        args.doRot, args.doBoot, args.op_index, args.op_step, args.seed,
        args.seed_input, args.isComplex, args.logMin, args.logMax,
        args.isExhaustive, args.dnum, args.scaleTech);
}

void CampaignRegistry::ensureCsvFilesExist()
{
    if (!fs::exists(start_csv_)) {
        std::ofstream f(start_csv_);
        if (!f)
            throw std::runtime_error("CampaignRegistry: no se pudo crear " + start_csv_);

        f << "campaign_id,library,stage,logN,logQ,bitPerCoeff,logDelta,logSlots,"
             "withNTT,mult_depth,doAdd,doPlainMul,doMul,doScalarMul,doRot,doBoot,op_index,"
             "op_step,seed,seed_input,"
             "isComplex,logMin,logMax,isExhaustive,dnum,scaleTech\n";
    }

    if (!fs::exists(end_csv_)) {
        std::ofstream f(end_csv_);
        if (!f)
            throw std::runtime_error("CampaignRegistry: no se pudo crear " + end_csv_);

        f << "campaign_id,total_bitflips,sdc_count,"
             "duration_seconds,l2_P95,l2_P99,duration\n";
    }
}


CampaignRegistry::ScanResult CampaignRegistry::scanCsv(
    const std::string& csvFile,
    const std::string& key)
{
    ScanResult result;

    std::ifstream file(csvFile);
    if (!file.is_open())
        return result;

    std::string line;
    std::getline(file, line); // header

    while (std::getline(file, line)) {

        while (!line.empty() && (line.back() == '\r' || line.back() == '\n'))
            line.pop_back();

        if (line.empty())
            continue;

        auto comma = line.find(',');
        if (comma == std::string::npos)
            continue; // linea corrupta: la ignoramos en vez de crashear

        uint32_t id;
        try {
            id = static_cast<uint32_t>(std::stoul(line.substr(0, comma)));
        } catch (const std::exception&) {
            continue; // campaign_id corrupto: ignorar la linea
        }

        result.max_id = std::max(result.max_id, id);

        if (result.existing_id == kInvalidId &&
            line.compare(comma + 1, std::string::npos, key) == 0) {
            result.existing_id = id;
        }
    }

    return result;
}

uint32_t CampaignRegistry::findCampaignId(const std::string& csvFile, const std::string& key)
{
    return scanCsv(csvFile, key).existing_id;
}

CampaignRegistry::CampaignRegistry(const CampaignArgs& args)
{
    const std::string& results_dir = args.results_dir;
    fs::create_directories(results_dir);

    start_csv_ = results_dir + "/campaigns_start.csv";
    end_csv_   = results_dir + "/campaigns_end.csv";
    lockfile_  = results_dir + "/.registry.lock";

    // RAII: el lock se libera solo al salir del scope del constructor,
    // sea por return normal o por cualquier excepcion lanzada mas abajo.
    FileLock lock(lockfile_);

    ensureCsvFilesExist();

    const auto key = makeCampaignKey(args);
    const auto scan = scanCsv(start_csv_, key);

    if (scan.existing_id != kInvalidId) {
        if (args.existing_policy == ExistingCampaignPolicy::Fail) {
            throw std::runtime_error(
                "Campaign already exists id=" + std::to_string(scan.existing_id));
        }
        campaign_id = scan.existing_id;
    } else {
        campaign_id = scan.max_id + 1;

        std::ofstream f(start_csv_, std::ios::app);
        if (!f)
            throw std::runtime_error("CampaignRegistry: no se pudo abrir " + start_csv_ + " para escritura");

        f << campaign_id << "," << key << "\n";

        if (!f)
            throw std::runtime_error("CampaignRegistry: fallo al escribir en " + start_csv_);
    }
    // ~FileLock() libera el flock aca.
}

void CampaignRegistry::register_end(const CampaignEndRecord& r)
{
    FileLock lock(lockfile_);

    std::ofstream f(end_csv_, std::ios::app);
    if (!f)
        throw std::runtime_error("CampaignRegistry: no se pudo abrir " + end_csv_ + " para escritura");
    f << joinCsvFields(r.campaign_id, r.total_bitflips, r.sdc_count,
                        r.duration_seconds, r.l2_P95, r.l2_P99, r.duration)
      << "\n";
    if (!f)
        throw std::runtime_error("CampaignRegistry: fallo al escribir en " + end_csv_);
}
