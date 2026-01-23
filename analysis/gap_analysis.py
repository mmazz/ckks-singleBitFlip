import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy

sys.path.append(os.path.abspath("./"))
import config

from args import parse_args, build_filters
from io_utils import load_campaign_data, load_and_filter_campaigns


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

    for ax, (title, results) in zip(axes, panels):
        for logSlots, stats in sorted(results.items()):
            # asegurar orden por bit
            stats = stats.sort_values("bit")

            x = stats["bit"].to_numpy()
            y = stats["mean_l2"].to_numpy()
            std = stats["std_l2"].to_numpy()

            ax.plot(
                x, y,
                linewidth=2,
                label=f"logSlots = {logSlots}"
            )

            lower = np.maximum(y - std, eps)
            upper = y + std

            ax.fill_between(
                x,
                lower,
                upper,
                alpha=0.25
            )

        ax.set_title(title)
        ax.set_xlabel("Bit index")
        ax.grid(True)

    axes[0].set_ylabel("$L_2$ error (symlog)")
    axes[0].set_yscale("symlog")
    axes[0].legend()

    plt.tight_layout()
    plt.show()


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
if __name__ == "__main__":
    main()
