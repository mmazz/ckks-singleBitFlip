import matplotlib.pyplot as plt
import copy
import sys
import os

from pathlib import Path
sys.path.append(os.path.abspath("./"))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.df_utils import split_by_gap,  stats_by_bit
from utils.plotters import plot_bit

show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
SAVENAME = "gap"

c = [colors["red"], colors["blue"], colors["orange"], colors["green"], colors["green"], colors["green"]]


    ########################## ARGS ################################
    ########################## DATA ################################
    ########################## STATS ###############################
    ########################## PLOT ################################

CSV_PATH = config.CAMPAIGNS_CSV
CSV_PATH=  "../results_multibit/campaigns_start.csv"
DATA_PATH = config.DATA_DIR
DATA_PATH = Path("../results_multibit/data")

def main():
    ########################## ARGS ################################
    base_args = parse_args()

    savename =  SAVENAME
    if base_args.title:
        savename = base_args.title

    logslots_values = [base_args.logSlots, base_args.logSlots - 2, base_args.logSlots - 4]

    fig, ax = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    i = 0
    s = config.size
    alpha = config.alpha
    for logSlot in logslots_values:
        args = copy.deepcopy(base_args)
        args.logSlots = logSlot

        filters = build_filters(args)
    ########################## DATA ################################
        selected = load_and_filter_campaigns(CSV_PATH , filters)
        if selected.empty:
            print(f"[WARN] No campaigns for logSlots = {logSlot}")
            continue

        data = load_campaign_data(selected, DATA_PATH)
        data["bit"] = data["bit"] +  3
    ########################## STATS ###############################
        stats_gaps, gap   = split_by_gap(data, args.logN, logSlot)
        stats_aligned     = stats_by_bit(stats_gaps[stats_gaps["gap_class"] =="aligned"])
        stats_non_aligned = stats_by_bit(stats_gaps[stats_gaps["gap_class"] =="non_aligned"])

    ########################## PLOT ################################
        plot_bit(stats_aligned,     ax=ax[0], label_prefix=f"logSlots={logSlot}", color=c[i], size=s-i*20, alpha=alpha)
        plot_bit(stats_non_aligned, ax=ax[1], label_prefix=f"logSlots={logSlot}", color=c[i],  size=s-i*20, alpha=alpha)
        i+=1



    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    plt.tight_layout()
    plt.gca()

    if show:
        plt.show()


if __name__ == "__main__":
    main()
