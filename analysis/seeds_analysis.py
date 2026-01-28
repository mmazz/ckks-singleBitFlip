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
def stats_by_bit(data, logN):
    """
    Two-stage averaging:
    - mean over campaigns per (bit, coeff)
    - then statistics over coeffs per bit
    """
    N = 1 << logN
    target_coeff = N // 2
    # filtrar solo el coeficiente N/2
    data_mid = data[data["coeff"] != target_coeff]
    per_coeff = (
        data_mid
        .groupby(["bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )

    per_bit = (
        per_coeff
        .groupby("bit", as_index=False)
        .agg(
            mean_l2=("l2_mean", "mean"),
            std_l2=("l2_mean", lambda x: x.std(ddof=0)),
            min_l2=("l2_mean", "min"),
            max_l2=("l2_mean", "max"),
            n_coeff=("l2_mean", "count"),
        )
    )

    return per_bit


def plot_bit_stats(stats):
    x = stats["bit"]
    mean = stats["mean_l2"]
    std = stats["std_l2"]

    plt.figure(figsize=(12, 5))

    plt.plot(x, mean, linewidth=2, label="Mean $L_2$ error")

    plt.fill_between(
        x,
        mean - std,
        mean + std,
        alpha=0.3,
        label="±1 std"
    )

    plt.plot(x, stats["min_l2"], "--", linewidth=1, label="Min")
    plt.plot(x, stats["max_l2"], "--", linewidth=1, label="Max")

    plt.yscale("symlog")
    plt.xlabel("Bit index")
    plt.ylabel("$L_2$ error (symlog)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()




def debug_near_zero_bits(
    data,
    bit_min,
    bit_max,
    data_dir,
    id_width=6,
    eps=1e-12
):
    suspect = data[
        (data["bit"].between(bit_min, bit_max)) &
        (data["l2_norm"].abs() < eps)
    ]

    if suspect.empty:
        print(f"✔ No near-zero values in bits [{bit_min}, {bit_max}]")
        return

    print("⚠ NEAR-ZERO L2 DETECTED")
    print(
        suspect[["campaign_id", "bit", "coeff", "l2_norm"]]
        .sort_values(["campaign_id", "bit", "coeff"])
        .head(20)
    )

    # Campaigns involucradas
    campaign_ids = sorted(suspect["campaign_id"].unique())

    print("\n📁 CSVs involucrados:")
    for cid in campaign_ids:
        fname = f"campaign_{cid:0{id_width}d}.csv.gz"
        fpath = Path(data_dir) / fname
        print(f"  {cid} → {fpath}")

    # Resumen por bit
    summary = (
        suspect
        .groupby("bit")
        .agg(
            count=("l2_norm", "count"),
            campaigns=("campaign_id", "nunique")
        )
    )

    print("\n📊 Resumen por bit:")
    print(summary)

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

#    debug_near_zero_bits(
#        data,
#        bit_min=45,
#        bit_max=55,
#        data_dir=config.DATA_DIR,
#        id_width=6
#    )

    stats = stats_by_bit(data,args.logN)

    print("\n=== STATS POR BIT ===")
    print(stats)

    plot_bit_stats(stats)


if __name__ == "__main__":
    main()

