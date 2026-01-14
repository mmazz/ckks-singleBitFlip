#include "openfhe.h"

#include "campaign_helper.h"
#include "campaign_logger.hpp"
#include "utils_openfhe.h"

int main(int argc, char* argv[]) {
    const CampaignArgs args = parse_arguments(argc, argv);

    if (args.verbose) {
        args.print();
    }
 // Setup registry
    CampaignRegistry registry(args.results_dir);
    uint32_t campaign_id = registry.get_next_campaign_id();

    std::cout << "\n=== Starting Campaign " << campaign_id << " ===" << std::endl;

    auto cfg = SDCConfigHelper::MakeConfig(
        false,                            // enableDetection
        SecretKeyAttackMode::CompleteInjection,   // attackMode
        5.0                              // thresholdBits
    );
    SDCConfigHelper::SetGlobalConfig(cfg);

    // Falta first mod, y batchsize, cambiar N a logN, logDelta
    CampaignMetadata metadata = {
        campaign_id,
        args.library,
        get_timestamp(),
        args.logN,
        args.logQ,
        args.logDelta,
        args.logSlots,
        args.mult_depth,
        args.seed,
        args.seed_input,
        args.num_limbs,
        args.withNTT,
        0.0,  // golden_norm (to be calculated)
        0,    // total_bitflips (to be calculated)
        0     // num_stages (to be calculated)
    };


    // Setup logger
    CampaignLogger logger(campaign_id, args.results_dir + "/data");


    registry.register_campaign(metadata);

    auto start_time = std::chrono::high_resolution_clock::now();

    PRNG& prng = PseudoRandomNumberGenerator::GetPRNG();
    CampaignContext ctx = setup_campaign(args, prng);

    IterationResult golden = run_iteration(ctx, args, prng);

    double golden_norm2 = compute_norm2(ctx.baseInput, golden.values);
    if(golden_norm2<0.5){
      //  size_t ringDim = 1 << args.logN;
       // size_t limbs = args.mult_depth + 1;
        for (size_t limb = 0; limb < 1; limb++)
        //for (size_t limb = 0; limb < limbs; limb++)
        {
            //std::cout << "RNS: " << limb << std::endl;
            for (size_t coeff = 0; coeff < 2; coeff++)
            //for (size_t coeff = 0; coeff < ringDim; coeff++)
            {
                //std::cout << "Coeff" << coeff << std::endl;
                for(size_t bit=0; bit<4; bit++)
                //for(size_t bit=0; bit<64; bit++)
                {
                    IterationArgs iterArgs(limb, coeff, bit);
                    IterationResult res = run_iteration(ctx, args, prng, iterArgs);
                    double norm2 = compute_norm2(golden.values, res.values);
                    logger.log_bitflip(iterArgs.limb, iterArgs.coeff, iterArgs.bit, "encrypt", norm2, 0.123, res.detected);
                }
            }
        }
    } else {
        std::cerr << "Error with golden norm, checkout the used parameters" << std::endl;
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(
                    end_time - start_time).count();

    std::cout << duration << std::endl;

    return 0;
}
