#include "utils.cpp"
#include "HEAAN.h"
#include <cmath>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <stdexcept>

using namespace std;
using namespace NTL;

// Constantes para limitar valores mágicos
const long DEFAULT_LOG_N = 4;
const long DEFAULT_LOG_Q = 35;
const long DEFAULT_LOG_P = 25;
const unsigned int DEFAULT_MIN = 0;
const unsigned int DEFAULT_MAX = 8;
const size_t DEFAULT_LOOPS = 1;
const int DEFAULT_GAP_SHIFT = 0;
const size_t MAX_H = 64;

int main(int argc, char *argv[])
{
        std::cout << "logN "<< "logQ "<< "logP "<< "gap "<< "MIN "<<  "MAX "<< "loops "<< std::endl;

        unsigned int MIN_LOG = DEFAULT_MIN;
        unsigned int MAX_LOG = DEFAULT_MAX;
        size_t loops = DEFAULT_LOOPS;
        int gapShift = DEFAULT_GAP_SHIFT;

        if (argc > 1)
            logN = std::stol(argv[1]);
        if (argc > 2)
            logQ = std::stol(argv[2]);
        if (argc > 3)
            logP = std::stol(argv[3]);
        if (argc > 4)
            gapShift = std::stoi(argv[4]);
        if (argc > 5)
            MIN_LOG = std::stoi(argv[5]);
        if (argc > 6)
            MAX_LOG = std::stoi(argv[6]);
        if (argc > 7)
            loops = std::stoi(argv[7]);

        long h = pow(2, logN);
        if (h > MAX_H)
            h = MAX_H;

        size_t ringDim = (1 << logN);
        long logSlots = logN - 1;
        long slots = pow(2, logSlots);

        // Ajustar slots basado en gapShift
        if (gapShift > 0) {
            slots = slots >> gapShift;
        }
    return 0;
}
