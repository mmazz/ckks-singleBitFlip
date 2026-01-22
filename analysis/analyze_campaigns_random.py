import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
import config

import matplotlib.pyplot as plt
from utils_parser import parse_args, build_filters, bits_to_flip_generator
from campaigns_filter import load_campaign_data, load_and_filter_campaigns,CAMPAIGNS_CSV, DATA_DIR

show = config.show
width = int(config.width)


logN = 6


def bit_labels(logDelta, logQ, bitPerCoeff):
    M = bitPerCoeff - 1

    return {
        0: "0",
        logDelta // 4: r"$\Delta/4$",
        logDelta // 2: r"$\Delta/2$",
        logDelta - 1: r"$\Delta - 1$",
        logDelta: r"$\Delta$",
        (logDelta + logQ) // 2: r"$(\Delta + Q)/2$",
        logQ - 1: r"$Q - 1$",
        logQ: r"$Q$",
        (logQ + M) // 2: r"$(Q + M)/2$",
        M: r"$M$",
    }

def bit_region(bit, logDelta, logQ, M):
    if bit <= logDelta // 4:
        return "A"   # ruido
    if bit <= logDelta:
        return "B"   # transición
    if bit <= (logDelta + logQ) // 2:
        return "C"   # mensaje
    if bit <= logQ:
        return "D"   # borde módulo
    return "E"       # overflow

def stats_by_bit_uniform_coeff_split(data, args, drop_dc=True):
    """
    Calcula estadísticas por bit separando coeficientes en dos grupos:
      - Grupo A: coeff % gap == 0
      - Grupo B: resto

    Devuelve:
      stats_A, stats_B
    """
    gap = (1 << (args.logN - 1)) // (1 << args.logSlots)
    print(f"gap is {gap}")
    # -------- filtrado base --------
    if drop_dc:
        data = data[data["coeff"] != 0]

    # -------- promedio por (bit, coeff) --------
    per_coeff = (
        data
        .groupby(["bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )

    # -------- split por gap --------
    group_A = per_coeff[per_coeff["coeff"] % gap == 0]
    group_B = per_coeff[per_coeff["coeff"] % gap != 0]

    def agg_per_bit(df):
        if df.empty:
            return pd.DataFrame(
                columns=["bit", "mean_l2", "std_l2", "min_l2", "max_l2", "count"]
            )

        return (
            df
            .groupby("bit", as_index=False)
            .agg(
                mean_l2=("l2_mean", "mean"),
                std_l2=("l2_mean", lambda x: x.std(ddof=0)),
                min_l2=("l2_mean", "min"),
                max_l2=("l2_mean", "max"),
                count=("l2_mean", "count"),
            )
        )

    stats_A = agg_per_bit(group_A)
    stats_B = agg_per_bit(group_B)

    return stats_A, stats_B

def stats_by_bit_uniform_coeff(data, drop_dc=True):
    if drop_dc:
        data = data[data["coeff"] != 0]
    data = data[data["coeff"] != 0]
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


def l2_norm_by_bit(mean_data):
    norm2 = (
        mean_data
        .groupby("bit")
        .apply(lambda g: np.linalg.norm(g["mean_l2"].values, ord=2))
        .reset_index(name="l2_norm")
    )
    return norm2

def plot_bit_stats(stats, ax=None, label_prefix="", scatter=False):
    if ax is None:
        ax = plt.gca()

    x = stats["bit"].to_numpy()
    mean = stats["mean_l2"].to_numpy()
    std = stats["std_l2"].to_numpy()
    ymin = stats["min_l2"].to_numpy()
    ymax = stats["max_l2"].to_numpy()

    # media

    if not scatter:
        ax.plot(
                x, mean,
                linewidth=2,
                marker="o",
                markersize=6,
                label=f"{label_prefix}Mean $L_2$"
                )
        lower = np.maximum(mean - std, 0)
        upper = mean + std

        ax.fill_between(
            x,
            lower,
            upper,
            alpha=0.25,
            label=f"{label_prefix}±1 std"
        )

    # min / max
    if scatter:
        ax.scatter(x, ymin, label=f"{label_prefix}Min")
        ax.scatter(x, ymax, label=f"{label_prefix}Max")
    else:
        ax.plot(x, ymax, linestyle="--", marker="^", label=f"{label_prefix}Max")
        ax.plot(x, ymin, linestyle="--", marker="x", label=f"{label_prefix}Min")

    ax.set_yscale("symlog")
    ax.set_xlabel("Bit index")
    ax.set_ylabel("$L_2$ norm (symlog)")
    ax.grid(True, which="both")

def plot_bit(stats, ax=None, label_prefix="", scatter=False):
    if ax is None:
        ax = plt.gca()

    x = stats["bit"].to_numpy()
    mean = stats["mean_l2"].to_numpy()

    if scatter:
        ax.scatter(
            x,
            mean, color=config.colors["red"],
            s=80,                # 👈 tamaño del punto
            zorder=4,            # 👈 arriba del plot
            label=f"{label_prefix}Mean $L_2$"
        )
    else:
        ax.plot(
            x,
            mean,
            linewidth=2,
            marker="o",
            markersize=6,
            zorder=2,            # 👈 abajo del scatter
            label=f"{label_prefix}Mean $L_2$"
        )

    ax.set_yscale("symlog")
    ax.set_xlabel("Bit index")
    ax.set_ylabel("$L_2$ norm (symlog)")
    ax.grid(True, which="both")

def main():
    args = parse_args()
    filters = build_filters(args)
    print("Filtros activos:", filters)

    selected = load_and_filter_campaigns(CAMPAIGNS_CSV, filters)
    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")
    data = load_campaign_data(selected, DATA_DIR)
#    args.logN = logN
#    args.logSlots = logN-1
#    filters_comparison = build_filters(args)
#
#    selected_comparison = load_and_filter_campaigns(CAMPAIGNS_CSV, filters_comparison)
#
#    if selected_comparison.empty:
#        raise RuntimeError("No hay campañas que cumplan los filtros")

 #   data_comparison = load_campaign_data(selected_comparison, DATA_DIR)
 #   print(data.head)
 #   print(data_comparison.head)
 #   df_comparison = stats_by_bit_uniform_coeff(data_comparison)
 #   orden_bits = bits_to_flip_generator(
 #       logQ=args.logQ,
 #       logDelta=args.logDelta,
 #       bit_per_coeff=args.bitPerCoeff
 #   )

 #   df = stats_by_bit_uniform_coeff(data)

 #   df = df[df["bit"].isin(set(orden_bits))].copy()

 #   df["bit"] = pd.Categorical(
 #       df["bit"],
 #       categories=orden_bits,
 #       ordered=True
 #   )

 #   df = df.sort_values("bit")
    fig, ax = plt.subplots(figsize=(12, 5))

 #   plot_bit(df_comparison, ax=ax, label_prefix="logN=6 – ")
 #   plot_bit(df, ax=ax, label_prefix="logN=16 – ", scatter=True)
    stats_A, stats_B = stats_by_bit_uniform_coeff_split(
        data,
        args,
        drop_dc=True
    )

    print(stats_A)
    print(stats_B)

    plot_bit(stats_A,ax=ax)
    plot_bit(stats_B,ax=ax)

    ax.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()

