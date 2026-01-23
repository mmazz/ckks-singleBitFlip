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

    # -------- obligatorios (conceptualmente) --------
    parser.add_argument("--library", type=str, default=None)
    parser.add_argument("--stage", type=str, default=None)

    # -------- opcionales con default --------
    parser.add_argument("--bitPerCoeff", type=int, default=64)
    parser.add_argument("--mult_depth", type=int, default=0)
    parser.add_argument("--num_limbs", type=int, default=1)
    parser.add_argument("--logMin", type=int, default=0)
    parser.add_argument("--logMax", type=int, default=0)
    parser.add_argument("--doAdd", type=int, default=0)
    parser.add_argument("--doMul", type=int, default=0)
    parser.add_argument("--doRot", type=int, default=0)
    parser.add_argument("--withNTT", type=int, default=0)
    parser.add_argument("--logN", type=int, default=6)
    parser.add_argument("--logSlots", type=int, default=5)
    parser.add_argument("--logQ", type=int, default=60)
    parser.add_argument("--logDelta", type=int, default=50)

    # -------- opcionales sin default (no filtran) --------
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--seed_input", type=int, default=None)
    parser.add_argument("--isExhaustive", type=int, default=None)

    # -------- openfhe --------
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


