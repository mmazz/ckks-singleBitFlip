#include "openfhe.h"

#include "campaign_helper.h"

int main(int argc, char* argv[]) {
    // 1. Parsear argumentos
    CampaignArgs args = parse_arguments(argc, argv);

    // 2. Mostrar configuración (opcional)
    if (args.verbose) {
        std::cout << "Campaign Configuration:" << std::endl;
        std::cout << "  Library: " << args.library << std::endl;
        std::cout << "  N: " << args.N << std::endl;
        std::cout << "  Delta: " << args.delta << std::endl;
        std::cout << "  Mult depth: " << args.mult_depth << std::endl;
        std::cout << "  Seed: " << args.seed << std::endl;
        std::cout << "  Seed-input: " << args.seed_input << std::endl;
        std::cout << "  Num limbs: " << args.num_limbs << std::endl;
        std::cout << "  Stage: " << args.stage << std::endl;
        std::cout << "  Results dir: " << args.results_dir << std::endl;
    }

    // 3. Usar los argumentos en tu código
    std::cout << "\nRunning campaign with N=" << args.N
              << " on stage=" << args.stage << std::endl;

    // ... resto de tu código ...

    return 0;
}
