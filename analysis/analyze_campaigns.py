import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
import config

import matplotlib.pyplot as plt
from utils_parser import parse_args, build_filters
from campaigns_filter import load_campaign_data, load_and_filter_campaigns,CAMPAIGNS_CSV, DATA_DIR

show = config.show
width = int(config.width)

def stats_by_bit_uniform_coeff(data):
    # 1) promedio por coeficiente
    per_coeff = (
        data
        .groupby(["bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )

    # 2) estadística por bit
    per_bit = (
        per_coeff
        .groupby("bit", as_index=False)
        .agg(
            mean_l2=("l2_mean", "mean"),
            std_l2=("l2_mean", lambda x: x.std(ddof=0)),
            min_l2=("l2_mean", "min"),
            max_l2=("l2_mean", "max"),
            count=("l2_mean", "count"),
        )
    )
    return per_bit

def mean_by_coeff_and_bit(data):
    print("coeff únicos en data:", data["coeff"].nunique())
    print("min/max coeff:", data["coeff"].min(), data["coeff"].max())
    mean_data = (
        data
        .groupby(["coeff", "bit"], as_index=False)
        .agg(mean_l2=("l2_norm", "mean"))
    )
    print("coeff únicos en mean_data:", mean_data["coeff"].nunique())
    return mean_data

def mean_by_bit(data):
    mean_data = (
        data
        .groupby(["bit"], as_index=False)
        .agg(mean_l2=("l2_norm", "mean"))
    )
    print("bits únicos en mean_data:", mean_data["bit"].nunique())
    return mean_data

def mean_std_by_bit(data):
    stats = (
        data
        .groupby("bit", as_index=False)
        .agg(
            mean_l2=("l2_norm", "mean"),
            std_l2=("l2_norm", "std"),
            count=("l2_norm", "count"),
        )
    )
    return stats

def l2_norm_by_bit(mean_data):
    norm2 = (
        mean_data
        .groupby("bit")
        .apply(lambda g: np.linalg.norm(g["mean_l2"].values, ord=2))
        .reset_index(name="l2_norm")
    )
    return norm2


# ============================================================
# 5. PLOT
# ============================================================

def plot_l2(norm2_by_bit):
    plt.figure(figsize=(8, 5))
    plt.plot(norm2_by_bit["bit"], norm2_by_bit["l2_norm"], marker="o")
    plt.xlabel("Bit")
    plt.ylabel("Norma L2 del error promedio")
    plt.title("Norma L2 por bit (promediado sobre campañas)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_per_coefficient(mean_data, max_coeff=None):
    plt.figure(figsize=(10, 6))

    for coeff, g in mean_data.groupby("coeff"):
        if max_coeff is not None and coeff >= max_coeff:
            continue

        g = g.sort_values("bit")
        plt.plot(
            g["bit"],
            g["mean_l2"],
            alpha=0.4,
            linewidth=1
        )

    plt.xlabel("Bit")
    plt.ylabel("Mean L2 norm (avg over campaigns)")
    plt.title("Error per bit, one curve per coefficient")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_concatenated_coeffs(mean_data, bits_per_coeff=64):
    """
    Eje X: coeff * bits_per_coeff + bit
    Eje Y: mean_l2
    """

    # Construir eje X global
    x = mean_data["coeff"] * bits_per_coeff + mean_data["bit"]
    y = mean_data["mean_l2"]

    # Ordenar por eje X (importante)
    order = np.argsort(x)
    x = x.iloc[order]
    y = y.iloc[order]

    plt.figure(figsize=(12, 5))
    plt.plot(x, y, linewidth=width, color=config.colors["blue"])
    for i in mean_data.groupby("coeff"):
        plt.axvline(64*i, linestyle='--')
    plt.yscale('symlog')
    plt.ylabel('$L_2$ norm (Symlog scale)')
    plt.xlabel('Modified Bit Index')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_bit_stats(stats):
    x = stats["bit"]
    mean = stats["mean_l2"]
    std = stats["std_l2"]
    ymin = stats["min_l2"]
    ymax = stats["max_l2"]

    plt.figure(figsize=(12, 5))

    # media
    plt.plot(x, mean, linewidth=2, label="Mean $L_2$")

    # std
    plt.fill_between(
        x,
        mean - std,
        mean + std,
        alpha=0.3,
        label="±1 std"
    )

    # min / max
    plt.plot(x, ymin, linestyle="--", linewidth=1, label="Min")
    plt.plot(x, ymax, linestyle="--", linewidth=1, label="Max")

    plt.yscale("symlog")
    plt.xlabel("Bit index")
    plt.ylabel("$L_2$ norm (symlog)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

def main():
    args = parse_args()
    filters = build_filters(args)

    print("Filtros activos:", filters)

    selected = load_and_filter_campaigns(CAMPAIGNS_CSV, filters)

    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data = load_campaign_data(selected, DATA_DIR)
    mean_data = stats_by_bit_uniform_coeff(data)
    #mean_data = mean_by_coeff_and_bit(data)
    print(mean_data)

    norm2 = l2_norm_by_bit(mean_data)

    print("\n=== NORMA L2 POR BIT ===")
    print(norm2)
    print(args.bitPerCoeff)
    plot_bit_stats(mean_data)
    #plot_concatenated_coeffs(mean_data, args.bitPerCoeff)


if __name__ == "__main__":
    main()

