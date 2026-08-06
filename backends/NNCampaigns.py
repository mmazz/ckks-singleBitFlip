from utilsGen import cartesian_product_rows, write_csv, SEEDS_PRNG, SEEDS_INP, EXTRA_SEEDS

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

def gen_heaanNN_hidden_analysis():
    variants = [
        {"op_step": list(range(0,13+1)) },

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
            "stage": "hidden_layer",
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("heaanNN_hidden_analysis", rows)

def gen_heaanNN_cheby_analysis():
    variants = [
        {"op_step": list(range(0,9+1)) },

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
            "stage": "cheby_tanh3",
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("heaanNN_cheby_analysis", rows)


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



