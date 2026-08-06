from utilsGen import cartesian_product_rows, write_csv, SEEDS_PRNG, SEEDS_INP, EXTRA_SEEDS
ADD_STEPS = 5
MUL_STEPS = 25
RESCALE_STEPS = 3
ROT_STEPS = 11



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



