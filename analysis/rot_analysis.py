import matplotlib.pyplot as plt
import sys
import os
import copy

sys.path.append(os.path.abspath("./"))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.df_utils import split_by_gap, stats_by_bit
from utils.plotters import plot_bit

show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
SAVENAME = "rot"

c = [colors["red"], colors["blue"], colors["orange"], colors["green"], colors["green_light"], colors["green_dark"]]


def main():
    ########################## ARGS ################################
    base_args = parse_args()

    savename =  SAVENAME
    if base_args.title:
        savename = base_args.title


    rot_values= [
        base_args.doRot,
        base_args.doRot - 1,
        base_args.doRot - 2,
    ]
    fig, ax = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    i = 0
    s = config.size
    alpha = config.alpha

    for rot in rot_values:
        args = copy.deepcopy(base_args)
        args.doRot = rot

        filters = build_filters(args)
    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

        if selected.empty:
            print(f"[WARN] No campaigns for doRot = {rot}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        print(f"Loaded data shape: {data.shape}")

    ########################## STATS ###############################
        stats_gaps, gap   = split_by_gap(data, args.logN, args.logSlots)

        stats_aligned     = stats_by_bit(stats_gaps[stats_gaps["gap_class"] =="aligned"])
        stats_non_aligned = stats_by_bit(stats_gaps[stats_gaps["gap_class"] =="non_aligned"])

    ########################## PLOT ################################
        plot_bit(stats_aligned,     ax=ax[0], label_prefix="Rotations=", label=rot, color=c[i], size=s-i*20, alpha=alpha)
        plot_bit(stats_non_aligned, ax=ax[1], label_prefix="Rotations=", label=rot, color=c[i],  size=s-i*20, alpha=alpha)
        i+=1


    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
