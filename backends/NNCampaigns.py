from utilsGen import cartesian_product_rows, write_csv, SEEDS_PRNG_NN, SEEDS_INP_NN, STAGES

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
        "seed": list(range(1, SEEDS_PRNG_NN+1)),
        "seed_input": list(range(1, SEEDS_INP_NN+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "library": "heaanNN",
            "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
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
        "seed": list(range(1, SEEDS_PRNG_NN+1)),
        "seed_input": list(range(1, SEEDS_INP_NN+1)),
        "op_step": list(range(0,13+1))
    }
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaanNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 220,
        "bitPerCoeff": 250,
        "logDelta": 30,
        "logSlots": 10,
        "mult_depth": 0,
        "withNTT": 0,
        "stage": "hidden_layer",
    }

    write_csv("heaanNN_hidden_analysis", cartesian_product_rows(fixed, sweep))

def gen_heaanNN_cheby_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG_NN+1)),
        "seed_input": list(range(1, SEEDS_INP_NN+1)),
        "op_step": list(range(0,9+1))
    }
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaanNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 220,
        "bitPerCoeff": 250,
        "logDelta": 30,
        "logSlots": 10,
        "mult_depth": 0,
        "withNTT": 0,
        "stage": "cheby_tanh3",
    }

    write_csv("heaanNN_cheby_analysis", cartesian_product_rows(fixed, sweep))


def gen_openfheNN_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG_NN+1)),
        "seed_input": list(range(1, SEEDS_INP_NN+1)),
        "withNTT": list(range(0,2)),
        "stages": STAGES
    }
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "openfheNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 60,
        "bitPerCoeff": 64,
        "logDelta": 50,
        "logSlots": 10,
        "mult_depth": 5,
    }
    write_csv("openfheNN_analysis", cartesian_product_rows(fixed, sweep))



ADD_STEPS = 5
MUL_STEPS = 26
RESCALE_STEPS = 3
ROT_STEPS = 11
BOOTOUT_STEPS = 7
BOOTEVAL_STEPS = 15



def gen_opNNAdd_analysis():
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaanNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 220,
        "bitPerCoeff": 250,
        "logDelta": 30,
        "logSlots": 10,
        "mult_depth": 0,
        "withNTT": 0,
        "op_depth": 0,
        "stage": "add_inside",
    }


    sweep = {
        "seed": list(range(1, 1+1)),
        "seed_input": list(range(1, 1+1)),
        "op_step": list(range(0,ADD_STEPS+1)),
    }
    write_csv("opNNAdd_analysis", cartesian_product_rows(fixed, sweep))


def gen_opNNMul_analysis():
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaanNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 220,
        "bitPerCoeff": 250,
        "logDelta": 30,
        "logSlots": 10,
        "mult_depth": 0,
        "withNTT": 0,
        "op_depth": 0,
        "stage": "mul_inside",
    }


    sweep = {
        "seed": list(range(1, 1+1)),
        "seed_input": list(range(1, 1+1)),
        "op_step": list(range(0,MUL_STEPS+1)),
    }
    write_csv("opNNMul_analysis", cartesian_product_rows(fixed, sweep))


def gen_opNNRescaleDepth_analysis():
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaanNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 220,
        "bitPerCoeff": 250,
        "logDelta": 30,
        "logSlots": 10,
        "mult_depth": 0,
        "withNTT": 0,
        "op_depth": 0,
        "stage": "rescale_inside",
    }


    sweep = {
        "seed": list(range(1, 1+1)),
        "seed_input": list(range(1, 1+1)),
        "op_step": list(range(0,RESCALE_STEPS+1)),
    }
    write_csv("opNNRescaleDepth_analysis", cartesian_product_rows(fixed, sweep))

def gen_opNNRot_analysis():
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaanNN",
        "results": "/home/mmazz/ckks-singleBitFlip/results_NN",
        "logN": 12,
        "logQ": 220,
        "bitPerCoeff": 250,
        "logDelta": 30,
        "logSlots": 10,
        "mult_depth": 0,
        "withNTT": 0,
        "op_depth": 0,
        "stage": "rot_inside",
    }


    sweep = {
        "seed": list(range(1, 1+1)),
        "seed_input": list(range(1, 1+1)),
        "op_step": list(range(0,ROT_STEPS+1)),
    }
    write_csv("opNNRot_analysis", cartesian_product_rows(fixed, sweep))



