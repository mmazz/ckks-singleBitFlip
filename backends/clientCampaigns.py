from utilsGen import cartesian_product_rows, write_csv, SEEDS_PRNG, SEEDS_INP, EXTRA_SEEDS, STAGES

seed_init = 3
seed_list = list(range(seed_init, seed_init+SEEDS_PRNG+1))

def gen_heaan_VS_openfhe_plain_analysis():
    variants = [
        {"library": "heaan",   "bitsPerCoeff": 128},
        {"library": "openfhe", "bitsPerCoeff": 64},
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
        "bitsPerCoeff": 64,
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
        "bitsPerCoeff": 64,
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
        "stage":STAGES
    }
    rows = []
    for v in variants:
        fixed = {
            "library": "heaan",
            "logQ": 60,
            "bitsPerCoeff": 64,
            "logDelta": 40,
            #"stage": "encrypt_c0",
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("logN_analysis", rows)

def gen_logQ_analysis():
    variants = [
        {"logQ": 40, "bitsPerCoeff": 50, "logDelta": 30},
        {"logQ": 60, "bitsPerCoeff": 75, "logDelta": 45},
        {"logQ": 80, "bitsPerCoeff": 100, "logDelta": 60},
        {"logQ": 100, "bitsPerCoeff": 125, "logDelta": 75},
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
            "bitsPerCoeff": 64,
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
            "bitsPerCoeff": 64,
            "logQ": 60,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("gap_analysis", rows)

def gen_boot_analysis():
    variants = [
        {"stage": "encode" ,     "bitsPerCoeff": 1280},
        {"stage": "encrypt_c0" , "bitsPerCoeff": 640},
        {"stage": "encrypt_c1" , "bitsPerCoeff": 640},
        {"stage": "decrypt_c0" , "bitsPerCoeff": 640},
        {"stage": "decrypt_c1" , "bitsPerCoeff": 640},
        {"stage": "decode" , "bitsPerCoeff": 640},
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
            "bitsPerCoeff": 64,
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
        {"stage": "encode" ,     "bitsPerCoeff": 128},
        {"stage": "encrypt_c0" , "bitsPerCoeff": 64},
        {"stage": "encrypt_c1" , "bitsPerCoeff": 64},
    ]
    sweep = {
        "seed": seed_list,
        "seed_input":seed_list,
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
        {"stage": "encode" ,     "bitsPerCoeff": 128},
        {"stage": "encrypt_c0" , "bitsPerCoeff": 64},
        {"stage": "encrypt_c1" , "bitsPerCoeff": 64},
    ]
    sweep = {
        "seed":seed_list,
        "seed_input":seed_list,
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
        {"stage": "encode" ,     "bitsPerCoeff": 128},
        {"stage": "encrypt_c0" , "bitsPerCoeff": 64},
        {"stage": "encrypt_c1" , "bitsPerCoeff": 64},
    ]
    sweep = {
        "seed":seed_list,
        "seed_input":seed_list,
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
        "seed":seed_list,
        "seed_input":seed_list,
        "doMul": [1, 2, 3],
        "stage": ["encode", "encrypt_c0", "encrypt_c1"]
    }
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "logN": 6,
        "logQ": 120,
        "bitsPerCoeff": 150,
        "logDelta": 30,
        "logSlots": 4,
        "withNTT": 0,
    }

    write_csv("opClientMul_analysis", cartesian_product_rows(fixed, sweep))

def gen_NN_sim_analysis():
    variants = [
            {"doAdd": 2 , "doPlainMul": 3, "doMul": 2, "doRot": 1},
            {"doAdd": 2 , "doPlainMul": 2, "doMul": 2, "doRot": 1},
            {"doAdd": 2 , "doPlainMul": 2, "doMul": 2, "doRot": 0},
            {"doAdd": 1 , "doPlainMul": 2, "doMul": 2, "doRot": 0},
            {"doAdd": 1 , "doPlainMul": 2, "doMul": 1, "doRot": 0},
            {"doAdd": 1 , "doPlainMul": 1, "doMul": 1, "doRot": 0},
            {"doAdd": 1 , "doPlainMul": 1, "doMul": 0, "doRot": 0},
            {"doAdd": 1 , "doPlainMul": 0, "doMul": 0, "doRot": 0},


    ]
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "stage": ["encrypt_c0", "encrypt_c1"]
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "library": "heaan",
            "logN": 6, 
            "logQ": 220,
            "bitsPerCoeff": 250,
            "logDelta": 30,
            "logSlots": 4,
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("NN_sim_analysis", rows)

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

def gen_opClient_RNS_analysis():

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
        "doAdd":1,
        "doRot":1,
        "doMul": 2,
        "mult_depth": 3,
    }
    write_csv("opClient_RNS_analysis", cartesian_product_rows(fixed, sweep))

def gen_opClient_RNS_NTT_analysis():

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
        "withNTT": 1,
        "doAdd":1,
        "doRot":1,
        "doMul": 2,
        "mult_depth": 3,
    }
    write_csv("opClient_RNS_NTT_analysis", cartesian_product_rows(fixed, sweep))


