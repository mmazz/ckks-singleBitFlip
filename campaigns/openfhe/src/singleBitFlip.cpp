#include "openfhe.h"

#include "campaign_helper.h"
#include "campaign_logger.hpp"
#include "utils_openfhe.h"

int main(int argc, char* argv[]) {
       const CampaignArgs args = parse_arguments(argc, argv);
    if (args.verbose) {
        args.print();
    }

    // ========== 1. SETUP SDC CONFIG ==========
    auto cfg = SDCConfigHelper::MakeConfig(
        false,                                    // enableDetection
        SecretKeyAttackMode::CompleteInjection,   // attackMode
        5.0                                       // thresholdBits
    );
    SDCConfigHelper::SetGlobalConfig(cfg);

    // ========== 2. SETUP REGISTRY ==========
    CampaignRegistry registry(args.results_dir);
    uint32_t campaign_id = registry.get_next_campaign_id();

    std::cout << "\n=== Starting Campaign " << campaign_id << " ===" << std::endl;

    // ========== 3. DETERMINAR STAGES ==========
    std::vector<std::string> stages;
    if (args.stage == "all") {
        stages = {"encode", "encrypt_c0", "encrypt_c1", "mul_c0", "mul_c1", "add_c0", "add_c1"};
    } else {
        stages = {args.stage};
    }

    // ========== 4. METADATA INICIAL ==========
    CampaignMetadata metadata = {
        campaign_id,
        args.library,
        get_timestamp(),                          // timestamp_start
        "",                                       // timestamp_end (se actualiza al final)
        args.logN,
        args.logQ,
        args.logDelta,
        args.logSlots,
        args.mult_depth,
        args.seed,
        args.seed_input,
        args.withNTT,
        args.num_limbs,
        args.logMin,
        args.logMax,
        0.0,                                      // golden_norm (se calcula abajo)
        0,                                        // total_bitflips (se actualiza al final)
        0,                                        // sdc_count (se actualiza al final)
        (uint32_t)stages.size(),                  // num_stages
        0,                                        // duration_seconds (se actualiza al final)
        0.0,                                      // bitflips_per_second (se actualiza al final)
        "campaign_" + std::to_string(campaign_id) + ".csv.gz"  // data_file
    };

    // ========== 5. SETUP CAMPAÑA ==========
    PRNG& prng = PseudoRandomNumberGenerator::GetPRNG();
    CampaignContext ctx = setup_campaign(args, prng);

    // ========== 6. GOLDEN RUN ==========
    std::cout << "Computing golden output..." << std::endl;
    IterationResult golden = run_iteration(ctx, args, prng);
    double golden_norm2 = compute_norm2(ctx.baseInput, golden.values);

    // Actualizar metadata con golden_norm
    metadata.golden_norm = golden_norm2;

    // ========== 7. REGISTRAR CAMPAÑA ==========
    registry.register_campaign(metadata);
    std::cout << "Campaign " << campaign_id << " registered" << std::endl;

    // ========== 8. CREAR LOGGER CON AUTO-UPDATE ==========
    // ⭐ CLAVE: Pasar &registry para auto-actualización
    CampaignLogger logger(campaign_id, args.results_dir + "/data",
                         10000, &registry);

    // ========== 9. INICIAR TIMER ==========
    auto start_time = std::chrono::high_resolution_clock::now();

    // ========== 10. LOOP DE BIT FLIPS ==========
    std::cout << "\nStarting bit flip campaign..." << std::endl;

    // Calcular total esperado para progress
    uint32_t N = 1 << args.logN;
    size_t num_coeffs = N / 2;
    size_t bits_per_coeff = 64;
    size_t total_expected = args.num_limbs * num_coeffs * bits_per_coeff * stages.size();

    std::cout << "Expected bit flips: " << total_expected << std::endl;

    size_t total_iterations = 0;
    size_t progress_interval = total_expected / 100;  // 1% intervals
    if (progress_interval == 0) progress_interval = 10000;

    if(golden_norm2<0.5){
        for (size_t limb = 0; limb < args.num_limbs; limb++)
        {
            for (size_t coeff = 0; coeff < num_coeffs; coeff++)
            {
                for(size_t bit=0; bit<bits_per_coeff; bit++)
                {
                    IterationArgs iterArgs(limb, coeff, bit);
                    IterationResult res = run_iteration(ctx, args, prng, iterArgs);
                    double norm2 = compute_norm2(golden.values, res.values);
                    logger.log_bitflip(iterArgs.limb, iterArgs.coeff, iterArgs.bit, "encrypt", norm2, 0.123, res.detected);
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
        std::cerr << "Error with golden norm, checkout the used parameters" << std::endl;
    }
// ========== 11. FINALIZAR ==========
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(
                    end_time - start_time).count();

    std::cout << "\n=== Campaign " << campaign_id << " Complete ===" << std::endl;
    std::cout << "Total bit flips: " << logger.get_total_entries() << std::endl;
    std::cout << "SDC detected: " << logger.get_sdc_count()
              << " (" << std::fixed << std::setprecision(2)
              << (100.0 * logger.get_sdc_count() / logger.get_total_entries())
              << "%)" << std::endl;

    std::cout << "Duration: " << duration << " seconds";
    if (duration >= 3600) {
        std::cout << " (" << (duration / 3600) << "h "
                 << ((duration % 3600) / 60) << "m)";
    } else if (duration >= 60) {
        std::cout << " (" << (duration / 60) << "m "
                 << (duration % 60) << "s)";
    }
    std::cout << std::endl;

    double rate = (duration > 0) ? (double)logger.get_total_entries() / duration : 0.0;
    std::cout << "Rate: " << std::fixed << std::setprecision(2)
              << rate << " bit flips/second" << std::endl;

    std::cout << "\nResults saved to:" << std::endl;
    std::cout << "  Data: " << args.results_dir << "/data/"
              << metadata.data_file << std::endl;
    std::cout << "  Registry: " << args.results_dir << "/campaigns.csv"
              << std::endl;


    return 0;
}
