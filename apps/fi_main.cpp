#include "backend_interface.h"
#include "logger.h"
#include "registry.h"


struct Sink {
    CampaignLogger&     logger;
    VectorLogger*       vlogger;   // nullptr si no hay --saveVectors
    std::vector<double> norms;
};

template <typename T>
bool baseline_ok(CampaignArgs& args, std::vector<T>& plain_golden, std::vector<T>& ckks_golden){
    CKKSAccuracyMetrics baseline_metrics = EvaluateCKKSAccuracy(plain_golden, ckks_golden.values);
    bool res;
    if(args.doBoot)
        res = AcceptCKKSResult(baseline_metrics, 1e-3, 1e-3);
    else
        res = AcceptCKKSResult(baseline_metrics);
    if(!res)
        printBaselineComparison(
            args,
            plain_golden,
            ckks_golden.values,
            baseline_metrics
        );
    return res;
}

template <typename T>
void run_one(BackendContext& ctx, CampaignArgs& args, std::vector<T>& ckks_golden, const IterationArgs& iterArgs, Sink& s){
    IterationResult res = run_iteration(ctx, args, iterArgs);

    CKKSAccuracyMetrics  exp_metrics = EvaluateCKKSAccuracy(ckks_golden.values, res.values);

    auto slot_stats = categorize_slots_relative(ckks_golden.values, res.values, ckks_golden.size());
    s.logger.log(iterArgs.limb,
            iterArgs.coeff,
            iterArgs.bit,
            exp_metrics.l2_abs_error,     // ||error||_2 / ||golden||_2
            exp_metrics.l2_rel_error,     // ||error||_2 / ||golden||_2
            exp_metrics.linf_abs_error,
            exp_metrics.linf_rel_error,
            res.detected,
            slot_stats
        );

    s.norms.push_back(exp_metrics.l2_rel_error);
}

void run_exhaustive(BackendContext& ctx, CampaignArgs& args, std::vector<T>& ckks_golden, Sink& s){

    for (size_t limb=0; limb<num_limbs(ctx, args); limb++)
    {
        for (size_t coeff=0; coeff<(1<<args.logN); coeff++)
        {
            for(size_t bit=0; bit< args.bitsPerCoeff; bit++)
            {                
                IterationArgs iterArgs(limb, coeff, bit);
                run_one(ctx, args, ckks_golden, iterArgs, s);
            }
        }
    }
}

void run_random(BackendContext& ctx, CampaignArgs& args, std::vector<T>& ckks_golden, Sink& s){
    std::vector<uint32_t> bits_to_flip = bitsToFlipGenerator(args); 
    uint32_t num_limb = num_limbs(ctx, args);
    uint32_t limb = random_int(0, num_limb - 1);
    uint32_t coeff = random_int(0, (1<<args.logN)-1);
    for (size_t sample=0; sample<args.numSamples; sample++)
    {
        for(size_t bitIndex=0; bitIndex< bits_to_flip.size(); bitIndex++)
        {                
            uint32_t bit = bits_to_flip[bitIndex];
            IterationArgs iterArgs(limb, coeff, bit);
            run_one(ctx, args, ckks_golden, iterArgs, s);
        }
    }
}
}


int main(int argc, char** argv) {
    CampaignArgs args = parse_arguments(argc, argv);
    backend_prepare_args(args);
    validateArgs(args);
    if(args.isExhaustive)
        args.numSamples = 0

    BackendContext* ctx = setup_campaign(args);
    auto golden = run_iteration(ctx, args, std::nullopt);
    ckks_golden = get_reference_output(ctx);
    if (!baseline_ok(args, ctx, golden)) return 1;


    CampaignRegistry reg(args);
    if (reg.already_done()){
        std::cout << "Campaing already done" << std::endl;
        return 0;
    }
    CampaignLogger log(reg.campaign_id, args.results_dir + "/data");
    if(args.saveVectors)
        std::unique_ptr<VectorLogger> complex;

    auto start_time = std::chrono::high_resolution_clock::now();

    if(args.isExhaustive)
        run_exhaustive( ctx, args,  ckks_golden,  s);
    else
        run_random( ctx, args,  ckks_golden,  s);
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::seconds duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
    auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration);
    uint64_t mins = minutes.count();
    logger.close();
    registry.register_end({campaign_id, logger.total(), logger.sdc(), mins, l2_P95, l2_P99, timestamp_now()});
    destroy_campaign(ctx);
    return 1
};
