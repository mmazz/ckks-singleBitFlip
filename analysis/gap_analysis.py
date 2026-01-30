import matplotlib.pyplot as plt
import copy
import sys
import os

sys.path.append(os.path.abspath("./"))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.df_utils import split_by_gap, stats_for_logslots_per_class, stats_by_bit_per_class
from utils.plotters import plot_bit_aligned_vs_nonaligned

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



def main():
    ########################## ARGS ################################
    base_args = parse_args()

    savename =  SAVENAME
    if base_args.title:
        savename = base_args.title

    logslots_values = [
        base_args.logSlots,
        base_args.logSlots - 1,
        base_args.logSlots - 2,
    ]

    results_aligned = {}
    results_non_aligned = {}

    for logSlot in logslots_values:
        args = copy.deepcopy(base_args)
        args.logSlots = logSlot

        filters = build_filters(args)
    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)
        if selected.empty:
            print(f"[WARN] No campaigns for logSlots = {logSlot}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)

    ########################## STATS ###############################
        stats_by_class, gap = stats_for_logslots_per_class(data, args.logN, logSlot)

        results_aligned[logSlot] = stats_by_class["aligned"]
        results_non_aligned[logSlot] = stats_by_class["non_aligned"]
    if not results_aligned:
        raise RuntimeError("No data loaded")

    ########################## PLOT ################################
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)

    plot_bit_aligned_vs_nonaligned(results_aligned, results_non_aligned, axes)

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
