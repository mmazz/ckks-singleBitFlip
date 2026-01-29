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
from utils.plotters import plot_bit
show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
savename = "encode"



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
    filters_heaan = build_filters(args)
    print("Filtros activos:", filters_heaan)

    filters_openfhe = filters_heaan.copy()
    filters_openfhe["library"] = ("str", "openfhe")
    filters_openfhe["bitPerCoeff"] = ("int", 64)
    selected_heaan = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_heaan)
    selected_openfhe = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_openfhe)

    if selected_openfhe.empty:
        raise RuntimeError("There is no campaigns with those filters")
    if selected_heaan.empty:
        raise RuntimeError("There is no campaigns with those filters")

    data_openfhe = load_campaign_data(selected_openfhe, config.DATA_DIR)
    data_heaan = load_campaign_data(selected_heaan, config.DATA_DIR)
    print(data_openfhe.head())
    print(data_heaan.head())
    openfhe = stats_by_bit_uniform_coeff(data_openfhe)
    heaan = stats_by_bit_uniform_coeff(data_heaan)
    print(openfhe)
    Q_openfhe = filters_openfhe["logQ"][1]
    Delta_openfhe = filters_openfhe["logDelta"][1]
    Q_HEAAN= 2*filters_heaan["logQ"][1]
    Delta_HEAAN =  filters_heaan["logDelta"][1] + filters_heaan["logQ"][1]

    fig, ax = plt.subplots(figsize=(12, 5))

    plot_bit(openfhe, Q_openfhe, Delta_openfhe, ax=ax, label_prefix=f"OpenFHE", color=colors["red"], scatter=True, ylabel="Normalize Bit index", size=80)
    plot_bit(heaan, Q_HEAAN, Delta_HEAAN, ax=ax, label_prefix=f"HEAAN", color=colors["blue"], scatter=True, ylabel="Normalize Bit index", size=50)
    ax.legend()
    plt.tight_layout()

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
