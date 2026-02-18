#include "utils_nn.h"
#include "backend_interface.h"

EncodedWeights encodeWeights(
    HEEnv& he,
    const vector<vector<double>>& W1,
    const vector<double>& b1,
    const vector<vector<double>>& W2,
    const vector<double>& b2,
    long slots,
    long logP
){
    EncodedWeights ew;

    size_t HIDDEN = W1.size();
    size_t INPUT  = W1[0].size();
    size_t OUTPUT = W2.size();

    ew.W1.resize(HIDDEN);

    vector<double> buffer(slots, 0.0);

    for(size_t j=0;j<HIDDEN;++j){
        fill(buffer.begin(), buffer.end(), 0.0);

        for(size_t i=0;i<INPUT;++i)
            buffer[i] = W1[j][i];

        ew.W1[j] = he.context.encode(buffer.data(), slots, logP);
    }

    ew.b1 = b1;

    ew.W2.resize(OUTPUT, vector<ZZX>(HIDDEN));

    for(size_t o=0;o<OUTPUT;++o){
        for(size_t h=0;h<HIDDEN;++h){

            fill(buffer.begin(), buffer.end(), W2[o][h]);

            ew.W2[o][h] = he.context.encode(buffer.data(), slots, logP);
        }
    }

    ew.b2 = b2;

    return ew;
}
Ciphertext encryptInput(
    HEEnv& he,
    const vector<double>& vals,
    long slots,
    long logP,
    long logQ
){
    vector<complex<double>> arr(slots, {0,0});

    for(size_t i=0;i<vals.size();++i)
        arr[i] = {vals[i],0};

    Plaintext pt = he.scheme.encode(arr.data(), slots, logP, logQ);

    return he.scheme.encryptMsg(pt);
}
Ciphertext chebyTanh3(
    HEEnv& he,
    Ciphertext x,
    long logP
){
    // x^2
    Ciphertext x2 = he.scheme.square(x);
    he.scheme.reScaleByAndEqual(x2, logP);

    // x^3
    Ciphertext x3 = he.scheme.mult(x2, x);
    he.scheme.reScaleByAndEqual(x3, logP);

    // -0.23*x^3
    he.scheme.multByConstAndEqual(x3, -0.23, logP);
    he.scheme.reScaleByAndEqual(x3, logP);

    // 0.98*x
    he.scheme.multByConstAndEqual(x, 0.98, logP);
    he.scheme.reScaleByAndEqual(x, logP);

    he.scheme.addAndEqual(x3, x);

    return x3;
}

void reduceSum(
    HEEnv& he,
    Ciphertext& ct,
    long logSlots
){
    for(int i=0;i<logSlots;i++){
        Ciphertext rot = he.scheme.leftRotateFast(ct, 1<<i);
        he.scheme.addAndEqual(ct, rot);
    }
}

vector<Ciphertext> forward(
    HEEnv& he,
    Ciphertext c,
    EncodedWeights& ew,
    long logSlots,
    long logP
)
{
    size_t HIDDEN = ew.W1.size();
    size_t OUTPUT = ew.W2.size();

    vector<Ciphertext> layer1(HIDDEN);
    for(size_t j=0;j<HIDDEN;++j){

        Ciphertext s = he.scheme.multByPoly(c, ew.W1[j], logP);
        he.scheme.reScaleByAndEqual(s, logP);

        reduceSum(he, s, logSlots);

        he.scheme.addConstAndEqual(s, ew.b1[j]);

        // Chebyshev tanh
        s = chebyTanh3(he, std::move(s), logP);

        layer1[j] = std::move(s);
    }

    vector<Ciphertext> out(OUTPUT);
    for(size_t o=0;o<OUTPUT;++o){

        Ciphertext acc = he.scheme.multByPoly(layer1[0], ew.W2[o][0], logP);
        he.scheme.reScaleByAndEqual(acc, logP);

        for(size_t h=0;h<HIDDEN;++h){
            Ciphertext term = he.scheme.multByPoly(layer1[h], ew.W2[o][h], logP);
            he.scheme.reScaleByAndEqual(term, logP);
            he.scheme.addAndEqual(acc, term);
        }

        he.scheme.addConstAndEqual(acc, ew.b2[o]);

        out[o] = std::move(acc);
    }

    return out;
}
vector<double> decryptLogits(
    HEEnv& he,
    vector<Ciphertext>& outs
){
    vector<double> res(outs.size());

    for(size_t i=0;i<outs.size();++i){

        unique_ptr<complex<double>[]> tmp(
            he.scheme.decrypt(he.sk, outs[i])
        );

        res[i] = tmp[0].real();
    }

    return res;
}

bool loadMnistNormRowByIndex(const std::string &csvPath, size_t rowIndex,
                         size_t &outLabel, std::vector<double> &pixelsOut)
{
    std::ifstream file(csvPath);
    if (!file.is_open()) {
        std::cerr << "Error: no se pudo abrir " << csvPath << "\n";
        return false;
    }

    std::string line;
    size_t currentRow = 0;

    while (std::getline(file, line)) {
        if (currentRow == rowIndex) {

            std::stringstream ss(line);
            std::string cell;

            // label
            if (!std::getline(ss, cell, ',')) {
                std::cerr << "Error: fila vacía en índice " << rowIndex << "\n";
                return false;
            }

            outLabel = std::stoi(cell);

            pixelsOut.clear();
            pixelsOut.reserve(784);

            // -------- normalization parameters --------
            constexpr double inv255 = 1.0 / 255.0;

            // Map to [-1, 1]  (BEST for Chebyshev)
            // x_norm = 2*(x/255) - 1

            while (std::getline(ss, cell, ',')) {

                int pixel = std::stoi(cell);
                pixel = std::clamp(pixel, 0, 255);

                double x = static_cast<double>(pixel) * inv255; // [0,1]
                x = 2.0 * x - 1.0;                              // [-1,1]

                pixelsOut.push_back(x);
            }

            if (pixelsOut.size() != 784) {
                std::cerr << "Error: fila " << rowIndex
                          << " tiene " << pixelsOut.size()
                          << " píxeles (esperado: 784)\n";
                return false;
            }

            return true;
        }

        ++currentRow;
    }

    std::cerr << "Error: índice " << rowIndex
              << " fuera de rango (total filas: " << currentRow << ")\n";

    return false;
}



std::vector<std::vector<double>> loadCSVMatrix(const std::string& path, size_t rows, size_t cols) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("No se pudo abrir " + path);
    }

    std::vector<std::vector<double>> matrix(rows, std::vector<double>(cols));
    std::string line, cell;
    size_t r = 0;

    while (std::getline(file, line) && r < rows) {
        std::stringstream ss(line);
        size_t c = 0;
        while (std::getline(ss, cell, ',') && c < cols) {
            matrix[r][c] = std::stod(cell);
            c++;
        }
        r++;
    }

    return matrix;
}

std::vector<double> loadCSVVector(const std::string& path, size_t size) {
    std::ifstream file(path);
    std::vector<double> data;
    data.reserve(size); // Reservamos para eficiencia

    if (!file.is_open()) {
        throw std::runtime_error("No se pudo abrir " + path);
    }

    std::string line, cell;
    while (std::getline(file, line) && data.size() < size) {
        std::stringstream ss(line);
        while (std::getline(ss, cell, ',') && data.size() < size) {
            data.push_back(std::stod(cell));
        }
    }

    if (data.size() != size) {
        throw std::runtime_error("Error: cantidad de valores leídos (" +
                                 std::to_string(data.size()) +
                                 ") no coincide con size esperado (" +
                                 std::to_string(size) + ")");
    }

    return data;
}


IterationResult run_iteration_NN(HEEnv& he, EncodedWeights encoded, const vector<double>& vals, CampaignArgs& args, size_t targetValue, std::optional<IterationArgs> iterArgs){

    size_t logSlots = args.logSlots;
    size_t slots = 1 << logSlots;
    size_t logP = args.logDelta;
    size_t logQ = args.logQ;
    size_t verbose = args.verbose;


    vector<complex<double>> arr(slots, {0,0});

    for(size_t i=0;i<vals.size();++i)
        arr[i] = {vals[i],0};

    Plaintext plain = he.scheme.encode(arr.data(), slots, logP, logQ);

    if (iterArgs && args.stage == "encode") {
        SwitchBit(plain.mx[iterArgs->coeff], iterArgs->bit);
    }
    Ciphertext c = he.scheme.encryptMsg(plain, ZZ(args.seed));

    if (iterArgs) {
        if (args.stage == "encrypt_c0") {
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }

    if(args.verbose)
        cout << "Running encrypted inference..." << endl;
    auto outputs = forward(
        he,
        c,
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
    IterationResult res;
    res.detected = (pred == targetValue);
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
    return res;
}

/// Server side bit flip/ ////
///
Ciphertext chebyTanh3OP(
    HEEnv& he,
    Ciphertext c,
    long logP,
    CampaignArgs& args, std::optional<IterationArgs> iterArgs, uint32_t hidden
){
    if(args.verbose)
        cout << hidden << ", ";
    if (hidden>0 && iterArgs && args.doMul==1) {
        if (args.stage == "encrypt_c0") {
            cout << "Bit: " << iterArgs->bit << ": " << c.bx[iterArgs->coeff] << ", ";
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
            cout << c.bx[iterArgs->coeff] << endl;
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }
    // x^2
    Ciphertext x2 = he.scheme.square(c);
    he.scheme.reScaleByAndEqual(x2, logP);

    if (hidden>0 && iterArgs && args.doMul==2) {
        if (args.stage == "encrypt_c0") {
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }
    // x^3
    Ciphertext x3 = he.scheme.mult(x2, c);
    he.scheme.reScaleByAndEqual(x3, logP);

    // -0.23*x^3
    he.scheme.multByConstAndEqual(x3, -0.23, logP);
    he.scheme.reScaleByAndEqual(x3, logP);
    if (hidden>0 && iterArgs && args.doScalarMul>0) {
        if (args.stage == "encrypt_c0") {
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }
    // 0.98*x
    he.scheme.multByConstAndEqual(c, 0.98, logP);
    he.scheme.reScaleByAndEqual(c, logP);

    he.scheme.addAndEqual(x3, c);

    return x3;
}

vector<Ciphertext> forwardOP(
    HEEnv& he,
    Ciphertext c,
    EncodedWeights& ew,
    long logSlots,
    long logP,
    CampaignArgs& args, std::optional<IterationArgs> iterArgs
)
{
    size_t HIDDEN = ew.W1.size();
    size_t OUTPUT = ew.W2.size();

    vector<Ciphertext> layer1(HIDDEN);
    uint32_t hidden = random_int(0, HIDDEN-1);
    if(args.verbose)
        cout << "Hidden bitflip: ";
    for(size_t j=0;j<HIDDEN;++j){

        Ciphertext s = he.scheme.multByPoly(c, ew.W1[j], logP);
        he.scheme.reScaleByAndEqual(s, logP);

        reduceSum(he, s, logSlots);

        he.scheme.addConstAndEqual(s, ew.b1[j]);

        // Chebyshev tanh
        s = chebyTanh3OP(he, std::move(s), logP, args, iterArgs, hidden==j);

        layer1[j] = std::move(s);
    }
    if(args.verbose)
        cout << endl;

    vector<Ciphertext> out(OUTPUT);
    for(size_t o=0;o<OUTPUT;++o){

        Ciphertext acc = he.scheme.multByPoly(layer1[0], ew.W2[o][0], logP);
        he.scheme.reScaleByAndEqual(acc, logP);

        for(size_t h=0;h<HIDDEN;++h){
            Ciphertext term = he.scheme.multByPoly(layer1[h], ew.W2[o][h], logP);
            he.scheme.reScaleByAndEqual(term, logP);
            he.scheme.addAndEqual(acc, term);
        }

        he.scheme.addConstAndEqual(acc, ew.b2[o]);

        out[o] = std::move(acc);
    }

    return out;
}

IterationResult run_iteration_NNOp(HEEnv& he, EncodedWeights encoded, const vector<double>& vals, CampaignArgs& args, size_t targetValue, std::optional<IterationArgs> iterArgs){

    size_t logSlots = args.logSlots;
    size_t slots = 1 << logSlots;
    size_t logP = args.logDelta;
    size_t logQ = args.logQ;
    size_t verbose = args.verbose;


    vector<complex<double>> arr(slots, {0,0});

    for(size_t i=0;i<vals.size();++i)
        arr[i] = {vals[i],0};

    Plaintext plain = he.scheme.encode(arr.data(), slots, logP, logQ);

    Ciphertext c = he.scheme.encryptMsg(plain, ZZ(args.seed));

    if(args.verbose)
        cout << "Running encrypted inference..." << endl;
    auto outputs = forwardOP(
        he,
        c,
        encoded,
        logSlots,
        logP,
        args, iterArgs
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
    IterationResult res;
    res.detected = (pred == targetValue);
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
    return res;
}
