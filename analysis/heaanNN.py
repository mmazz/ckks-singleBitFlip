import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy

sys.path.append(os.path.abspath("./"))
from utils import config

from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.df_utils import split_by_gap, stats_by_bit_sdc
from utils.plotters import plot_bit_cat
show = config.show
width = int(config.width)
colors = config.colors
s = config.size
c = [colors["red"], colors["blue"]]

dir = "img/"

SAVENAME = "heaan_NN"


def main():
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title


    filters = build_filters(args)

    selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

    if selected.empty:
        print(f"[WARN] No campaigns for doMul")

    data = load_campaign_data(selected, config.DATA_DIR)
    fig, ax = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    i = 0
    s = config.size
    alpha = config.alpha

    ########################## DATA ################################
    selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)
    data = load_campaign_data(selected, config.DATA_DIR)

    ########################## STATS ###############################
    stats_gaps, gap = split_by_gap(data, args.logN, args.logSlots)
    stats_aligned   = stats_by_bit_sdc(stats_gaps[stats_gaps["gap_class"] =="aligned"])
    stats_non_aligned = stats_by_bit_sdc(stats_gaps[stats_gaps["gap_class"] =="non_aligned"])

    plot_bit_cat(stats_aligned,     ax=ax[0], label_prefix="", color=c[1],  size=s)
    plot_bit_cat(stats_non_aligned, ax=ax[1], label_prefix="", color=c[1],  size=s)


    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()

if __name__ == "__main__":
    main()
