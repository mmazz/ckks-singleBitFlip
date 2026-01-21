
#include "campaign_helper.h"
#include "campaign_logger.h"
#include "campaign_registry.h"
#include "backend_interface.h"
#include "utils_ckks.h"


int main(int argc, char* argv[]) {
    std::cout << "\n=== Starting Campaign "<< std::endl;
    CampaignArgs args = parse_arguments(argc, argv);
    args.library = "heaan";
    args.flipType = "exhaustive";
    args.num_limbs = 1;
    args.mult_depth = 1;
    if (args.verbose) {
        args.print();
    }


    BackendContext* ctx = setup_campaign(args);

    std::cout << "Computing golden output..." << std::endl;
    IterationResult golden = run_iteration(ctx, args);

    const auto& input = get_reference_output(ctx);

    auto scheme_metrics = EvaluateCKKSAccuracy(input, golden.values);


    if(AcceptCKKSResult(scheme_metrics))
    {
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

        // Calcular total esperado para progress
        uint32_t N = 1 << args.logN;
        size_t num_coeffs = N;
        size_t bits_per_coeff = args.bitPerCoeff;
        size_t total_expected =  num_coeffs * bits_per_coeff ;

        std::vector<double> norms;
        norms.reserve(total_expected);
        std::cout << "Expected bit flips: " << total_expected << std::endl;

        size_t total_iterations = 0;
    //    size_t progress_interval = total_expected / 10;  // 10% intervals
    //    if (progress_interval == 0)
    //        progress_interval = 10000;
        for (size_t coeff = 0; coeff<num_coeffs; coeff++)
        {
            for(size_t bit=0; bit<bits_per_coeff; bit++)
            {
                IterationArgs iterArgs(0, coeff, bit);
                IterationResult res = run_iteration(ctx, args, iterArgs);
                CKKSAccuracyMetrics  metricsBitFlip = EvaluateCKKSAccuracy(golden.values, res.values);

                logger.log(iterArgs.limb,
                        iterArgs.coeff,
                        iterArgs.bit,
                        metricsBitFlip.l2_rel_error,     // ||error||_2 / ||golden||_2
                        metricsBitFlip.linf_abs_error,
                        res.detected
                    );

                norms.push_back(metricsBitFlip.l2_rel_error);
                total_iterations++;

              //  if (total_iterations % progress_interval == 0) {
              //      double percent = (double)total_iterations / total_expected * 100.0;
              //      auto now = std::chrono::high_resolution_clock::now();
              //      auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
              //          now - start_time
              //      ).count();

              //      double rate = (elapsed > 0) ? (double)total_iterations / elapsed : 0.0;

              //      std::cout << "Progress: " << std::fixed << std::setprecision(1)
              //               << percent << "% (" << total_iterations << "/"
              //               << total_expected << ") - Rate: "
              //               << std::setprecision(0) << rate << " bf/s"
              //               << std::endl;
              //  }
            }
        }
    std::sort(norms.begin(), norms.end());
    double l2_P95 = percentile(norms, 0.95);
    double l2_P99 = percentile(norms, 0.99);
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::seconds duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
    auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration);
    uint64_t mins = minutes.count();

    registry.register_end({campaign_id, logger.total(), logger.sdc(), mins, l2_P95, l2_P99, timestamp_now()});
    } else {
        std::cout << "Input vs output " << input.size() << "\n";
        for(size_t i=0; i<input.size(); i++)
            std::cout << golden.values[i] << ", " << input[i] << std::endl;
        std::cout << "L2 relative error : " << scheme_metrics.l2_rel_error << "\n";
        std::cout << "Linf abs error   : "  << scheme_metrics.linf_abs_error << "\n";
        std::cout << "Bits precision   : "  << scheme_metrics.bits_precision << "\n";
        std::cerr << "Error with golden norm, checkout the used parameters" << std::endl;
    }

    return 0;
}

