import numpy as np
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
import config

import matplotlib.pyplot as plt
from args import parse_args, build_filters
from  bitflip_utils import bits_to_flip_generator
from io_utils import load_campaign_data, load_and_filter_campaigns

show = config.show
width = int(config.width)

BASELINE_SMALL_LOGN = 6
BASELINE_SMALL_LOGSLOTS = 5

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

def prepare_stats(data, bit_list=None):
    df = stats_by_bit_uniform_coeff(data)

    # Si se pasa bit_list → filtrar y ordenar
    if bit_list is not None:
        bit_set = set(bit_list)
        df = df[df["bit"].isin(bit_set)].copy()

        df["bit"] = pd.Categorical(
            df["bit"],
            categories=bit_list,
            ordered=True
        )
        df = df.sort_values("bit")

    # Si bit_list es None → dejar todos los bits, orden natural
    return df
def main():
    args = parse_args()
    filters_large = build_filters(args)
    print("Filtros activos:", filters_large)

    filters_small = filters_large.copy()
    filters_small["logN"] = ("int", BASELINE_SMALL_LOGN)
    filters_small["logSlots"] = ("int", BASELINE_SMALL_LOGSLOTS)
    selected_large = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_large)
    selected_small = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_small)

    if selected_large.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")
    if selected_small.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data_large = load_campaign_data(selected_large, config.DATA_DIR)
    data_small = load_campaign_data(selected_small, config.DATA_DIR)
    print(data_large.head())
    print(data_small.head())

    random_bit_list = bits_to_flip_generator(
                       logQ=args.logQ,
                       logDelta=args.logDelta,
                       bit_per_coeff=args.bitPerCoeff
                    )
    df_large = prepare_stats(data_large, random_bit_list)
    df_small = prepare_stats(data_small)
    df_large = df_large.sort_values("bit")

    df_small = stats_by_bit_uniform_coeff(data_small)

    fig, ax = plt.subplots(figsize=(12, 5))

    plot_bit(df_small, ax=ax, label_prefix=f"logN={BASELINE_SMALL_LOGN} – ")
    plot_bit(df_large, ax=ax, label_prefix=f"logN={args.logN} – ", scatter=True)
    ax.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()


