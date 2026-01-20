# utils_parser.py
import argparse

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v in ("1", "true", "True"):
        return True
    if v in ("0", "false", "False"):
        return False
    raise argparse.ArgumentTypeError("Boolean value expected (0/1, true/false)")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Filtro de campañas CKKS"
    )

    # -------- strings --------
    parser.add_argument("--library", type=str, default=None)
    parser.add_argument("--stage", type=str, default=None)

    # -------- enteros --------
    parser.add_argument("--bitPerCoeff", type=int, default=64)
    parser.add_argument("--logN", type=int, default=None)
    parser.add_argument("--logQ", type=int, default=None)
    parser.add_argument("--logDelta", type=int, default=None)
    parser.add_argument("--logSlots", type=int, default=None)
    parser.add_argument("--mult_depth", type=int, default=None)
    parser.add_argument("--num_limbs", type=int, default=None)
    parser.add_argument("--logMin", type=int, default=0)
    parser.add_argument("--logMax", type=int, default=0)

    # -------- bool opcional --------
    parser.add_argument(
        "--withNTT",
        default=None,
        help="Filtra campañas por NTT (1=True, 0=False)"
    )
    parser.add_argument(
        "--doAdd",
        type=str2bool,
        default=False,
        help="Filtrer campaigns with addition (1=True, 0=False)"
    )
    parser.add_argument(
        "--doMul",
        type=str2bool,
        default=False,
        help="Filtrer campaigns with multiplication (1=True, 0=False)"
    )
    # -------- openfhe opcionales --------
    parser.add_argument("--openfhe_attack_mode", type=str, default=None)
    parser.add_argument("--openfhe_threshold_bits", type=float, default=None)

    return parser.parse_args()


def build_filters(args):
    filters = {}

    for name, value in vars(args).items():
        if value is None:
            continue  # NO filtrar

        if isinstance(value, str):
            filters[name] = ("str", value)
        elif isinstance(value, bool):
            filters[name] = ("int", int(value))
        elif isinstance(value, int):
            filters[name] = ("int", value)
        elif isinstance(value, float):
            filters[name] = ("float", value)
        else:
            raise TypeError(f"Tipo no soportado para {name}: {type(value)}")

    return filters

