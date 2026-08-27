#!/usr/bin/env python3
"""
generate_config.py — Genera un CSV de config para run_campaign.py a partir de
un producto cartesiano de parámetros, definido en un diccionario Python.
Uso:
  python generate_config.py  -> escribe configs/<nombre>.csv
"""


from clientCampaigns import *
from serverCampaigns import *
from NNCampaigns import *
from utilsGen import cartesian_product_rows, write_csv
STAGES = ["encode", "encrypt_c0", "encrypt_c1", "decrypt_c0", "decrypt_c1", "decode"]
def gen_testML_analysis():
    variants = [
        {"doAdd": 0,   "doPlainMul": 0, "doMul": 3, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 0, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 1, "doMul": 0, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 1, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 2, "doRot": 1, "doBoot": 0},
        {"doAdd": 0,   "doPlainMul": 0, "doMul": 0, "doRot": 0, "doBoot": 0},
        {"doAdd": 2,   "doPlainMul": 0, "doMul": 0, "doRot": 2, "doBoot": 0},
        {"doAdd": 3,   "doPlainMul": 1, "doMul": 0, "doRot": 2, "doBoot": 0},
        {"doAdd": 0,   "doPlainMul": 0, "doMul": 0, "doRot": 0, "doBoot": 0},
        {"doAdd": 1,   "doPlainMul": 0, "doMul": 3, "doRot": 1, "doBoot": 0},
        {"doAdd": 3,   "doPlainMul": 0, "doMul": 2, "doRot": 2, "doBoot": 0},
        {"doAdd": 0,   "doPlainMul": 0, "doMul": 0, "doRot": 2, "doBoot": 0},
        {"doAdd": 0,   "doPlainMul": 0, "doMul": 3, "doRot": 0, "doBoot": 0}
    ]
    sweep = {
        "seed": list(range(1, 2)),
        "seed_input": list(range(1, 2)),
        "stage": STAGES,
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
            **v,
        }
        rows += cartesian_product_rows(fixed, sweep)

    write_csv("testML_analysis", rows)




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


    gen_testML_analysis()
    gen_testML_add_analysis()
    gen_testML_mul_analysis()
    gen_testML_rot_analysis()
    gen_testML_rescale_analysis()

    gen_testML_analysis()

    # ops server boot
    gen_opServerBootOutside_analysis()
    gen_opServerBootEval_analysis()

    # NN
    gen_heaanNN_analysis()
    gen_heaanNN_cheby_analysis()
    gen_heaanNN_hidden_analysis()
    gen_openfheNN_analysis()
