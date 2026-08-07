from utilsGen import cartesian_product_rows, write_csv, SEEDS_PRNG, SEEDS_INP, EXTRA_SEEDS, stages

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

    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,13+1))
    }
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
    }

    write_csv("heaanNN_hidden_analysis", cartesian_product_rows(fixed, sweep))

def gen_heaanNN_cheby_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_step": list(range(0,9+1))
    }
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
    }

    write_csv("heaanNN_cheby_analysis", cartesian_product_rows(fixed, sweep))


def gen_openfheNN_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "withNTT": list(range(0,2)),
        "stages": stages
    }
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "openfheNN",
        "logN": 12,
        "logQ": 60,
        "bitPerCoeff": 64,
        "logDelta": 50,
        "logSlots": 10,
        "mult_depth": 5,
    }
    write_csv("openfheNN_analysis", cartesian_product_rows(fixed, sweep))




