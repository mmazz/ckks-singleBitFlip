#include "openfhe.h"

#include "campaign_helper.h"
#include "campaign_logger.h"
#include "campaign_registry.h"
#include "utils_openfhe.h"
#include "utils_ckks.h"




int main(int argc, char* argv[]) {
    const CampaignArgs args = parse_arguments(argc, argv);
    if (args.verbose) {
        args.print();
    }
    auto cfg = SDCConfigHelper::MakeConfig(
        false,
        args.attackMode,
        args.thresholdBitsSKA
    );

    SDCConfigHelper::SetGlobalConfig(cfg);

    CampaignRegistry registry(args.results_dir);
    uint32_t campaign_id = registry.allocate_campaign_id();
    std::cout << "\n=== Registring Campaign "<< std::endl;
    registry.register_start({
        campaign_id,
        args,
        ""
    });

    std::cout << "\n=== Starting Campaign " << campaign_id << " ===" << std::endl;

    CampaignLogger logger(
    campaign_id,
    args.results_dir + "/data",
    10000);

    PRNG& prng = PseudoRandomNumberGenerator::GetPRNG();
    CKKSExperimentContext ctx = setup_campaign(args, prng);

    std::cout << "Computing golden output..." << std::endl;
    IterationResult golden = run_iteration(ctx, args, prng);
    auto metrics = EvaluateCKKSAccuracy(ctx.baseInput, golden.values);

    // Actualizar metadata con golden_norm
 //   metadata.golden_norm = golden_norm2;

    std::cout << "Campaign " << campaign_id << " registered" << std::endl;



    auto start_time = std::chrono::high_resolution_clock::now();

    // ========== 10. LOOP DE BIT FLIPS ==========
    std::cout << "\nStarting bit flip campaign..." << std::endl;

    // Calcular total esperado para progress
    uint32_t N = 1 << args.logN;
    size_t num_coeffs = N / 2;
    size_t bits_per_coeff = 64;
    size_t total_expected = args.num_limbs * num_coeffs * bits_per_coeff ;

    std::cout << "Expected bit flips: " << total_expected << std::endl;

    size_t total_iterations = 0;
    size_t progress_interval = total_expected / 100;  // 1% intervals
    if (progress_interval == 0) progress_interval = 10000;

    if(AcceptCKKSResult(metrics)){
        for (size_t limb = 0; limb < args.num_limbs; limb++)
        {
            for (size_t coeff = 0; coeff < num_coeffs; coeff++)
            {
                for(size_t bit=0; bit<bits_per_coeff; bit++)
                {
                    IterationArgs iterArgs(limb, coeff, bit);
                    IterationResult res = run_iteration(ctx, args, prng, iterArgs);
                    auto metricsBitFlip = EvaluateCKKSAccuracy(golden.values, res.values);

                    logger.log(iterArgs.limb,
                            iterArgs.coeff,
                            iterArgs.bit,
                            args.stage,
                            metricsBitFlip.l2_rel_error,     // ||error||_2 / ||golden||_2
                            metricsBitFlip.linf_abs_error,
                            res.detected
                        );
                    total_iterations++;

                    // Progress
                    if (total_iterations % progress_interval == 0) {
                        double percent = (double)total_iterations / total_expected * 100.0;
                        auto now = std::chrono::high_resolution_clock::now();
                        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                            now - start_time
                        ).count();

                        double rate = (elapsed > 0) ? (double)total_iterations / elapsed : 0.0;

                        std::cout << "Progress: " << std::fixed << std::setprecision(1)
                                 << percent << "% (" << total_iterations << "/"
                                 << total_expected << ") - Rate: "
                                 << std::setprecision(0) << rate << " bf/s"
                                 << std::endl;
                    }
                }
            }
        }
    } else {
        std::cout << "L2 relative error : " << metrics.l2_rel_error << "\n";
        std::cout << "Linf abs error   : " << metrics.linf_abs_error << "\n";
        std::cout << "Bits precision   : " << metrics.bits_precision << "\n";
        std::cerr << "Error with golden norm, checkout the used parameters" << std::endl;
    }
    registry.register_end({
            campaign_id,
            logger.total(),
            logger.sdc(),
            0,
            timestamp_now()
            });
    return 0;
}
// ========== 11. FINALIZAR ==========
//    auto end_time = std::chrono::high_resolution_clock::now();
//    auto duration = std::chrono::duration_cast<std::chrono::seconds>(
//                    end_time - start_time).count();
//
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
