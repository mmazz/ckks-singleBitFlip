#!/usr/bin/env python3
"""
generate_config.py — Genera un CSV de config para run_campaign.py a partir de
un producto cartesiano de parámetros, definido en un diccionario Python.
Uso:
  python generate_config.py  -> escribe configs/<nombre>.csv
"""

import csv
import itertools
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SEEDS_PRNG = 5
SEEDS_INP = 5
EXTRA_SEEDS = 20
stages = ["encode", "encrypt_c0", "encrypt_c1", "decrypt_c0", "decrypt_c1", "decode"]


ADD_STEPS = 5
MUL_STEPS = 25
RESCALE_STEPS = 3
ROT_STEPS = 11

def cartesian_product_rows(fixed: dict, sweep: dict) -> list[dict]:
    """
    variants: parámetros que varian en pares o solos
    fixed: parámetros que NO varían (mismo valor en todas las filas)
    sweep: parámetros que SÍ varían -> se genera el producto cartesiano de sus listas

    Devuelve una lista de dicts (filas), cada una con run_id ya generado.
    """
    sweep_keys = list(sweep.keys())
    sweep_values = [sweep[k] for k in sweep_keys]

    rows = []
    for combo in itertools.product(*sweep_values):
        row = dict(fixed)
        row.update(dict(zip(sweep_keys, combo)))
        # run_id legible: junta los valores que varían, ej. "s1_si2"
        run_id_parts = [f"{k}{v}" for k, v in zip(sweep_keys, combo)]
        row["run_id"] = "_".join(run_id_parts)
        rows.append(row)
    return rows

def write_csv(name: str, rows: list[dict]):
    if not rows:
        print(f"[{name}] no se generaron filas, se omite.")
        return
    all_keys = []
    for row in rows:
        for k in row.keys():
            if k not in all_keys:
                all_keys.append(k)
    ordered = ["run_id", "binary", "library"] + [
        k for k in all_keys if k not in ("run_id", "binary", "library")
    ]

    out_path = CONFIG_DIR / f"{name}.csv"
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[{name}] {len(rows)} filas -> {out_path}")

def gen_heaan_VS_openfhe_plain_analysis():
    variants = [
        {"library": "heaan",   "bitPerCoeff": 128},
        {"library": "openfhe", "bitPerCoeff": 64},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "logN": 6,
            "logSlots": 5,
            "logQ": 60,
            "logDelta": 40,
            "stage": "encode",
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("heaan_VS_openfhe_plain_analysis", rows)


def gen_heaan_plain_VS_c0_VS_c1_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "stage": ["encode", "encrypt_c0", "encrypt_c1"],
        "library": ["openfhe", "heaan"],
    }
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "logN": 6,
        "logSlots": 5,
        "bitPerCoeff": 64,
        "logQ": 60,
        "logDelta": 40,
        "withNTT": 0,
    }
    write_csv("heaan_plain_VS_c0_VS_c1_analysis", cartesian_product_rows(fixed, sweep))

def gen_seeds_analysis():
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "logN": 6,
        "logQ": 60,
        "bitPerCoeff": 64,
        "logDelta": 40,
        "stage": "encrypt_c0",
        "logSlots": 5,
        "withNTT": 0,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1+EXTRA_SEEDS)),
        "seed_input": list(range(1, SEEDS_INP+1+EXTRA_SEEDS)),
    }
    write_csv("seeds_analysis", cartesian_product_rows(fixed, sweep))

def gen_logN_analysis():
    variants = [
        {"logN": 16, "logSlots": 15, "binary": "randomSingleBitFlip"},
        {"logN": 6,  "logSlots": 5, "binary": "exhaustiveSingleBitFlip"},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "stage":stages
    }
    rows = []
    for v in variants:
        fixed = {
            "library": "heaan",
            "logQ": 60,
            "bitPerCoeff": 64,
            "logDelta": 40,
            #"stage": "encrypt_c0",
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("logN_analysis", rows)

def gen_logQ_analysis():
    variants = [
        {"logQ": 40, "bitPerCoeff": 50, "logDelta": 30},
        {"logQ": 60, "bitPerCoeff": 75, "logDelta": 45},
        {"logQ": 80, "bitPerCoeff": 100, "logDelta": 60},
        {"logQ": 100, "bitPerCoeff": 125, "logDelta": 75},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logSlots": 5,
            "stage": "encrypt_c0",
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("logQ_analysis", rows)

def gen_logDelta_analysis():
    variants = [
        {"logDelta": 25},
        {"logDelta": 35},
        {"logDelta": 45},
        {"logDelta": 55},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logSlots": 5,
            "bitPerCoeff": 64,
            "logQ": 60,
            "stage": "encrypt_c0",
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("logDelta_analysis", rows)


def gen_gap_analysis():
    variants = [
        {"logSlots": 5},
        {"logSlots": 4},
        {"logSlots": 3},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "stage": ["encrypt_c0", "encrypt_c1", "decode"],
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logDelta": 40,
            "bitPerCoeff": 64,
            "logQ": 60,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("gap_analysis", rows)

def gen_boot_analysis():
    variants = [
        {"stage": "encode" ,     "bitPerCoeff": 1280},
        {"stage": "encrypt_c0" , "bitPerCoeff": 640},
        {"stage": "encrypt_c1" , "bitPerCoeff": 640},
        {"stage": "decrypt_c0" , "bitPerCoeff": 640},
        {"stage": "decrypt_c1" , "bitPerCoeff": 640},
        {"stage": "decode" , "bitPerCoeff": 640},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "doBoot": list(range(0,2)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logDelta": 34,
            "logSlots": 4,
            "logQ": 620,
            "doMul": 4,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("boot_analysis", rows)

def gen_heaanNN_analysis():
    variants = [
        {"stage": "encode"     , "bitPerCoeff": 500},
        {"stage": "encrypt_c0" , "bitPerCoeff": 250},
        {"stage": "encrypt_c1" , "bitPerCoeff": 250},
        {"stage": "decrypt_c0" , "bitPerCoeff": 250},
        {"stage": "decrypt_c1" , "bitPerCoeff": 250},
        {"stage": "decode"     , "bitPerCoeff": 250},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "library": "heaanNN",
            "logN": 12,
            "logQ": 220,
            "logDelta": 30,
            "logSlots": 10,
            "mult_depth": 0,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("heaanNN_analysis", rows)

def gen_openfheNN_analysis():
    variants = [
        {"stage": "encode"      },
        {"stage": "encrypt_c0"  },
        {"stage": "encrypt_c1"  },
        {"stage": "decrypt_c0"  },
        {"stage": "decrypt_c1"  },
        {"stage": "decode"      },
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "withNTT": list(range(1,3)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "library": "openfheNN",
            "logN": 12,
            "logQ": 60,
            "bitPerCoeff": 64,
            "logDelta": 50,
            "logSlots": 10,
            "mult_depth": 5,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("openfheNN_analysis", rows)

def gen_input_analysis():
    variants = [
            {"logMin": 0,  "logMax": 1},
            {"logMin": 9,  "logMax": 10},
            {"logMin": 19,  "logMax": 20},
            {"logMin": 29,  "logMax": 30},
        ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logQ": 60,
            "bitPerCoeff": 64,
            "logDelta": 20,
            "stage": "encrypt_c0",
            "logSlots": 5,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("input_analysis", rows)

def gen_opClientAdd_analysis():
    variants = [
        {"stage": "encode" ,     "bitPerCoeff": 128},
        {"stage": "encrypt_c0" , "bitPerCoeff": 64},
        {"stage": "encrypt_c1" , "bitPerCoeff": 64},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "doAdd": [1, 2, 3]
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logQ": 60,
            "logDelta": 30,
            "logSlots": 4,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("opClientAdd_analysis", rows)

def gen_opClientRot_analysis():
    variants = [
        {"stage": "encode" ,     "bitPerCoeff": 128},
        {"stage": "encrypt_c0" , "bitPerCoeff": 64},
        {"stage": "encrypt_c1" , "bitPerCoeff": 64},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "doRot": [1, 2, 3]
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logQ": 60,
            "logDelta": 30,
            "logSlots": 4,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("opClientRot_analysis", rows)

def gen_opClientAddRot_analysis():
    variants = [
        {"stage": "encode" ,     "bitPerCoeff": 128},
        {"stage": "encrypt_c0" , "bitPerCoeff": 64},
        {"stage": "encrypt_c1" , "bitPerCoeff": 64},
    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6,
            "logQ": 60,
            "logDelta": 30,
            "logSlots": 4,
            "withNTT": 0,
            "doAdd": 3,
            "doRot": 2,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("opClientAddRot_analysis", rows)



def gen_opClientMul_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "doMul": [1, 2, 3],
        "stage": ["encode", "encrypt_c0", "encrypt_c1"]
    }
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 150,
        "logDelta": 30,
        "logSlots": 4,
        "withNTT": 0,
    }

    write_csv("opClientMul_analysis", cartesian_product_rows(fixed, sweep))

def gen_opClientAddRot_RNS_analysis():

    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "stage": ["encode", "encrypt_c0", "encrypt_c1"]
    }
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "openfhe",
        "logN": 6,
        "logQ": 60,
        "logDelta": 30,
        "logSlots": 4,
        "withNTT": 0,
        "doAdd": 3,
        "doRot": 2,
        "mult_depth": 3,
    }
    write_csv("opClientAddRot_RNS_analysis", cartesian_product_rows(fixed, sweep))

def gen_opClientMul_RNS_analysis():

    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "stage": ["encode", "encrypt_c0", "encrypt_c1"]
    }
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "openfhe",
        "logN": 6,
        "logQ": 60,
        "logDelta": 30,
        "logSlots": 4,
        "withNTT": 0,
        "doMul": 1,
        "mult_depth": 3,
    }
    write_csv("opClientAddRot_RNS_analysis", cartesian_product_rows(fixed, sweep))


def gen_opServerAdd_analysis():
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 144,
        "logDelta": 40,
        "stage": "add_inside",
        "doAdd": 2,
        "op_depth": 0,
        "logSlots": 4,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,ADD_STEPS+1)),
    }
    write_csv("opServerAdd_analysis", cartesian_product_rows(fixed, sweep))


def gen_opServerMul_analysis():
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 144,
        "logDelta": 40,
        "stage": "mul_inside",
        "doMul": 1,
        "op_depth": 0,
        "mult_depth": 0,
        "logSlots": 4,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,MUL_STEPS+1)),
    }
    write_csv("opServerMul_analysis", cartesian_product_rows(fixed, sweep))

def gen_opServerMulDepth_analysis():
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 144,
        "logDelta": 40,
        "stage": "mul_inside",
        "doMul": 2,
        "op_depth": 0,
        "mult_depth": 0,
        "logSlots": 4,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,MUL_STEPS+1)),
    }
    write_csv("opServerMulDepth_analysis", cartesian_product_rows(fixed, sweep))


def gen_opServerRescaleDepth_analysis():
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 144,
        "logDelta": 40,
        "stage": "rescale_inside",
        "doMul": 2,
        "mult_depth": 0,
        "logSlots": 4,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,RESCALE_STEPS+1)),
        "op_depth": [0,1],
    }
    write_csv("opServerRescaleDepth_analysis", cartesian_product_rows(fixed, sweep))

def gen_opServerRot_analysis():
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 144,
        "logDelta": 40,
        "stage": "rot_inside",
        "doRot": 2,
        "logSlots": 4,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,ROT_STEPS+1)),
    }
    write_csv("opServerRot_analysis", cartesian_product_rows(fixed, sweep))





if __name__ == "__main__":
    gen_heaan_VS_openfhe_plain_analysis()
    gen_heaan_plain_VS_c0_VS_c1_analysis()
    gen_seeds_analysis()
    gen_logN_analysis()
    gen_logQ_analysis()
    gen_logDelta_analysis()
    gen_gap_analysis()
    gen_boot_analysis()
    gen_input_analysis()

    # ops client
    gen_opClientAdd_analysis()
    gen_opClientRot_analysis()
    gen_opClientAddRot_analysis()
    gen_opClientMul_analysis()
    gen_opClientAddRot_RNS_analysis()


    # ops server
    gen_opServerAdd_analysis()
    gen_opServerMul_analysis()
    gen_opServerMulDepth_analysis()
    gen_opServerRescaleDepth_analysis()
    gen_opServerRot_analysis()

    # NN
    gen_heaanNN_analysis()
    gen_openfheNN_analysis()
