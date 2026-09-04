/* 
 Code to calculate de accuracy of the model
 */
#include "utils_nn.h"
#include "campaign_helper.h"
#include "campaign_logger.h"
#include "campaign_registry.h"
#include "backend_interface.h"
#include "utils_ckks.h"

const size_t INPUT_DIM = 784;
const size_t HIDDEN_DIM = 64;
const size_t OUTPUT_DIM = 10;
const double PIXEL_MAX = 255.0;
const std::string path = "../NN_config/data/";
int main(int argc, char* argv[]) {

    std::random_device rd;

    // 2. Initialize the standard Mersenne Twister engine with the seed
    std::mt19937 gen(rd());

    // 3. Define the range [inclusive, inclusive]
    std::uniform_int_distribution<int> distrib(1, 60000);
    std::cout << "\n=== Starting Single execution "<< std::endl;
    CampaignArgs args = parse_arguments(argc, argv);

    long logQ = args.logQ;
    long logP = args.logDelta;
    long logN = args.logN;
    long logSlots = args.logSlots;
    long slots = 1 << logSlots;
    long h = 64;

    size_t targetRow =  args.seed;
    size_t verbose =  args.verbose;

    assert(INPUT_DIM <= slots);

    HEEnv he(logN, logQ, h);


    auto W1  = loadCSVMatrix(path+"weights/W1.csv", HIDDEN_DIM, INPUT_DIM);
    auto b1  = loadCSVVector(path+"weights/b1.csv", HIDDEN_DIM);

    auto W2  = loadCSVMatrix(path+"weights/W2.csv", OUTPUT_DIM, HIDDEN_DIM);
    auto b2  = loadCSVVector(path+"weights/b2.csv", OUTPUT_DIM);

    assert(W1[0].size() == INPUT_DIM);
    assert(W2[0].size() == HIDDEN_DIM);
    EncodedWeights encoded =
        encodeWeights(he, W1, b1, W2, b2, slots, logP);
    vector<double> vals;
    size_t targetValue = 0;

    bool ok = loadMnistNormRowByIndex(
        path+"mnist_train.csv",
        targetRow,
        targetValue,
        vals
    );

    if(!ok){
        cerr << "Error loading MNIST image\n";
        return 1;
    }

    auto start_time = std::chrono::high_resolution_clock::now();
    uint32_t dummy = 0;
    IterationResult res = run_iteration_NN(he, encoded, vals, args, targetValue, dummy, dummy);
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> duration = end_time - start_time;
    std::cout << "Time: " << duration.count() << " s, output: " << !res.detected << std::endl;
    return 0;
}
