#include "utils_nn.h"

const size_t INPUT_DIM = 784;
const size_t HIDDEN_DIM = 64;
const size_t OUTPUT_DIM = 10;
const double PIXEL_MAX = 255.0;
const std::string path = "data/mnist_train.csv";

int main(int argc, char* argv[]) {

    long logQ = 220;
    long logP = 30;
    long logN = 12;
    long logSlots = 10;
    long slots = 1 << logSlots;
    long h = 64;

    size_t targetRow =  std::stoi(argv[1]);;
    size_t verbose =  std::stoi(argv[2]);;
    assert(INPUT_DIM <= slots);
    if(verbose)
        cout << "Initializing HE..." << endl;

    HEEnv he(logN, logQ, h);

    if(verbose)
        cout << "Loading weights..." << endl;

    auto W1  = loadCSVMatrix("data/weights/W1.csv", HIDDEN_DIM, INPUT_DIM);
    auto b1  = loadCSVVector("data/weights/b1.csv", HIDDEN_DIM);

    auto W2  = loadCSVMatrix("data/weights/W2.csv", OUTPUT_DIM, HIDDEN_DIM);
    auto b2  = loadCSVVector("data/weights/b2.csv", OUTPUT_DIM);
    assert(W1[0].size() == INPUT_DIM);
    assert(W2[0].size() == HIDDEN_DIM);



    if(verbose)
        cout << "Encoding weights..." << endl;

    EncodedWeights encoded =
        encodeWeights(he, W1, b1, W2, b2, slots, logP);

    if(verbose)
        cout << "Ready for inference.\n" << endl;

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
        cout << "Encrypting input..." << endl;

    Ciphertext x = encryptInput(he, vals, slots, logP, logQ);

    if(verbose)
        cout << "Running encrypted inference..." << endl;

    auto outputs = forward(
        he,
        x,
        encoded,
        logSlots,
        logP
    );

    if(verbose)
        cout << "Decrypting..." << endl;

    auto logits = decryptLogits(he, outputs);


    size_t pred = 0;
    double best = logits[0];

    for(size_t i=1;i<logits.size();++i){
        if(logits[i] > best){
            best = logits[i];
            pred = i;
        }
    }

    if(verbose){
        cout << "\nPrediction: " << pred
             << "\nTarget:     " << targetValue
             << endl;

        if(pred == targetValue)
            cout << "✔ Correct\n";
        else
            cout << "✘ Incorrect\n";
    }
    else{
        if(pred == targetValue)
            cout << 1 << std::endl;
        else
            cout << 0 << std::endl;
    }
}
