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

bool integrityChequer(Ciphertext<DCRTPoly>& cx){
    bool corrupt = false;
    DCRTPoly c = cx->GetElements()[0];
    size_t N = c.GetParams()->GetCyclotomicOrder();
    c.SetFormat(Format::COEFFICIENT);
    Poly c1 = c.CRTInterpolate();
    const Poly::Integer mod = c1.GetModulus();

    size_t coeff = 0;
    while(corrupt==false && coeff<N){
        corrupt = coeffIntegrityCheck(c1, coeff, mod);
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
    lbcrypto::Ciphertext<lbcrypto::DCRTPoly> goldenCKKS_cipher = gen_cipher(ctx, args);

    bool chequer =  integrityChequer(goldenCKKS_cipher);
    std::cout << chequer << std::endl;
  //  goldenCKKS_cipher.CRTInterpolate();

 //   if(AcceptCKKSResult(baseline_metrics)){
 //       auto start_time = std::chrono::high_resolution_clock::now();

 //       uint32_t N = 1 << args.logN;
 //       size_t num_bitFlips = NUM_BITFLIPS;


 //       std::cout << "Total bit flips: " << num_bitFlips << std::endl;

 //       std::vector<uint32_t> bits_to_flip = bitsToFlipGenerator(args); // 10 values
 //       for (size_t bitIndex = 0; bitIndex < bits_to_flip.size() ; bitIndex++) {
 //           uint32_t bit = bits_to_flip[bitIndex];
 //           std::cout << bit << std::endl;
 //           for (size_t i = 0; i < num_bitFlips; i++) {
 //               uint32_t limb = random_int(0, args.mult_depth);
 //               uint32_t coeff = random_int(0, N-1);
 //               IterationArgs iterArgs(limb, coeff, bit);
 //               IterationResult res = run_iteration(ctx, args, iterArgs);

 //           }
 //       }

 //   auto end_time = std::chrono::high_resolution_clock::now();
 //   std::chrono::seconds duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
 //   auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration);
 //   uint64_t mins = minutes.count();

 //   } else {
 //       printBaselineComparison(
 //           goldenOutput,
 //           goldenCKKS_output.values,
 //           baseline_metrics
 //       );
 //   }
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
