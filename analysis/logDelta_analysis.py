import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.plotters import plot_bit
from utils.df_utils import stats_by_bit

show = config.show
width = int(config.width)
colors = config.colors

c = [colors["red"], colors["blue"], colors["green"], colors["orange"], colors["violet"]]
alpha=config.alpha

dir = "img/"
SAVENAME = "logDelta"



BASELINE_LOGN = 3
BASELINE_LOGSLOTS = 2
BASELINE_LIBRARY = "heaan"
BASELINE_STAGE = "encrypt_c0"
LOGDELTA_VALUES = [25, 35, 45, 55]




def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title
    base_filters = build_filters(args)

    all_stats = {}
    for logDelta in LOGDELTA_VALUES:
        filters = base_filters.copy()
        filters["logDelta"] = ("int", logDelta)

    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)
        if selected.empty:
            print(f"[WARN] No campaigns for logDelta={logDelta}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        if data.empty:
            print(f"[WARN] No bitflip data for logDelta={logDelta}")
            continue
    ########################## STATS ###############################
        stats = stats_by_bit(data)
        all_stats[logDelta] = stats

    if not all_stats:
        raise RuntimeError("No data loaded for any logDelta")

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))
    i = 0
    s = config.size
    for logQ, df in all_stats.items():
        plot_bit(df, ax=ax, label_prefix=f"logQ={logQ}", color=c[i], size=s-i*20, alpha=alpha)
        i+=1

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()


