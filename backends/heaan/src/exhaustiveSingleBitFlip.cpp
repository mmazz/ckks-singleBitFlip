
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
    size_t slots =  (size_t)(1 << args.logSlots);
    std::cout << "Computing golden output..." << std::endl;
    IterationResult goldenCKKS_output = run_iteration(ctx, args);

    const auto& goldenOutput = get_reference_output(ctx);
    CKKSAccuracyMetrics baseline_metrics = EvaluateCKKSAccuracy(goldenOutput, goldenCKKS_output.values);


    if(AcceptCKKSResult(baseline_metrics))
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


        for (size_t coeff = 0; coeff<num_coeffs; coeff++)
        {
            for(size_t bit=0; bit<bits_per_coeff; bit++)
            {
                IterationArgs iterArgs(0, coeff, bit);
                IterationResult res = run_iteration(ctx, args, iterArgs);

                CKKSAccuracyMetrics  exp_metrics = EvaluateCKKSAccuracy(goldenCKKS_output.values, res.values);

                auto slot_stats = categorize_slots_relative(goldenCKKS_output.values, res.values, slots);
                logger.log(iterArgs.limb,
                        iterArgs.coeff,
                        iterArgs.bit,
                        exp_metrics.l2_rel_error,     // ||error||_2 / ||golden||_2
                        exp_metrics.linf_abs_error,
                        res.detected,
                        slot_stats
                    );

                norms.push_back(exp_metrics.l2_rel_error);
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
        std::cout << "Input vs output " << goldenOutput.size() << "\n";
        for(size_t i=0; i<goldenOutput.size(); i++)
            std::cout << goldenCKKS_output.values[i] << ", " << goldenOutput[i] << std::endl;
        std::cout << "L2 relative error : " << baseline_metrics.l2_rel_error << "\n";
        std::cout << "Linf abs error   : "  << baseline_metrics.linf_abs_error << "\n";
        std::cout << "Bits precision   : "  << baseline_metrics.bits_precision << "\n";
        std::cerr << "Error with golden norm, checkout the used parameters" << std::endl;
    }

    return 0;
}

