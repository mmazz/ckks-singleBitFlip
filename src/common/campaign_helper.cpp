#include "campaign_helper.h"
#include "campaign_registry.h"

#include <getopt.h>
#include <cstdlib>
#include <chrono>
#include <iomanip>
#include <sstream>



void CampaignArgs::print(std::ostream& os) const {
    os << "===== CampaignArgs =====\n";
    os << "library: " << library << '\n';
    os << "stage: " << stage << '\n';

    os << "bitPerCoeff: " << bitPerCoeff << '\n';
    os << "logN: " << logN << '\n';
    os << "logQ: " << logQ << '\n';
    os << "logDelta: " << logDelta << '\n';
    os << "logSlots: " << logSlots << '\n';
    os << "mult_depth: " << mult_depth << '\n';
    os << "logMin: " << logMin << '\n';
    os << "logMax: " << logMax << '\n';

    os << "seed: " << seed << '\n';
    os << "seed_input: " << seed_input << '\n';

    os << "withNTT: " << std::boolalpha << withNTT << '\n';
    os << "doAdd: " << doAdd << '\n';
    os << "doPlainMul: " << doPlainMul << '\n';
    os << "doMul: " << doMul << '\n';
    os << "doScalarMul: " << doScalarMul << '\n';
    os << "doRot: " << doRot << '\n';
    os << "doBoot: " << doBoot << '\n';
    os << "op_step: " << op_step << '\n';
    os << "op_depth: " << op_depth << '\n';

    os << "isComplex: " << isComplex << '\n';
    os << "isExhaustive: " << isExhaustive << '\n';
    os << "verbose: " << verbose << '\n';

    os << "dnum: " << dnum << '\n';
    os << "amountBits: " << amountBits << '\n';
    os << "scaleTech: " << scaleTech << '\n';
    os << "results_dir: " << results_dir << '\n';

    if (openfhe_attack_mode)
        os << "openfhe_attack_mode: " << static_cast<int>(*openfhe_attack_mode) << '\n';
    else
        os << "openfhe_attack_mode: <none>\n";

    if (openfhe_threshold_bits)
        os << "openfhe_threshold_bits: " << *openfhe_threshold_bits << '\n';
    else
        os << "openfhe_threshold_bits: <none>\n";

    os << "========================\n";
}



void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [OPTIONS]\n\n"
              << "Options:\n"
              << "  --stage <name>              Stage to target: none, encode, encrypt_c0, encrypt_c1, decrypt_c0, decrypt_c1, decode, mul_inside, mul_outside, add_inside, add_outside, rot_inside, rot_outside (default: none)\n"
              << "  --bitPerCoeff <value>   Max bits per coeff (default: 64)\n"
              << "  --logN <value>          log Ring dimension (default: 3 = 2^3 = 8)\n"
              << "  --logQ <value>          First mod bits (default: 60)\n"
              << "  --logDelta <value>      Scaling factor bits (default: 50)\n"
              << "  --logSlots <value>      log Slots used (default: 1)\n"
              << "  --mult_depth <value>    Multiplicative depth (only openfhe, default: 0)\n"
              << "  --withNTT <value>       Turn on or off NTT (only heaan, default: 0)\n"
              << "  --doAdd <value>         The pipeline server has addition (default: 0)\n"
              << "  --doPlainMul <value>    The pipeline server has that much of plain Muls (default: 0)\n"
              << "  --doMul <value>         The pipeline server has that much Muls (default: 0)\n"
              << "  --doScalarMul <value>   The pipeline server has Multiplies the cipher with that scalar (double) (default: 0, no mult)\n"
              << "  --doRot <value>         The pipeline server has Rot, the value is how many rot (default: 0)\n"
              << "  --doBoot <value>        The pipeline server has Bootstrapping after operations (default: 0)\n"
              << "  --op_step <value>      Index of the target operation within the selected stage (0-based, default: 0)\n"
              << "  --op_depth <value>      Depth within the selected operation where the bit flip is applied (0-based, default: 0)\n"
              << "  --isComplex <name>      Complex input, only for HEAAN (default: 0)\n"
              << "  --isExhaustive <name>   Type of bit flip campaign (default: exhaustive)\n"
              << "  --seed <value>          Random seed for scheme (default: 0)\n"
              << "  --seed_input <value>    Random seed for input (default: 0)\n"
              << "  --logMin <value>        logMin value (default: 0= sample from [-1,)\n"
              << "  --logMax <value>        logMax value (default: 0= sample up to ,1])\n"
              << "  --attackModeSKA <value> Type of error injection for SKA (only heaan, default: complete)\n"
              << "  --thresholdSKA <value>  Bits for threshold for SKA (only heaan, default: 5.0)\n"
              << "  --dnum <value>          Digit number (default: 3)\n"
              << "  --amountBits <value>    Amount of burst bits (default: 1)\n"
              << "  --scaleTech <value>     Scaling technique (default: FIXEDMANUAL, others: FIXEDAUTO, FLEXIBLEAUTO or FLEXIBLEAUTOEXT)\n"
              << "  --results_dir <path>    Results directory (default: results)\n"
              << "  --verbose, -v           Verbose output\n"
              << "  --help, -h              Show this help\n\n"
              << "Examples:\n"
              << "  " << program_name << " --library openfhe --logN 16 --stage encrypt\n"
              << "  " << program_name << " --library heaan --logN 15 --logDelta 60 --seed 123\n"
              << "  " << program_name << " --stage mul --limbs 4 -v\n";
}
CampaignArgs parse_arguments(int argc, char* argv[]) {
    CampaignArgs args;

    static struct option long_options[] = {
        {"stage",          required_argument, 0, 'S'},
        {"bitPerCoeff",    required_argument, 0, 'c'},
        {"logN",           required_argument, 0, 'N'},
        {"logQ",           required_argument, 0, 'Q'},
        {"logDelta",       required_argument, 0, 'd'},
        {"logSlots",       required_argument, 0, 'g'},
        {"mult_depth",     required_argument, 0, 'm'},
        {"withNTT",        required_argument, 0, 'n'},
        {"doAdd",          required_argument, 0, 'A'},
        {"doPlainMul",     required_argument, 0, 'p'},
        {"doMul",          required_argument, 0, 'M'},
        {"doScalarMul",    required_argument, 0, 'L'},
        {"doRot",          required_argument, 0, 'r'},
        {"doBoot",         required_argument, 0, 'B'},
        {"op_step",        required_argument, 0, 'o'},
        {"op_depth",       required_argument, 0, 'O'},
        {"isComplex",      required_argument, 0, 'X'},
        {"isExhaustive",   required_argument, 0, 'T'},
        {"logMin",         required_argument, 0, 'x'},
        {"logMax",         required_argument, 0, 'y'},
        {"seed",           required_argument, 0, 's'},
        {"seed_input",     required_argument, 0, 'b'},
        // only Openfhe
        {"attackModeSKA",  required_argument, 0, 'a'},
        {"thresholdSKA",   required_argument, 0, 't'},
        {"dnum",           required_argument, 0, 'D'},
        {"amountBits",     required_argument, 0, 'J'},
        {"scaleTech",      required_argument, 0, 'C'},
        {"results_dir",    required_argument, 0, 'R'},
        {"verbose",        no_argument,       0, 'v'},
        {"help",           no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };

    int opt, option_index = 0;

    while ((opt = getopt_long(
        argc, argv,
        "S:c:N:Q:d:g:m:n:A:p:M:L:r:B:o:O:X:T:x:y:s:b:a:t:D:C:R:v:h",
        long_options,
        &option_index)) != -1)
    {
        switch (opt) {
            case 'l':
                args.library = optarg;
                if (args.library != "openfhe" && args.library != "heaan") {
                    std::cerr << "Error: library must be 'openfhe' or 'heaan'\n";
                    std::exit(1);
                }
                break;

            case 'c': args.bitPerCoeff = std::stoul(optarg); break;
            case 'N': args.logN = std::stoul(optarg); break;
            case 'Q': args.logQ = std::stoul(optarg); break;
            case 'd': args.logDelta = std::stoul(optarg); break;
            case 'm': args.mult_depth = std::stoul(optarg); break;
            case 's': args.seed = std::stoul(optarg); break;
            case 'b': args.seed_input = std::stoul(optarg); break;
            case 'x': args.logMin = std::stoul(optarg); break;
            case 'y': args.logMax = std::stoul(optarg); break;
            case 'D': args.dnum= std::stoul(optarg); break;
            case 'r': args.doRot = std::stoul(optarg); break;
            case 'B': args.doBoot = std::stoul(optarg); break;
            case 'o': args.op_step = std::stoul(optarg); break;
            case 'O': args.op_depth = std::stoul(optarg); break;
            case 'J': args.amountBits = std::stoul(optarg); break;

            case 'v':
                args.verbose = true;
                break;
            case 'g':
                args.logSlots = std::stoul(optarg);
                args.logSlots_provided = true;
                break;

            case 'n':  // --withNTT 0/1
                args.withNTT = std::stoul(optarg) != 0;
                break;

            case 'A': args.doAdd = std::stoul(optarg); break;
            case 'p': args.doPlainMul = std::stoul(optarg); break;
            case 'M': args.doMul = std::stoul(optarg); break;
            case 'L':
                try {
                    args.doScalarMul = std::stod(optarg);
                } catch (const std::exception& e) {
                    std::cerr << "Invalid value for -L (expected double): " << optarg << "\n";
                    std::exit(EXIT_FAILURE);
                }
                break;

            case 'S':
                args.stage = optarg;
                if (args.stage != "encode" &&
                    args.stage != "encrypt_c0" &&
                    args.stage != "encrypt_c1" &&
                    args.stage != "decrypt_c0" &&
                    args.stage != "decrypt_c1" &&
                    args.stage != "decode" &&
                    args.stage != "cheby_tanh3" &&
                    args.stage != "hidden_layer" &&
                    args.stage != "add_inside" &&
                    args.stage != "mul_inside" &&
                    args.stage != "rescale_inside" &&
                    args.stage != "rot_inside" &&
                    args.stage != "boot_outside" &&
                    args.stage != "boot_coeff" &&
                    args.stage != "boot_eval" &&
                    args.stage != "boot_slot")
                {
                    std::cerr << "Error: invalid stage '" << args.stage
                              << "' (expected: encode, encrypt_c0, encrypt_c1, decrypt_c0, decrypt_c1"
                              " decode, cheby_tanh3, hidden_layer,  mul_inside or mul_outside"
                              "boot_outisde, boot_coeff, boot_eval, boot_slots)\n";
                    std::exit(EXIT_FAILURE);
                }
                break;

            case 'X':
                args.isComplex= std::stoul(optarg);
                break;

            case 'T':
                args.isExhaustive = optarg;
                break;

            case 'a':
                args.openfhe_attack_mode =
                    parse_attack_mode(std::stoul(optarg));
                break;

            case 't':
                args.openfhe_threshold_bits =
                    std::stod(optarg);
                break;

            case 'C':
                args.scaleTech= optarg;
                break;

            case 'R':
                args.results_dir = optarg;
                break;

            case 'h':
                print_usage(argv[0]);
                std::exit(0);

            default:
                print_usage(argv[0]);
                std::exit(1);
        }
    }

    if (!args.logSlots_provided) {
        if (args.logN == 0) {
            std::cerr << "Error: logN must be set if --logSlots is omitted\n";
            std::exit(1);
        }
        args.logSlots = args.logN - 1;
    }
    return args;
}


