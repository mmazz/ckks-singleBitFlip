#include "campaign_helper.h"
#include "campaign_registry.h"

#include <getopt.h>
#include <cstdlib>
#include <chrono>
#include <iomanip>
#include <sstream>



void CampaignArgs::print(std::ostream& os) const {
    os << "Campaign configuration:\n"
       << "  library: " << library << "\n"
       << "  stage: " << stage<< "\n"
       << "  bitPerCoeff: " << bitPerCoeff << "\n"
       << "  logN: " << logN << "\n"
       << "  logQ: " << logQ << "\n"
       << "  logDelta: " << logDelta << "\n"
       << "  logSlots: " << logSlots << "\n"
       << "  mult_depth: " << mult_depth << "\n"
       << "  seed: " << seed << "\n"
       << "  seed_input: " << seed_input << "\n"
       << "  logMin: " << logMin << "\n"
       << "  logMax: " << logMax << "\n"
       << "  withNTT: " << withNTT << "\n"
       << "  doAdd: " << doAdd << "\n"
       << "  doPlainMul: " << doPlainMul << "\n"
       << "  doMul: " << doMul << "\n"
       << "  doScalarMul: " << doScalarMul << "\n"
       << "  doRot: " << doRot << "\n"
       << "  isComplex : " << isComplex<< "\n"
       << "  isExhaustive: " << isExhaustive << "\n"
       << "  dnum: " << dnum << "\n"
       << "  scaleTech: " << scaleTech << "\n";
           /* -------- OpenFHE-only knobs -------- */
        if (library == "openfhe") {
            os << "  attackModeSKA: ";
            if (openfhe_attack_mode)
                os << to_string(*openfhe_attack_mode) << "\n";
            else
                os << "(default)\n";

            os << "  thresholdBitsSKA: ";
            if (openfhe_threshold_bits)
                os << *openfhe_threshold_bits << "\n";
            else
                os << "(default)\n";
        }
    os << "  results_dir: " << results_dir << "\n";

}

void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [OPTIONS]\n\n"
              << "Options:\n"
              << "  --stage <name>          Stage to attack: none, encode, encrypt_c0, encrypt_c1, mul_c0, mul_c1, add_c0, add_c1 (default: none)\n"
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
              << "  --isComplex <name>      Complex input, only for HEAAN (default: false)\n"
              << "  --isExhaustive <name>   Type of bit flip campaign (default: exhaustive)\n"
              << "  --seed <value>          Random seed for scheme (default: 0)\n"
              << "  --seed_input <value>    Random seed for input (default: 0)\n"
              << "  --logMin <value>        logMin value (default: 0= sample from [-1,)\n"
              << "  --logMax <value>        logMax value (default: 0= sample up to ,1])\n"
              << "  --attackModeSKA <value> Type of error injection for SKA (only heaan, default: complete)\n"
              << "  --thresholdSKA <value>  Bits for threshold for SKA (only heaan, default: 5.0)\n"
              << "  --dnum <value>          Digit number (default: 3)\n"
              << "  --scaleTech <value>     Scaling technique (default: FIXEDMANUAL)\n"
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
        {"scaleTech",      required_argument, 0, 'C'},
        {"results_dir",    required_argument, 0, 'R'},
        {"verbose",        no_argument,       0, 'v'},
        {"help",           no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };

    int opt, option_index = 0;

    while ((opt = getopt_long(
        argc, argv,
        "S:c:N:Q:d:g:m:n:A:p:M:L:r:X:T:x:y:s:b:a:t:D:C:R:v:h",
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
            case 'A':
                args.doAdd = std::stoul(optarg) != 0;
                break;

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
                break;

            case 'X':
                args.isComplex= optarg;
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
