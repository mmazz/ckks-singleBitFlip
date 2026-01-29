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
from utils.plotters import plot_bits
show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
savename = "encrypt"

def shift_bits(df, offset):
    df = df.copy()
    df["bit"] = df["bit"] + offset
    return df

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

def main():
    args = parse_args()
    filters_c0 = build_filters(args)
    print("Filtros activos:", filters_c0)

    filters_c1 = filters_c0.copy()
    filters_c1["stage"] = ("str", "encrypt_c1")
    selected_c0 = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_c0)
    selected_c1 = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_c1)

    if selected_c1.empty:
        raise RuntimeError("There is no campaigns with those filters")
    if selected_c0.empty:
        raise RuntimeError("There is no campaigns with those filters")

    data_c0 = load_campaign_data(selected_c0, config.DATA_DIR)
    data_c1 = load_campaign_data(selected_c1, config.DATA_DIR)
    print(data_c0.head())
    print(data_c1.head())
    c0 = data_c0.copy()
    c0["bit"] = c0["coeff"] * args.bitPerCoeff + c0["bit"]
    c1 = data_c1.copy()
    c1["bit"] = c1["coeff"] * args.bitPerCoeff + c1["bit"]


    fig, ax = plt.subplots(figsize=(12, 5))

    offset = c0["bit"].max() + 1
    c1_shifted = shift_bits(c1, offset)

    plot_bits(c0, ax=ax, label_prefix=f"C0", color=colors["blue"], scatter=True)
    plot_bits(c1_shifted, ax=ax, label_prefix=f"C1", color=colors["red"], scatter=True)
    ax.legend()
    plt.tight_layout()

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
