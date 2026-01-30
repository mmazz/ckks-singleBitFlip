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
from utils.df_utils import split_by_gap, stats_for_logslots_per_class, stats_by_bit_per_class

show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
SAVENAME = "gap"

c = [colors["red"], colors["blue"], colors["orange"], colors["green"], colors["green"], colors["green"]]


def plot_bit_stats_aligned_vs_nonaligned(
    results_aligned,
    results_non_aligned
):
    fig, axes = plt.subplots(
        1, 2,
        figsize=(15, 5),
        sharey=True
    )

    panels = [
        ("Aligned coefficients\n(coeff % gap = 0)", results_aligned),
        ("Non-aligned coefficients\n(coeff % gap ≠ 0)", results_non_aligned),
    ]

    eps = 1e-18  # clamp mínimo para symlog
    count = 0
    for ax, (title, results) in zip(axes, panels):
        for logSlots, stats in sorted(results.items()):
            # asegurar orden por bit
            stats = stats.sort_values("bit")

            x = stats["bit"].to_numpy()
            y = stats["mean_l2"].to_numpy()

            ax.scatter(
                x, y,
                s=s,
                color=c[count],
                label=f"logSlots = {logSlots}"
            )
            count+=1

        ax.set_title(title)
        ax.set_xlabel("Bit index")
        ax.grid(True)

    axes[0].set_ylabel("$L_2$ error (symlog)")
    axes[0].set_yscale("symlog")
    axes[0].legend()

    plt.tight_layout()




def main():
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

    for ls in logslots_values:
        args = copy.deepcopy(base_args)
        args.logSlots = ls

        filters = build_filters(args)

        print(f"\n=== logSlots = {ls} ===")

        selected = load_and_filter_campaigns(
            config.CAMPAIGNS_CSV, filters
        )

        if selected.empty:
            print(f"[WARN] No campaigns for logSlots = {ls}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        print(f"Loaded data shape: {data.shape}")

        stats_by_class, gap = stats_for_logslots_per_class(
            data, args.logN, ls
        )

        print(f"gap = {gap}")

        results_aligned[ls] = stats_by_class["aligned"]
        results_non_aligned[ls] = stats_by_class["non_aligned"]
    if not results_aligned:
        raise RuntimeError("No data loaded")

    plot_bit_stats_aligned_vs_nonaligned(
        results_aligned,
        results_non_aligned
    )

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
