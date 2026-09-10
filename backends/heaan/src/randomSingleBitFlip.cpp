#include "campaign_helper.h"
#include "logger.h"
#include "registry.h"
#include "backend_interface.h"
#include "args.h"
#include "metrics.h"

size_t NUM_BITFLIPS = 50;

int main(int argc, char* argv[]) {
    std::cout << "\n=== Starting Campaign "<< std::endl;
    CampaignArgs args = parse_arguments(argc, argv);
    args.library = "heaan";
    args.isExhaustive= false;
    args.mult_depth = 0;

    if (args.verbose) {
        args.print();
    }

    BackendContext* ctx = setup_campaign(args);

    size_t slots =  (size_t)(1 << args.logSlots);
    std::cout << "Computing golden output..." << std::endl;
    // if complex, goldenCKKs_output has 2*slots
    IterationResult goldenCKKS_output = run_iteration(ctx, args);
    std::vector<double> goldenOutput;

    if(args.isComplex){
        goldenOutput = get_reference_output_complex(ctx);
    } else {
        goldenOutput = get_reference_output(ctx);
    }

    CKKSAccuracyMetrics baseline_metrics = EvaluateCKKSAccuracy(goldenOutput, goldenCKKS_output.values);

    double max_rel_error = 1e-4;
    double max_abs_error = 1e-4;
    if(args.doBoot){
        max_rel_error = 1e-3;
        max_abs_error = 1e-3;
    } 
    if(AcceptCKKSResult(baseline_metrics, max_rel_error, max_abs_error))
    {
        std::cout << "\n=== Registring Campaign "<< std::endl;
        CampaignRegistry registry(args);
        uint32_t campaign_id = registry.campaign_id;
        seed_rng(args.seed, campaign_id);
        std::cout << "\n=== Starting Campaign " << campaign_id << " ===" << std::endl;

        CampaignLogger logger(
            campaign_id,
            args.results_dir + "/data",
            10000);

        VectorLogger  vlogger(campaign_id, args.results_dir+ "/vectors", args.logSlots);
        std::cout << "Campaign " << campaign_id << " registered" << std::endl;


        // ========== 10. LOOP DE BIT FLIPS ==========
        std::cout << "\nStarting bit flip campaign..." << std::endl;

        // Calcular total esperado para progress
        uint32_t N = 1 << args.logN;
        size_t num_bitFlips = NUM_BITFLIPS;
        std::vector<double> norms;
        norms.reserve(num_bitFlips);

        std::cout << "Total bit flips: " << num_bitFlips << std::endl;

        size_t num_zones = 4;
        size_t bits_per_coeff = args.bitPerCoeff;

        std::mt19937 rng(args.seed);

        auto start_time = std::chrono::high_resolution_clock::now();
        std::vector<uint32_t> bits_to_flip = bitsToFlipGenerator(args); 
        if (args.verbose) {
            for(int i=0; i<bits_to_flip.size(); i++)
                std::cout << bits_to_flip[i] << ", ";
            std::cout << std::endl;

        }
        for (size_t i = 0; i < num_bitFlips; i++) {
            uint32_t coeff = random_int(0, N-1);
            for (size_t bitIndex = 0; bitIndex < bits_to_flip.size() ; bitIndex++) {
                uint32_t bit = bits_to_flip[bitIndex];
                IterationArgs iterArgs(0, coeff, bit);

                    IterationResult res = run_iteration(ctx, args, iterArgs);

                    CKKSAccuracyMetrics  exp_metrics = EvaluateCKKSAccuracy(goldenCKKS_output.values, res.values);

                    auto slot_stats = categorize_slots_relative(goldenCKKS_output.values, res.values, slots);
                    logger.log(iterArgs.limb,
                            iterArgs.coeff,
                            iterArgs.bit,
                            exp_metrics.l2_abs_error,     // ||error||_2 / ||golden||_2
                            exp_metrics.l2_rel_error,     // ||error||_2 / ||golden||_2
                            exp_metrics.linf_abs_error,
                            exp_metrics.linf_rel_error,
                            res.detected,
                            slot_stats
                        );
  
                    vlogger.log(iterArgs.limb, iterArgs.coeff, iterArgs.bit, goldenCKKS_output.values, res.values);
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
        logger.close();
        registry.register_end({campaign_id, logger.total(), logger.sdc(), mins, l2_P95, l2_P99, timestamp_now()});
    } else {
        printBaselineComparison(
            args,
            goldenOutput,
            goldenCKKS_output.values,
            baseline_metrics
        );
        return 1;
    }

    return 0;
}

