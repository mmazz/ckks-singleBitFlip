from utilsGen import cartesian_product_rows, write_csv, SEEDS_PRNG, SEEDS_INP, EXTRA_SEEDS, SEEDS_PRNG_NN, SEEDS_INP_NN
ADD_STEPS = 5
MUL_STEPS = 26
RESCALE_STEPS = 3
ROT_STEPS = 11
BOOTOUT_STEPS = 7
BOOTEVAL_STEPS = 15


def gen_testML_analysis():
    variants = [
        {"library": "heaan",   "bitPerCoeff": 128},
        {"library": "openfhe", "bitPerCoeff": 64},
    ]
    sweep = {
        "seed": list(range(1, 3)),
        "seed_input": list(range(1, 3)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "exhaustiveSingleBitFlip",
            "logN": 6,
            "library": "heaan",
            "logSlots": 4,
            "logQ": 60,
            "logDelta": 40,
            "stage": "encode",
            "withNTT": 0,
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("heaan_VS_openfhe_plain_analysis", rows)

    ]
    sweep = {
        "seed": list(range(1, 2)),
        "seed_input": list(range(1, 2)),
        "op_step": list(range(0,ADD_STEPS+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "logN": 6,
            "logSlots": 4,
            "library": "heaan",
            "logQ": 160,
            "logDelta": 30,
            "bitPerCoeff": 180,
            "withNTT": 0,
            "stage": "add_inside",
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("testML_add_analysis", rows)

def gen_testML_mul_analysis():
    variants = [
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 0, "doBoot": 0},
        {"doAdd": 2,   "doPlainMul": 0, "doMul": 3, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 1, "doMul": 2, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 1, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 1, "doRot": 1, "doBoot": 0},

    ]
    sweep = {
        "seed": list(range(1, 2)),
        "seed_input": list(range(1, 2)),
        "op_step": list(range(0,MUL_STEPS+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "logN": 6,
            "logSlots": 4,
            "library": "heaan",
            "logQ": 160,
            "logDelta": 30,
            "bitPerCoeff": 180,
            "withNTT": 0,
            "stage": "mul_inside",
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("testML_mul_analysis", rows)


def gen_testML_rot_analysis():
    variants = [
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 2, "doBoot": 0},
        {"doAdd": 2,   "doPlainMul": 0, "doMul": 3, "doRot": 1, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 1, "doMul": 2, "doRot": 3, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 1, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 1, "doRot": 2, "doBoot": 0},

    ]
    sweep = {
        "seed": list(range(1, 2)),
        "seed_input": list(range(1, 2)),
        "op_step": list(range(0,ROT_STEPS+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "logN": 6,
            "logSlots": 4,
            "library": "heaan",
            "logQ": 160,
            "logDelta": 30,
            "bitPerCoeff": 180,
            "withNTT": 0,
            "stage": "rot_inside",
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("testML_rot_analysis", rows)

def gen_testML_rescale_analysis():
    variants = [
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 2, "doBoot": 0},
        {"doAdd": 2,   "doPlainMul": 0, "doMul": 3, "doRot": 1, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 1, "doMul": 2, "doRot": 3, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 1, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 1, "doRot": 2, "doBoot": 0},

    ]
    sweep = {
        "seed": list(range(1, 2)),
        "seed_input": list(range(1, 2)),
        "op_step": list(range(0,RESCALE_STEPS+1)),
    }
    rows = []
    for v in variants:
        fixed = {
            "binary": "randomSingleBitFlip",
            "logN": 6,
            "logSlots": 4,
            "library": "heaan",
            "logQ": 160,
            "logDelta": 30,
            "bitPerCoeff": 180,
            "withNTT": 0,
            "stage": "rescale_inside",
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("testML_rescale_analysis", rows)

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


def gen_opServerBootOutside_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG_NN+1)),
        "seed_input": list(range(1, SEEDS_INP_NN+1)),
        "op_step": list(range(0,BOOTOUT_STEPS+1)),
    }
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaan",
        "stage": "boot_outside",
        "logN": 6,
        "logDelta": 34,
        "bitPerCoeff": 640,
        "logSlots": 4,
        "logQ": 620,
        "doMul": 4,
        "doBoot": 1,
        "withNTT": 0,
    }

    write_csv("bootOutside_analysis", cartesian_product_rows(fixed, sweep))

def gen_opServerBootEval_analysis():
    sweep = {
        "seed": list(range(1, SEEDS_PRNG_NN+1)),
        "seed_input": list(range(1, SEEDS_INP_NN+1)),
        "op_step": list(range(0,BOOTEVAL_STEPS+1)),
    }
    fixed = {
        "binary": "randomSingleBitFlip",
        "library": "heaan",
        "stage": "boot_eval",
        "logN": 6,
        "logDelta": 34,
        "bitPerCoeff": 640,
        "logSlots": 4,
        "logQ": 620,
        "doMul": 4,
        "doBoot": 1,
        "withNTT": 0,
    }

    write_csv("bootEval_analysis", cartesian_product_rows(fixed, sweep))

