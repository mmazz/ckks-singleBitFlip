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
    IterationArgs iterArgs(10, 1, 0);
    std::vector<double> res = run_iteration(ctx, args, prng, iterArgs);
//  log_bitflip(uint32_t limb,uint32_t coeff, uint8_t bit, const std::string& stage, double norm2, double rel_error, bool is_sdc = false)
    logger.log_bitflip(iterArgs.limb, iterArgs.coeff, iterArgs.bit, "encrypt", 0.01, 0.123, 0);

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(
                    end_time - start_time).count();

    std::cout << duration << std::endl;

    return 0;
}
