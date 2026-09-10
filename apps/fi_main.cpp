#include "backend_interface.h"
#include "logger.h"
#include "registry.h"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <memory>

struct Sink {
    CampaignLogger&     logger;
    VectorLogger*       vlogger;   // nullptr si no hay --saveVectors
    std::vector<double> norms;
};

static bool baseline_ok(const CampaignArgs& args, const std::vector<double>& plain_golden, const std::vector<double>& ckks_golden){
    CKKSAccuracyMetrics baseline_metrics = EvaluateCKKSAccuracy(plain_golden, ckks_golden);
    double tol = args.doBoot ? 1e-3 : 1e-4;
    bool res = AcceptCKKSResult(baseline_metrics, tol, tol);
    if(!res)
        printBaselineComparison(
            args,
            plain_golden,
            ckks_golden,
            baseline_metrics
        );
    return res;
}

static void run_one(BackendContext* ctx, CampaignArgs& args, const std::vector<double>& ckks_golden, const IterationArgs& iterArgs, Sink& s){
    IterationResult res = run_iteration(ctx, args, iterArgs);

    CKKSAccuracyMetrics  exp_metrics = EvaluateCKKSAccuracy(ckks_golden, res.values);

    auto slot_stats = categorize_slots_relative(ckks_golden, res.values, ckks_golden.size());
    s.logger.log(iterArgs.limb,
            iterArgs.coeff,
            iterArgs.bit,
            exp_metrics.l2_abs_error,     // ||error||_2 
            exp_metrics.l2_rel_error,     // ||error||_2 / ||golden||_2
            exp_metrics.linf_abs_error,
            exp_metrics.linf_rel_error,
            res.detected,
            slot_stats
        );
    if (s.vlogger) s.vlogger->log(iterArgs.limb, iterArgs.coeff, iterArgs.bit, ckks_golden, res.values);
    s.norms.push_back(exp_metrics.l2_rel_error);
}

static void run_exhaustive(BackendContext* ctx, CampaignArgs& args, const std::vector<double>& ckks_golden, Sink& s){
    
    uint32_t num_limb = num_limbs(ctx, args);
    uint32_t N = (1U<<args.logN);
    
    for (size_t limb=0; limb<num_limb; limb++)
    {
        for (size_t coeff=0; coeff<N; coeff++)
        {
            for(size_t bit=0; bit< args.bitsPerCoeff; bit++)
            {                
                IterationArgs iterArgs(limb, coeff, bit);
                run_one(ctx, args, ckks_golden, iterArgs, s);
            }
        }
    }
}

static void run_random(BackendContext* ctx, CampaignArgs& args, const std::vector<double>& ckks_golden, Sink& s){
    std::vector<uint32_t> bits_to_flip = bitsToFlipGenerator(args); 
    uint32_t N = (1U<<args.logN);
    uint32_t num_limb = num_limbs(ctx, args);
    for (size_t sample=0; sample<args.numSamples; sample++)
    {
        uint32_t limb = random_int(0, num_limb - 1);
        uint32_t coeff = random_int(0, N-1);
        for(size_t bitIndex=0; bitIndex< bits_to_flip.size(); bitIndex++)
        {                
            uint32_t bit = bits_to_flip[bitIndex];
            IterationArgs iterArgs(limb, coeff, bit);
            run_one(ctx, args, ckks_golden, iterArgs, s);
        }
    }
}


int main(int argc, char** argv) {
    try{
        CampaignArgs args = parse_arguments(argc, argv);
        backend_prepare_args(args);
        validateArgs(args);
        if(args.isExhaustive)
            args.numSamples = 0;

        BackendContext* ctx = setup_campaign(args);
        const std::vector<double> ckks_golden  = run_iteration(ctx, args, std::nullopt).values;
        const std::vector<double> plain_golden = get_reference_output(ctx);
        if (!baseline_ok(args, plain_golden, ckks_golden)) { 
            destroy_campaign(ctx); 
            return 1;
        }

        CampaignRegistry registry(args);
        if (registry.already_done){
            std::cout << "Campaing already done" << std::endl;
            return 0;
        }
        CampaignLogger logger(registry.campaign_id, args.results_dir + "/data");
        std::unique_ptr<VectorLogger> vlogger;
        if (args.saveVectors)
            vlogger = std::make_unique<VectorLogger>(registry.campaign_id, args.results_dir + "/vectors",
                                                     args.logSlots + (args.isComplex ? 1 : 0));
        Sink s{logger, vlogger.get(), {}};

        auto start_time = std::chrono::steady_clock::now();

        if(args.isExhaustive)
            run_exhaustive(ctx, args,  ckks_golden,  s);
        else
            run_random(ctx, args,  ckks_golden,  s);

        auto end_time = std::chrono::steady_clock::now();
        std::chrono::seconds duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
        auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration);
        uint64_t mins = minutes.count();
        logger.close();
        if (vlogger) vlogger->close();
        double p95 = 0, p99 = 0;
        if(!s.norms.empty())
            std::sort(s.norms.begin(), s.norms.end());

        registry.register_end({registry.campaign_id, logger.total(), logger.sdc(), mins, p95, p99, timestamp_now()});
        destroy_campaign(ctx);
        return 0;
    } catch (const std::exception& e) { 
        std::cerr << "ERROR: " << e.what() << '\n'; return 1; 
    }
}
