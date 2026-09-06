#include "campaign_logger.h"


namespace fs = std::filesystem;

std::string BitflipResult::header() {
    return "limb,coeff,bit,l2_norm,rel_error,is_sdc,correct,degraded,corrupted,failed,hidden_layer,reduceSum_layer";
}

std::string BitflipResult::row() const {
    std::ostringstream ss;
    ss << limb << "," << coeff << "," << bit << ","
       << norm2 << ","
       << rel_error << "," << (is_sdc ? 1 : 0) << ","
       << stats.correct << "," << stats.degraded << ","
       << stats.corrupted << "," << stats.failed<< ","
       << hidden_layer << "," << reduceSum_layer;
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
    csv_path_ = path.str();

    const bool write_header =
        !fs::exists(csv_path_) || fs::file_size(csv_path_) == 0;

    file_.open(csv_path_, std::ios::out | std::ios::app);

    if (write_header) {
        file_ << BitflipResult::header() << "\n";
    }
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
          double norm2, double rel_error, bool is_sdc, SlotErrorStats stats,
          uint32_t hidden_layer, uint32_t reduceSum_layer)
    {
        BitflipResult r{
            limb,
            coeff,
            bit,
            norm2,
            rel_error,
            is_sdc,
            stats,
            hidden_layer,
            reduceSum_layer
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
    compress_and_cleanup();

}
void CampaignLogger::compress_and_cleanup() {
    std::string gz_path = csv_path_ + ".gz";

    std::string cmd = "gzip -f " + csv_path_;
    int ret = std::system(cmd.c_str());

    if (ret != 0) {
        std::cerr << "[WARN] gzip failed for " << csv_path_ << std::endl;
        return;
    }

    // gzip ya borra el .csv si usás -f
    std::cout << "[INFO] Compressed campaign data → " << gz_path << std::endl;
}

bool CampaignLogger::contains(const IterationArgs& args) const
{
    std::ifstream file(csv_path_);

    if (!file.is_open())
        return false;

    std::string line;

    // header
    std::getline(file, line);

    while (std::getline(file, line))
    {
        std::stringstream ss(line);
        std::string field;

        std::getline(ss, field, ',');
        uint32_t limb = std::stoul(field);

        std::getline(ss, field, ',');
        uint32_t coeff = std::stoul(field);

        std::getline(ss, field, ',');
        uint32_t bit = std::stoul(field);

        if (limb == args.limb &&
            coeff == args.coeff &&
            bit == args.bit)
        {
            return true;
        }
    }

    return false;
}


VectorLogger::VectorLogger(uint32_t id,
                           const std::string& dir,
                           uint32_t logSlot,
                           size_t flush_th)
    : log_slot_(logSlot),
      n_slots_(size_t{1} << logSlot),
      flush_threshold_(flush_th == 0 ? size_t{1} : flush_th)
{
    fs::create_directories(dir);
 
    std::ostringstream path;
    path << dir << "/campaign_" << std::setw(6)
         << std::setfill('0') << id << ".csv";
    csv_path_ = path.str();
 
    const bool fresh =
        !fs::exists(csv_path_) || fs::file_size(csv_path_) == 0;
 
    file_.open(csv_path_, std::ios::out | std::ios::app);
    if (!file_.is_open())
        throw std::runtime_error("VectorLogger: no se pudo abrir " + csv_path_);
 
    // 17 digitos significativos => el double se recupera exacto al leerlo.
    file_ << std::defaultfloat
          << std::setprecision(std::numeric_limits<double>::max_digits10);
 
    if (fresh) {
        file_ << header() << "\n";
    } else {
        // Estamos reanudando una campania: la fila de entrada ya esta escrita.
        input_written_ = true;
    }
}
 
VectorLogger::~VectorLogger() {
    close();
}
 
std::string VectorLogger::header() const {
    std::ostringstream ss;
    ss << "limb,coeff,bit";
    for (size_t i = 0; i < n_slots_; ++i)
        ss << ",v_" << i;
    return ss.str();
}
 
void VectorLogger::write_row_locked(long long limb,
                                    long long coeff,
                                    long long bit,
                                    const std::vector<double>& v)
{
    if (v.size() != n_slots_) {
        std::ostringstream e;
        e << "VectorLogger: se esperaban " << n_slots_
          << " slots (1<<" << log_slot_ << ") y llegaron " << v.size();
        throw std::invalid_argument(e.str());
    }
 
    file_ << limb << ',' << coeff << ',' << bit;
    for (double x : v)
        file_ << ',' << x;
    file_ << '\n';
 
    if (++since_flush_ >= flush_threshold_) {
        file_.flush();
        since_flush_ = 0;
    }
}
 
void VectorLogger::set_input(const std::vector<double>& input) {
    std::lock_guard<std::mutex> g(mtx_);
    if (input_written_) return;
    write_row_locked(kInputRowTag, kInputRowTag, kInputRowTag, input);
    input_written_ = true;
}
 
void VectorLogger::log(uint32_t limb, uint32_t coeff, uint32_t bit,
                       const std::vector<double>& output)
{
    std::lock_guard<std::mutex> g(mtx_);
    write_row_locked(limb, coeff, bit, output);
    total_++;
}
 
void VectorLogger::log(const IterationArgs& args,
                       const std::vector<double>& output)
{
    log(args.limb, args.coeff, args.bit, output);
}
 
void VectorLogger::log(uint32_t limb, uint32_t coeff, uint32_t bit,
                       const std::vector<double>& input,
                       const std::vector<double>& output)
{
    std::lock_guard<std::mutex> g(mtx_);
    if (!input_written_) {
        write_row_locked(kInputRowTag, kInputRowTag, kInputRowTag, input);
        input_written_ = true;
    }
    write_row_locked(limb, coeff, bit, output);
    total_++;
}
 
void VectorLogger::flush() {
    std::lock_guard<std::mutex> g(mtx_);
    if (file_.is_open()) file_.flush();
    since_flush_ = 0;
}
 
void VectorLogger::close() {
    std::lock_guard<std::mutex> g(mtx_);
    if (closed_) return;
    closed_ = true;
 
    if (file_.is_open()) {
        file_.flush();
        file_.close();
    }
    compress_and_cleanup();
}
 
void VectorLogger::compress_and_cleanup() {
    if (!fs::exists(csv_path_)) return;   // ya comprimido o nunca se escribio
 
    const std::string gz_path = csv_path_ + ".gz";
    const std::string cmd = "gzip -f \"" + csv_path_ + "\"";
 
    int ret = std::system(cmd.c_str());
    if (ret != 0) {
        std::cerr << "[WARN] gzip failed for " << csv_path_ << std::endl;
        return;
    }
 
    std::cout << "[INFO] Compressed campaign vectors -> " << gz_path << std::endl;
}
 
bool VectorLogger::contains(const IterationArgs& args) const
{
    std::lock_guard<std::mutex> g(mtx_);
 
    std::ifstream f(csv_path_);
    if (!f.is_open())
        return false;
 
    constexpr auto kMax = std::numeric_limits<std::streamsize>::max();
 
    f.ignore(kMax, '\n');   // header
 
    long long limb, coeff, bit;
    char sep;
    // Solo se parsean las 3 primeras columnas; el resto de la fila se saltea
    // sin materializarla (son cientos de KB por fila).
    while (f >> limb >> sep >> coeff >> sep >> bit) {
        f.ignore(kMax, '\n');
 
        if (limb < 0) continue;   // fila del vector de entrada
 
        if (static_cast<uint32_t>(limb)  == args.limb &&
            static_cast<uint32_t>(coeff) == args.coeff &&
            static_cast<uint32_t>(bit)   == args.bit)
        {
            return true;
        }
    }
 
    return false;
}

