import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config

import matplotlib.pyplot as plt
from utils.args import parse_args, build_filters
from  utils.bitflip_utils import bits_to_flip_generator
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.plotters import plot_bit
from utils.df_utils import stats_by_bit

show = config.show
width = int(config.width)
s = config.size
colors = config.colors

dir = "img/"
savename = "logN"

BASELINE_SMALL_LOGN = 6
BASELINE_SMALL_LOGSLOTS = 5
    ########################## ARGS ################################
    ########################## DATA ################################
    ########################## STATS ###############################
    ########################## PLOT ################################


def main():
    ########################## ARGS ################################
    args = parse_args()
    filters_large = build_filters(args)
    print("Filtros activos:", filters_large)

    filters_small = filters_large.copy()
    filters_small["logN"] = ("int", BASELINE_SMALL_LOGN)
    filters_small["logSlots"] = ("int", BASELINE_SMALL_LOGSLOTS)

    ########################## DATA ################################
    selected_large = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_large)
    selected_small = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_small)

    if selected_large.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")
    if selected_small.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data_large = load_campaign_data(selected_large, config.DATA_DIR)
    data_small = load_campaign_data(selected_small, config.DATA_DIR)

    ########################## STATS ###############################
    df_small = stats_by_bit(data_small)
    df_large = stats_by_bit(data_large)

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))

    plot_bit(df_small, ax=ax, color=colors["blue"], label_prefix=f"logN={BASELINE_SMALL_LOGN} – ", scatter=True)
    plot_bit(df_large, ax=ax, color=colors["red"],label_prefix=f"logN={args.logN} – ", scatter=True)

    plt.savefig(dir + f"{savename}.pdf", bbox_inches="tight")
    plt.savefig(dir + f"{savename}.png", bbox_inches="tight")
    if show:
        plt.show()

if __name__ == "__main__":
    main()


