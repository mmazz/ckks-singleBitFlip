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

def plot_l2_per_coeff_bit(
    df,
    coeff_col="coeff",
    bit_col="bit",
    value_col="l2_norm",
    title="L2 norm per (coeff, bit)",
):
    """
    Plot a value (default: l2_norm) ordered by (coeff, bit).

    X axis: coeff * bits_per_coeff + bit
    """

    bits_per_coeff = df[bit_col].max() + 1

    df_plot = df.copy()
    df_plot["x"] = df_plot[coeff_col] * bits_per_coeff + df_plot[bit_col]
    df_plot = df_plot.sort_values("x")

    plt.figure()
    plt.plot(df_plot["x"], df_plot[value_col])
    plt.xlabel("Coefficient-bit index")
    plt.ylabel(value_col)
    plt.yscale("symlog")
    plt.title(title)
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

    limb2= data[data["limb"]==2]
    plot_l2_per_coeff_bit(limb2)
    limb0= data[data["limb"]==0]
    plot_l2_per_coeff_bit(limb0)
if __name__ == "__main__":
    main()
