#include "openfhe.h"
#include "campaign_helper.h"
#include "campaign_logger.h"
#include "campaign_registry.h"
#include "backend_interface.h"
#include "backend_openfhe.h"
#include "utils_ckks.h"

size_t NUM_BITFLIPS = 500;

bool coeffIntegrityCheck(Poly& c, size_t coeff, const Poly::Integer mod){
    auto c_coeff = c.GetValues()[coeff];
    bool bigger = c_coeff > mod;
    return bigger;
}

double bitUniform(Poly& c, const Poly::Integer mod, size_t N) {
    size_t logMod = mod.GetMSB();
    auto c_coeffs = c.GetValues();
    double worst = 0.0;
    for (size_t bit = 0; bit < logMod; bit++) {
        size_t ones = 0;
        for (size_t coeff = 0; coeff < N; coeff++) {
            uschar bitval = c_coeffs[coeff].GetBitAtIndex(bit);
            if (bitval)
                ones++;
        }
        double ratio = ones / (double)N;
        double deviation = std::abs(ratio - 0.5);

        worst = std::max(worst, deviation);
    }
    return worst;
}

double cipherBitUniform(Ciphertext<DCRTPoly>& cx){
    DCRTPoly c0 = cx->GetElements()[0];
    DCRTPoly c1 = cx->GetElements()[1];
    size_t N = c0.GetRingDimension();
    c0.SetFormat(Format::COEFFICIENT);
    c1.SetFormat(Format::COEFFICIENT);
    Poly c0_p = c0.CRTInterpolate();
    Poly c1_p = c1.CRTInterpolate();
    const Poly::Integer mod  = c0_p.GetModulus();
    double c0_worst = bitUniform(c0_p, mod, N);
    double c1_worst = bitUniform(c1_p, mod, N);
    std::cout << c0_worst << ", " << c1_worst << std::endl;
    return std::max(c0_worst, c1_worst);
}

bool integrityChequer(Ciphertext<DCRTPoly>& cx){
    bool corrupt = false;
    DCRTPoly c0 = cx->GetElements()[0];
    DCRTPoly c1 = cx->GetElements()[1];
    size_t N = c0.GetRingDimension();
    c0.SetFormat(Format::COEFFICIENT);
    c1.SetFormat(Format::COEFFICIENT);
    Poly c0_p = c0.CRTInterpolate();
    Poly c1_p = c1.CRTInterpolate();
    const Poly::Integer mod  = c0_p.GetModulus();
    size_t coeff = 0;
    while(corrupt==false && coeff<N){
        corrupt = coeffIntegrityCheck(c0_p, coeff, mod) && coeffIntegrityCheck(c1_p, coeff, mod);
        coeff++;
    }
    return corrupt;
}

int main(int argc, char* argv[]) {
    CampaignArgs args = parse_arguments(argc, argv);
    args.library = "openfhe";
    args.isExhaustive= false;
    if (args.verbose) {
        args.print();
    }

    BackendContext* ctx = setup_campaign(args);
    IterationResult goldenCKKS_output = run_iteration(ctx, args);

    const auto& goldenOutput = get_reference_output(ctx);
    CKKSAccuracyMetrics baseline_metrics = EvaluateCKKSAccuracy(goldenOutput, goldenCKKS_output.values);
    IterationChequer chequerRes = gen_cipher(ctx, args);
    cipherBitUniform(chequerRes.cipher);
    if(AcceptCKKSResult(baseline_metrics)){
        auto start_time = std::chrono::high_resolution_clock::now();

        uint32_t N = 1 << args.logN;
        size_t num_bitFlips = NUM_BITFLIPS;


        std::cout << "Total bit flips: " << num_bitFlips << std::endl;

        std::vector<uint32_t> bits_to_flip = bitsToFlipGenerator(args); // 10 values
        for (size_t bitIndex = 0; bitIndex < bits_to_flip.size() ; bitIndex++) {
            uint32_t bit = bits_to_flip[bitIndex];
          std::cout << bit << std::endl;
            for (size_t i = 0; i < num_bitFlips; i++) {
                uint32_t limb = random_int(0, args.mult_depth);
                uint32_t coeff = random_int(0, N-1);
                IterationArgs iterArgs(limb, coeff, bit);
                IterationChequer chequerRes = gen_cipher(ctx, args, iterArgs);
                cipherBitUniform(chequerRes.cipher);
     //           bool chequer =  integrityChequer(chequerRes.cipher);
       //         std::cout << "Integrity chequer: " <<  chequer  << ", Openfhe detection: " << chequerRes.detected << std::endl;
                std::cout << "Openfhe detection: " << chequerRes.detected << std::endl;
            }
        }

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::seconds duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
    auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration);
    uint64_t mins = minutes.count();
    std::cout << "Time: " << mins << std::endl;

    } else {
        printBaselineComparison(
            goldenOutput,
            goldenCKKS_output.values,
            baseline_metrics
        );
    }
    return 0;
}
// ========== 11. FINALIZAR ==========

//    std::cout << "\n=== Campaign " << campaign_id << " Complete ===" << std::endl;
//    std::cout << "Total bit flips: " << logger.get_total_entries() << std::endl;
//    std::cout << "SDC detected: " << logger.get_sdc_count()
//              << " (" << std::fixed << std::setprecision(2)
//              << (100.0 * logger.get_sdc_count() / logger.get_total_entries())
//              << "%)" << std::endl;
//
//    std::cout << "Duration: " << duration << " seconds";
//    if (duration >= 3600) {
//        std::cout << " (" << (duration / 3600) << "h "
//                 << ((duration % 3600) / 60) << "m)";
//    } else if (duration >= 60) {
//        std::cout << " (" << (duration / 60) << "m "
//                 << (duration % 60) << "s)";
//    }
//    std::cout << std::endl;
//
//    double rate = (duration > 0) ? (double)logger.get_total_entries() / duration : 0.0;
//    std::cout << "Rate: " << std::fixed << std::setprecision(2)
//              << rate << " bit flips/second" << std::endl;
//
//    std::cout << "\nResults saved to:" << std::endl;
//    std::cout << "  Data: " << args.results_dir << "/data/"
//              << metadata.data_file << std::endl;
//    std::cout << "  Registry: " << args.results_dir << "/campaigns.csv"
//              << std::endl;
