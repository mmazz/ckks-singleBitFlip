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
