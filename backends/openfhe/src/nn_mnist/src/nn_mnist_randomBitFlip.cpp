
#include "campaign_helper.h"
#include "campaign_logger.h"
#include "campaign_registry.h"
#include "backend_interface.h"
#include "utils_nn.h"

const size_t INPUT_DIM = 784;
const size_t HIDDEN_DIM = 64;
const size_t OUTPUT_DIM = 10;
const double PIXEL_MAX = 255.0;
const std::string path = "../../../heaan/src/nn_mnist/data/mnist_train.csv";
size_t NUM_BITFLIPS = 5;

int main(int argc, char* argv[]) {

    std::cout << "\n=== Starting Campaign "<< std::endl;
    CampaignArgs args = parse_arguments(argc, argv);
    args.library = "openfheNN";
    args.isExhaustive= false;

    if (args.verbose) {
        args.print();
    }

    long logQ = args.logQ;
    long logP = args.logDelta;
    long multDepth = args.mult_depth;
    long logN = args.logN;
    long logSlots = args.logSlots;
    long slots = 1 << logSlots;

    size_t targetRow =  args.seed;
    size_t verbose =  args.verbose;

    assert(INPUT_DIM <= slots);
    if(verbose)
        std::cout << "Initializing HE..." << std::endl;

    HEEnv he(logN, multDepth, logP, logQ);

    if(verbose)
        std::cout << "Loading weights..." << std::endl;

    auto W1  = loadCSVMatrix("../../../heaan/src/nn_mnist/data/weights/W1.csv", HIDDEN_DIM, INPUT_DIM);
    auto b1  = loadCSVVector("../../../heaan/src/nn_mnist/data/weights/b1.csv", HIDDEN_DIM);
    auto W2  = loadCSVMatrix("../../../heaan/src/nn_mnist/data/weights/W2.csv", OUTPUT_DIM, HIDDEN_DIM);
    auto b2  = loadCSVVector("../../../heaan/src/nn_mnist/data/weights/b2.csv", OUTPUT_DIM);
    assert(W1[0].size() == INPUT_DIM);
    assert(W2[0].size() == HIDDEN_DIM);



    if(verbose)
        std::cout << "Encoding weights..." << std::endl;

    EncodedWeights encoded =
        encodeWeights(he, W1, b1, W2, b2, slots);

    if(verbose)
        std::cout << "Ready for inference.\n" << std::endl;

    vector<double> vals;
    size_t targetValue;

    bool ok = loadMnistNormRowByIndex(
        path,
        targetRow,
        targetValue,
        vals
    );

    if(!ok){
        cerr << "Error loading MNIST image\n";
        return 1;
    }


    if(verbose)
        std::cout << "Encrypting input..." << std::endl;

    IterationResult res = run_iteration_NN(he, encoded, vals, args, targetValue);
    if(res.detected)
    {
        args.results_dir = "../../../../results_NN";
        CampaignRegistry registry(args.results_dir);
        uint32_t campaign_id = registry.allocate_campaign_id();
        std::cout << "\n=== Registring Campaign "<< std::endl;
        registry.register_start({
                campaign_id,
                args,
                ""});

        std::cout << "\n=== Starting Campaign " << campaign_id << " ===" << std::endl;

        CampaignLogger logger(
            campaign_id,
            args.results_dir + "/data",
            10000);

        std::cout << "Campaign " << campaign_id << " registered" << std::endl;



        auto start_time = std::chrono::high_resolution_clock::now();

        // ========== 10. LOOP DE BIT FLIPS ==========
        std::cout << "\nStarting bit flip campaign..." << std::endl;

        uint32_t N = 1 << args.logN;
        size_t num_bitFlips = NUM_BITFLIPS;
        std::vector<double> norms;
        norms.reserve(num_bitFlips);

        std::cout << "Total bit flips: " << num_bitFlips*14 << std::endl;

        std::mt19937 rng(args.seed);

        std::vector<uint32_t> bits_to_flip = bitsToFlipGenerator(args); // 10 values
        for (size_t bitIndex = 0; bitIndex < bits_to_flip.size() ; bitIndex++) {
            uint32_t bit = bits_to_flip[bitIndex];
            for (size_t i = 0; i < num_bitFlips; i++) {
                uint32_t coeff = random_int(0, N-1);
                IterationArgs iterArgs(0, coeff, bit);
                IterationResult res = run_iteration_NN(he, encoded, vals, args, targetValue, iterArgs);
                SlotErrorStats  stats;
                logger.log(iterArgs.limb,
                        iterArgs.coeff,
                        iterArgs.bit,
                        0.0, 0.0,
                        !res.detected,     // is_sdc: predict correct or not, we need to negate. 1 will be sdc, bad. 0 will be mask, good.
                        stats
                        );
            }

        }
        auto end_time = std::chrono::high_resolution_clock::now();
        std::chrono::seconds duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
        auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration);
        uint64_t mins = minutes.count();

        registry.register_end({campaign_id, logger.total(), logger.sdc(), mins, 0.0, 0.0, timestamp_now()});
    } else {
        std::cout << "Wrong prediction of clean NN" << std::endl;
    }

    return 0;
}
