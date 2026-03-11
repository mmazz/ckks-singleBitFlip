#include "openfhe.h"
#include "backend_interface.h"
using namespace lbcrypto;

struct OpenFHEContext final : BackendContext {
    CryptoContext<DCRTPoly> cc;
    KeyPair<DCRTPoly> keys;
    std::vector<double> baseInput;
    std::vector<double> goldenOutput;
    PRNG* prng;
};


Ciphertext<DCRTPoly> gen_cipher(BackendContext* bctx,
              const CampaignArgs& args,
                std::optional<IterationArgs> iterArgs = std::nullopt);
