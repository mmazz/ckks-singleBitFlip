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


def plot_bit_stats(stats, logDelta, logQ, bitPerCoeff):
    # eje X uniforme (ordinal)
    x_pos = np.arange(len(stats))

    # labels simbólicos
    label_map = bit_labels(logDelta, logQ, bitPerCoeff)
    x_labels = [label_map.get(b, str(b)) for b in stats["bit"]]

    plt.figure(figsize=(12, 5))

    # media
    plt.plot(
        x_pos,
        stats["mean_l2"],
        marker="o",
        linewidth=2,
        label="Mean $L_2$"
    )

    # std
    plt.fill_between(
        x_pos,
        stats["mean_l2"] - stats["std_l2"],
        stats["mean_l2"] + stats["std_l2"],
        alpha=0.3,
        label="±1 std"
    )

    # min / max
    plt.plot(x_pos, stats["min_l2"], linestyle="--", marker="x", label="Min")
    plt.plot(x_pos, stats["max_l2"], linestyle="--", marker="^", label="Max")

    plt.yscale("symlog")
    plt.xlabel("Bit position (symbolic)")
    plt.ylabel(r"$L_2$ norm (symlog)")
    plt.grid(True)

    plt.xticks(x_pos, x_labels, rotation=30)

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
        df,
        logDelta=args.logDelta,
        logQ=args.logQ,
        bitPerCoeff=args.bitPerCoeff
    )



if __name__ == "__main__":
    main()

