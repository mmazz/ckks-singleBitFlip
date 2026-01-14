#include "HEAAN.h"

#include <cmath>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <stdexcept>
#include <random>
#include <filesystem>
using namespace std;
using namespace NTL;

int main(int argc, char *argv[])
{
    size_t boot    = 0;
    long logN      = 10;
    long logQ      = 620;
    long logq      = 29;
    long logp      = 23;
    long logT      = 3;
    long logSlots  = 3;
    unsigned seed  = 0;
    size_t ringDim = (1u << logN);
    long slots = 1 << logSlots;

    NTL::ZZ seed_NTL = ZZ(seed);
    NTL::SetSeed(seed_NTL);
    std::srand(seed);

    std::mt19937_64 rng(seed ? seed : std::random_device{}());
    std::uniform_real_distribution<double> unif(0.0, 1.0);


    complex<double>* vals = new complex<double>[slots];
    complex<double>* vals2 = new complex<double>[slots];
    complex<double>* vals3 = new complex<double>[slots];
    complex<double>* vals4 = new complex<double>[slots];
    complex<double>* valsMul = new complex<double>[slots];

    for (uint32_t i = 0; i < slots; i++) {
        double a = unif(rng);
        double b = unif(rng);
        double c = unif(rng);
        double d = unif(rng);

        vals[i]    = complex<double>(a, 0.0);
        vals2[i]   = complex<double>(b, 0.0);
        vals3[i]   = complex<double>(c, 0.0);
        vals4[i]   = complex<double>(d, 0.0);
        valsMul[i] = vals[i] * vals2[i] * vals3[i] * vals4[i];
        std::cout << vals[i] << "x" << vals2[i] << "x"<< vals3[i] << "x" << vals4[i] <<"=" << valsMul[i] << std::endl;
    }
    std::cout <<  std::endl;
    Context context(logN, logQ);
    SecretKey sk(logN);
    Scheme scheme(sk, context);
    scheme.addBootKey(sk, logSlots, logq + 4);
    Plaintext plain = scheme.encode(vals, slots, logp, logQ);
    Ciphertext cipher = scheme.encryptMsg(plain, seed_NTL);
    Plaintext plain2 = scheme.encode(vals2, slots, logp, logQ);
    Ciphertext cipher2 = scheme.encryptMsg(plain2, seed_NTL);
    Plaintext plain3 = scheme.encode(vals3, slots, logp, logQ);
    Ciphertext cipher3 = scheme.encryptMsg(plain3, seed_NTL);
    Plaintext plain4 = scheme.encode(vals4, slots, logp, logQ);
    Ciphertext cipher4 = scheme.encryptMsg(plain4, seed_NTL);

    std::cout << cipher.logq << ", " <<   cipher2.logq << ", " << cipher3.logq << ", " << cipher4.logq << ", " << std::endl;
    Ciphertext cipherMul = scheme.mult(cipher, cipher2);
    std::cout << "Before Rescale first mul: " <<  cipherMul.logq << std::endl;
    scheme.reScaleByAndEqual(cipherMul, logp);
    std::cout << "After Rescale first mul:  " <<  cipherMul.logq << std::endl;
    Ciphertext cipherMul1 = scheme.mult(cipherMul, cipher3);
    scheme.reScaleByAndEqual(cipherMul1, logp);
    std::cout << "After Rescale second mul:  " <<  cipherMul1.logq << std::endl;
    Ciphertext cipherMul2 = scheme.mult(cipherMul1, cipher4);
    scheme.reScaleByAndEqual(cipherMul2, logp);
    std::cout << "After Rescale third mul:   " <<  cipherMul2.logq << std::endl;
    cipherMul2.logq = logq;
    if(boot){
        scheme.bootstrapAndEqual(cipherMul2, cipherMul2.logq, logQ, logT);
    }
    Plaintext dec = scheme.decryptMsg(sk, cipherMul2);
    complex<double>* out = scheme.decode(dec);
    std::cout << "After bootstrap:           " <<  cipherMul2.logq << std::endl;
    for(size_t i=0; i<slots; i++){
        std::cout << out[i].real() << " vs " << valsMul[i].real() << std::endl;
    }

    return 0;
}
