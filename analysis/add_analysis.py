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
show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"

c = [colors["red"], colors["blue"], colors["orange"], colors["green"], colors["green"], colors["green"]]


def split_by_gap(data, logN, logSlots):
    """
    - remove central coefficient N/2
    - classify coefficients by gap alignment
    """
    N = 1 << logN
    target_coeff = N // 2

    data = data[data["coeff"] != target_coeff].copy()

    gap = (1 << (logN - 1)) // (1 << logSlots)

    data["gap_class"] = np.where(
        data["coeff"] % gap == 0,
        "aligned",
        "non_aligned"
    )

    return data, gap

def plot_bit_stats_aligned_vs_nonaligned(
    results_aligned: pd.DataFrame,
    results_non_aligned: pd.DataFrame,
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

    for ax, (title, stats) in zip(axes, panels):
        # asegurar orden por bit
        stats = stats.sort_values("bit")

        x = stats["bit"].to_numpy()
        y = stats["mean_l2"].to_numpy()

        ax.scatter(
            x,
            y,
            s=s,
        )

        ax.set_title(title)
        ax.set_xlabel("Bit index")
        ax.grid(True)

    axes[0].set_ylabel("$L_2$ error (symlog)")
    axes[0].set_yscale("symlog")

    plt.tight_layout()



def stats_by_bit_per_class(data):
    """
    Two-stage averaging:
    - mean over campaigns per (gap_class, bit, coeff)
    - stats over coefficients per bit
    """

    per_coeff = (
        data
        .groupby(["gap_class", "bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )

    per_bit = (
        per_coeff
        .groupby(["gap_class", "bit"], as_index=False)
        .agg(
            mean_l2=("l2_mean", "mean"),
            std_l2=("l2_mean", lambda x: x.std(ddof=0)),
            min_l2=("l2_mean", "min"),
            max_l2=("l2_mean", "max"),
            n_coeff=("l2_mean", "count"),
        )
    )
    return per_bit

def stats_for_logslots_per_class(data, logN, logSlots):
    data, gap = split_by_gap(data, logN, logSlots)
    stats = stats_by_bit_per_class(data)

    out = {}

    for cls in ["aligned", "non_aligned"]:
        s = stats[stats["gap_class"] == cls]

        out[cls] = s[["bit", "mean_l2", "std_l2"]]

    return out, gap



def main():
    base_args = parse_args()

    args = copy.deepcopy(base_args)

    filters = build_filters(args)

    savename = args.title
    selected = load_and_filter_campaigns(
        config.CAMPAIGNS_CSV, filters
    )

    if selected.empty:
        print(f"[WARN] No campaigns for doMul")

    data = load_campaign_data(selected, config.DATA_DIR)
    print(f"Loaded data shape: {data.shape}")

    stats_by_class, gap = stats_for_logslots_per_class(
        data, args.logN, args.logSlots
    )

    print(f"gap = {gap}")

    results_aligned = stats_by_class["aligned"]
    results_non_aligned = stats_by_class["non_aligned"]
    print(results_aligned)

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
