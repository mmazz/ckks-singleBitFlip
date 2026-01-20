
#include "campaign_helper.h"
#include "campaign_logger.h"
#include "campaign_registry.h"
#include "backend_interface.h"
#include "utils_ckks.h"


int main(int argc, char* argv[]) {
    std::cout << "\n=== Starting Campaign "<< std::endl;
    CampaignArgs args = parse_arguments(argc, argv);
    args.library = "heaan";
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

 //   metadata.golden_norm = golden_norm2;



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
        size_t num_bitFlips = 1000;
        std::vector<double> norms;
        norms.reserve(num_bitFlips);

        std::cout << "Total bit flips: " << num_bitFlips << std::endl;

        size_t num_zones = 4;
        size_t bits_per_coeff = args.bitPerCoeff;

        std::mt19937 rng(args.seed);

        for (size_t zone = 0; zone < num_zones; zone++) {
            auto [bit_lo, bit_hi] = bit_zone_bounds(zone, bits_per_coeff);

            std::uniform_int_distribution<uint32_t> bit_dist(
                static_cast<uint32_t>(bit_lo),
                static_cast<uint32_t>(bit_hi - 1) // IMPORTANTE
            );

            uint32_t bit = bit_dist(rng);
            size_t total_iterations = 0;

            uint32_t coeff = random_int(0, N-1);
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
        std::cout << "L2 relative error : " << scheme_metrics.l2_rel_error << "\n";
        std::cout << "Linf abs error   : "  << scheme_metrics.linf_abs_error << "\n";
        std::cout << "Bits precision   : "  << scheme_metrics.bits_precision << "\n";
        std::cerr << "Error with golden norm, checkout the used parameters" << std::endl;
    }

    return 0;
}

