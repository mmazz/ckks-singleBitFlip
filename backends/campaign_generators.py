"""
Campaign generators for the exhaustiveSingleBitFlip fault-injection sweeps.

Design notes (see chat for the full rationale):

- logN, logSlots, logQ, logDelta and op_depth are now swept instead of fixed,
  subject to the constraints below. bitPerCoeff is *derived* from logQ
  (bitPerCoeff = logQ + 10), never swept independently.
- seed / seed_input are no longer swept: they are fixed constants
  (SEED_FIXED / SEED_INPUT_FIXED) so the CSV schema is unchanged but the
  campaign no longer multiplies its size by SEEDS_PRNG * SEEDS_INP.
- "small variety" was chosen: 2-3 candidate values per parameter, so the
  structural grid stays in the tens of combinations. Since op_step already
  performs an *exhaustive* per-bit sweep for the targeted stage, every extra
  structural combination multiplies the total row count by the full
  ADD_STEPS/MUL_STEPS/RESCALE_STEPS/ROT_STEPS range -- keep these lists short
  unless you deliberately want a much bigger campaign.

Global constraints enforced by build_structural_variants():
    4 < logN < 9                      -> logN in {5, 6, 7, 8}
    0 < logSlots < logN
    0 < logDelta < 50
    logQ < 200
    logQ > logDelta * (1 + doMul), with margin >= 20
        i.e. logQ >= logDelta * (1 + doMul) + 20
    bitPerCoeff = logQ + 10

Per-function constraints enforced by the caller:
    doMul <= 3, doAdd <= 3, doRot <= 3
    op_depth <= the doOp actually exercised by that stage
"""

import itertools

from utilsGen import cartesian_product_rows, write_csv

# Seeds are no longer swept -- fixed constants instead.
SEED_FIXED = 1
SEED_INPUT_FIXED = 1
ADD_STEPS = 5
MUL_STEPS = 26
RESCALE_STEPS = 3
ROT_STEPS = 11
BOOTOUT_STEPS = 7
BOOTEVAL_STEPS = 15



def build_structural_variants(doMul, logN_values, logDelta_values, logQ_margins):
    """
    Build the list of valid (logN, logSlots, logDelta, logQ, bitPerCoeff)
    combinations for a given doMul (doMul is whatever value is fixed for the
    stage being generated -- 0 if the stage does not exercise multiplication
    at all).

    logQ_margins: extra margins added on top of the *minimum* valid logQ
    (logDelta * (1 + doMul) + 20), e.g. [0, 20] tries the tightest valid logQ
    and one 20 bits looser. Values that would push logQ >= 200 are dropped.
    """
    variants = []
    for logN in logN_values:
        assert 4 < logN < 9, f"logN={logN} violates 4 < logN < 9"
        for logSlots in range(1, logN):
            for logDelta in logDelta_values:
                assert 0 < logDelta < 50, f"logDelta={logDelta} violates 0 < logDelta < 50"
                min_logQ = logDelta * (1 + doMul) + 20
                for margin in logQ_margins:
                    logQ = min_logQ + margin
                    if logQ >= 200:
                        continue
                    assert logQ > logDelta + doMul * logDelta
                    variants.append({
                        "logN": logN,
                        "logSlots": logSlots,
                        "logDelta": logDelta,
                        "logQ": logQ,
                        "bitPerCoeff": logQ + 10,
                    })
    return variants


def expand_campaign(common_fixed, structural_variants, op_depth_values, op_step_values):
    """
    Cartesian product of (structural_variants) x (op_depth_values) x
    (op_step_values), merged on top of common_fixed. seed/seed_input are
    added here as fixed constants (see SEED_FIXED / SEED_INPUT_FIXED).
    """
    rows = []
    for variant, op_depth, op_step in itertools.product(
        structural_variants, op_depth_values, op_step_values
    ):
        row = dict(common_fixed)
        row.update(variant)
        row["op_depth"] = op_depth
        row["op_step"] = op_step
        row["seed"] = SEED_FIXED
        row["seed_input"] = SEED_INPUT_FIXED
        rows.append(row)
    return rows


# Small, shared "variety" grid. Tweak here to widen/narrow every generator at
# once, or override per-function below if a stage needs something different.
DEFAULT_LOGN_VALUES = [5, 6, 8]
DEFAULT_LOGDELTA_VALUES = [20, 35]
DEFAULT_LOGQ_MARGINS = [0, 20]


def gen_opServerAdd_analysis():
    doAdd = 2
    common_fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "stage": "add_inside",
        "doAdd": doAdd,
    }
    structural_variants = build_structural_variants(
        doMul=0,  # this stage does not exercise multiplication
        logN_values=DEFAULT_LOGN_VALUES,
        logDelta_values=DEFAULT_LOGDELTA_VALUES,
        logQ_margins=DEFAULT_LOGQ_MARGINS,
    )
    op_depth_values = list(range(0, doAdd + 1))  # op_depth <= doAdd
    op_step_values = list(range(0, ADD_STEPS + 1))
    rows = expand_campaign(common_fixed, structural_variants, op_depth_values, op_step_values)
    write_csv("opServerAdd_analysis", rows)


def gen_opServerMul_analysis():
    doMul = 1
    common_fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "stage": "mul_inside_asplos",
        "doMul": doMul,
        "mult_depth": 0,
    }
    structural_variants = build_structural_variants(
        doMul=doMul,
        logN_values=DEFAULT_LOGN_VALUES,
        logDelta_values=DEFAULT_LOGDELTA_VALUES,
        logQ_margins=DEFAULT_LOGQ_MARGINS,
    )
    op_depth_values = list(range(0, doMul + 1))  # op_depth <= doMul
    op_step_values = list(range(0, MUL_STEPS + 1))
    rows = expand_campaign(common_fixed, structural_variants, op_depth_values, op_step_values)
    write_csv("opServerMul_analysis", rows)


def gen_opServerMulDepth_analysis():
    doMul = 2
    common_fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "stage": "mul_inside_asplos",
        "doMul": doMul,
        "mult_depth": 0,
    }
    structural_variants = build_structural_variants(
        doMul=doMul,
        logN_values=DEFAULT_LOGN_VALUES,
        logDelta_values=DEFAULT_LOGDELTA_VALUES,
        logQ_margins=DEFAULT_LOGQ_MARGINS,
    )
    op_depth_values = list(range(0, doMul + 1))  # op_depth <= doMul
    op_step_values = list(range(0, MUL_STEPS + 1))
    rows = expand_campaign(common_fixed, structural_variants, op_depth_values, op_step_values)
    write_csv("opServerMulDepth_analysis", rows)


def gen_opServerRescaleDepth_analysis():
    doMul = 2
    common_fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "stage": "rescale_inside",
        "doMul": doMul,
        "mult_depth": 0,
    }
    structural_variants = build_structural_variants(
        doMul=doMul,
        logN_values=DEFAULT_LOGN_VALUES,
        logDelta_values=DEFAULT_LOGDELTA_VALUES,
        logQ_margins=DEFAULT_LOGQ_MARGINS,
    )
    op_depth_values = list(range(0, doMul + 1))  # op_depth <= doMul (was fixed [0,1])
    op_step_values = list(range(0, RESCALE_STEPS + 1))
    rows = expand_campaign(common_fixed, structural_variants, op_depth_values, op_step_values)
    write_csv("opServerRescaleDepth_analysis", rows)


def gen_opServerRot_analysis():
    doRot = 2
    common_fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "stage": "rot_inside_asplos",
        "doRot": doRot,
    }
    structural_variants = build_structural_variants(
        doMul=0,  # this stage does not exercise multiplication
        logN_values=DEFAULT_LOGN_VALUES,
        logDelta_values=DEFAULT_LOGDELTA_VALUES,
        logQ_margins=DEFAULT_LOGQ_MARGINS,
    )
    # NOTE: the original fixed dict for this stage had no op_depth at all.
    # Added here for depth variety, bounded by doRot as instructed
    # ("op_depth <= the doOp used"). Remove this block if rot depth is not
    # actually a meaningful axis for this stage.
    op_depth_values = list(range(0, doRot + 1))  # op_depth <= doRot
    op_step_values = list(range(0, ROT_STEPS + 1))
    rows = expand_campaign(common_fixed, structural_variants, op_depth_values, op_step_values)
    write_csv("opServerRot_analysis", rows)



if __name__ == "__main__":
    gen_opServerAdd_analysis()
    gen_opServerMul_analysis()
    gen_opServerMulDepth_analysis()
    gen_opServerRescaleDepth_analysis()
    gen_opServerRot_analysis()


