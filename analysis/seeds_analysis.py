import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config

import matplotlib.pyplot as plt
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns

show = config.show
width = int(config.width)
s = config.size
colors = config.colors
dir = "img/"
savename = "seeds"

def stats_by_bit(data, logN):
    N = 1 << logN
    target_coeff = N // 2

    # opcional: excluir coeficiente central
    data_mid = data[data["coeff"] != target_coeff]

    # (1) extremos globales reales por bit
    extrema = (
        data_mid
        .groupby("bit", as_index=False)
        .agg(
            min_l2=("l2_norm", "min"),
            max_l2=("l2_norm", "max"),
        )
    )

    # (2) promedio por coeficiente (colapsa campañas)
    per_coeff = (
        data_mid
        .groupby(["bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )

    # (3) stats entre coeficientes por bit
    stats = (
        per_coeff
        .groupby("bit", as_index=False)
        .agg(
            mean_l2=("l2_mean", "mean"),
            std_l2=("l2_mean", lambda x: x.std(ddof=0)),
            n_coeff=("l2_mean", "count"),
        )
    )

    # (4) juntar todo
    return stats.merge(extrema, on="bit")

def plot_bit_stats(stats):
    x = stats["bit"]
    mean = stats["mean_l2"]
    std = stats["std_l2"]

    plt.figure(figsize=(12, 5))

    plt.scatter(
        x, mean,
        s=s,
        label="Mean $L_2$ error",
        zorder=2
    )

    plt.fill_between(
        x,
        mean - std,
        mean + std,
        alpha=0.3,
        label="±1 std",
        zorder=1
    )

    plt.scatter(x, stats["min_l2"], s=s, marker="_", color = colors["red"], label="Global Min", zorder=3)
    plt.scatter(x, stats["max_l2"], s=s, marker="+", color = colors["green"], label="Global Max", zorder=3)

    plt.yscale("symlog")
    plt.xlabel("Bit index")
    plt.ylabel("$L_2$ error (symlog)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(dir + f"{savename}.pdf", bbox_inches="tight")
    plt.savefig(dir + f"{savename}.png", bbox_inches="tight")
    if show:
        plt.show()


def main():
    args = parse_args()
    filters = build_filters(args)

    print("Filtros activos:", filters)

    selected = load_and_filter_campaigns(
        config.CAMPAIGNS_CSV, filters
    )

    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data = load_campaign_data(selected, config.DATA_DIR)
    stats = stats_by_bit(data,args.logN)

    print("\n=== STATS POR BIT ===")
    print(stats)

    plot_bit_stats(stats)


if __name__ == "__main__":
    main()

