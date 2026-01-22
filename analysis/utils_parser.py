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
    parser.add_argument("--mult_depth", type=int, default=0)
    parser.add_argument("--num_limbs", type=int, default=1)
    parser.add_argument("--logMin", type=int, default=0)
    parser.add_argument("--logMax", type=int, default=0)
    parser.add_argument("--doAdd", type=int, default=0)
    parser.add_argument("--doMul", type=int, default=0)
    parser.add_argument("--doRot", type=int, default=0)
    parser.add_argument("--withNTT", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)


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
def bits_to_flip_generator(logQ: int, logDelta: int, bit_per_coeff: int):
    res = []

    M = bit_per_coeff - 1

    def clamp(v: int) -> int:
        return min(v, M)

    def push_unique(v: int):
        v = clamp(v)
        if v not in res:
            res.append(v)

    # --- Región A: ruido ---
    push_unique(0)
    push_unique(logDelta // 4)

    # --- Región B: transición ---
    push_unique(logDelta // 2)
    if logDelta > 0:
        push_unique(logDelta - 1)

    # --- Región C: mensaje ---
    push_unique(logDelta)
    push_unique((logDelta + logQ) // 2)

    # --- Región D: borde módulo ---
    if logQ > 0:
        push_unique(logQ - 1)
    push_unique(logQ)

    # --- Región E: overflow ---
    push_unique((logQ + M) // 2)
    push_unique(M)

    return res
