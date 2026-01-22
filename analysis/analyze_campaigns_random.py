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


def l2_norm_by_bit(mean_data):
    norm2 = (
        mean_data
        .groupby("bit")
        .apply(lambda g: np.linalg.norm(g["mean_l2"].values, ord=2))
        .reset_index(name="l2_norm")
    )
    return norm2



def plot_bit_stats(stats):
    x = stats["bit"].to_numpy()
    mean = stats["mean_l2"].to_numpy()
    std = stats["std_l2"].to_numpy()
    ymin = stats["min_l2"].to_numpy()
    ymax = stats["max_l2"].to_numpy()

    upper = mean + std
    lower = mean                      # std solo hacia arriba
    lower = np.maximum(lower, 1e-12)  # evita tocar 0 en symlog

    plt.figure(figsize=(12, 5))

    # media
    plt.plot(
        x, mean,
        linewidth=2,
        marker="o",
        markersize=6,
        label="Mean $L_2$"
    )

    # std (solo positivo, sin cruzar cero)
    lower = np.maximum(mean - std, 0)
    upper = mean + std

    plt.fill_between(
        x,
        lower,
        upper,
        alpha=0.3,
        label="±1 std"
    )

    # min / max
    plt.plot(x, ymin, linestyle="--", marker="x", label="Min")
    plt.plot(x, ymax, linestyle="--", marker="^", label="Max")

    plt.yscale("symlog", linthresh=1e-10)
    plt.xlabel("Bit index")
    plt.ylabel("$L_2$ norm (symlog)")
    plt.grid(True, which="both")
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
    df = stats_by_bit_uniform_coeff(data)
    orden_bits = bits_to_flip_generator(
        logQ=args.logQ,
        logDelta=args.logDelta,
        bit_per_coeff=args.bitPerCoeff
    )

    df = stats_by_bit_uniform_coeff(data)

    df = df[df["bit"].isin(set(orden_bits))].copy()

    df["bit"] = pd.Categorical(
        df["bit"],
        categories=orden_bits,
        ordered=True
    )

    df = df.sort_values("bit")

    plot_bit_stats(
        df
    )



if __name__ == "__main__":
    main()

