#include "campaign_helper.h"

// Función para mostrar ayuda
void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [OPTIONS]\n\n"
              << "Options:\n"
              << "  --library <name>        Library: openfhe or heaan (default: openfhe)\n"
              << "  --stage <name>          Stage to attack: all, encode, encrypt, mul, add, decrypt (default: all)\n"
              << "  --N <value>             Ring dimension (default: 16384)\n"
              << "  --delta <value>         Scaling factor bits (default: 50)\n"
              << "  --mult-depth <value>    Multiplicative depth (default: 5)\n"
              << "  --seed <value>          Random seed for scheme (default: 42)\n"
              << "  --seed-input <value>    Random seed for input (default: 42)\n"
              << "  --limbs <value>         Number of RNS limbs (default: 3)\n"
              << "  --results-dir <path>    Results directory (default: results)\n"
              << "  --verbose, -v           Verbose output\n"
              << "  --help, -h              Show this help\n\n"
              << "Examples:\n"
              << "  " << program_name << " --library openfhe --N 16384 --stage encrypt\n"
              << "  " << program_name << " --library heaan --N 32768 --delta 60 --seed 123\n"
              << "  " << program_name << " --stage mul --limbs 4 -v\n";
}

CampaignArgs parse_arguments(int argc, char* argv[]) {
    CampaignArgs args;  // Inicializa con valores por defecto

    // Definir opciones largas
    // Formato: {nombre, argumento_requerido?, puntero_flag, valor_corto}
    static struct option long_options[] = {
        {"library",       required_argument, 0, 'l'},  // Requiere argumento
        {"stage",         required_argument, 0, 'S'},
        {"N",             required_argument, 0, 'n'},
        {"delta",         required_argument, 0, 'd'},
        {"mult-depth",    required_argument, 0, 'm'},
        {"seed",          required_argument, 0, 'r'},
        {"seed-input",  required_argument, 0, 'b'},
        {"limbs",         required_argument, 0, 'L'},
        {"results-dir",   required_argument, 0, 'R'},
        {"verbose",       no_argument,       0, 'v'},  // No requiere argumento
        {"help",          no_argument,       0, 'h'},
        {0, 0, 0, 0}  // Terminador
    };

    int opt;
    int option_index = 0;

    // Loop de parsing
    // getopt_long procesa argv[] y retorna el carácter de la opción
    // optarg contiene el argumento (si required_argument)
    while ((opt = getopt_long(argc, argv,
                              "l:n:d:s:m:b:r:L:S:R:vh",  // String de opciones cortas
                              long_options,
                              &option_index)) != -1)
    {
        switch (opt) {
            case 'l':  // --library o -l
                args.library = optarg;
                // Validación
                if (args.library != "openfhe" && args.library != "heaan") {
                    std::cerr << "Error: library must be 'openfhe' or 'heaan'" << std::endl;
                    exit(1);
                }
                break;

            case 'n':  // --N o -n
                args.N = std::stoul(optarg);  // String to unsigned long
                break;

            case 'd':  // --delta o -d
                args.delta = std::stoul(optarg);
                break;

            case 'm':  // --mult-depth o -m
                args.mult_depth = std::stoul(optarg);
                break;

            case 'r':  // --seed o -r
                args.seed = std::stoull(optarg);  // String to unsigned long long
                break;

            case 'b':  // --seed-input o -b
                args.seed_input = std::stoull(optarg);
                break;

            case 'L':  // --limbs o -L
                args.num_limbs = std::stoul(optarg);
                break;

            case 'S':  // --stage o -S
                args.stage = optarg;
                // Opcional: validar stages válidos
                break;

            case 'R':  // --results-dir o -R
                args.results_dir = optarg;
                break;

            case 'v':  // --verbose o -v (no argumento)
                args.verbose = true;
                break;

            case 'h':  // --help o -h
                print_usage(argv[0]);
                exit(0);

            default:  // Opción desconocida
                print_usage(argv[0]);
                exit(1);
        }
    }

    // Opcional: procesar argumentos no-opción (posicionales)
    // if (optind < argc) {
    //     std::cout << "Argumentos extra: ";
    //     while (optind < argc) {
    //         std::cout << argv[optind++] << " ";
    //     }
    //     std::cout << std::endl;
    // }

    return args;
}
