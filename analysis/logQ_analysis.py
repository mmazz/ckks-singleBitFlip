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

BASELINE_LOGN = 6
BASELINE_LOGSLOTS = 5
BASELINE_LIBRARY = "heaan"
BASELINE_STAGE = "encrypt_c0"
LOGQ_VALUES = [40, 60, 80, 100]
LOGDELTA_VALUES = {
        40:30,
        60:45,
        80:60,
        100:75
    }

BIT_PER_COEFF = {
    40: 50,
    60: 75,
    80: 100,
    100: 125,
}
def minmax_normalize_per_campaign(data):
    """
    Min-max normalize l2_norm to [0, 1] independently per campaign.
    """
    data = data.copy()

    grouped = data.groupby("campaign_id")["l2_norm"]

    min_val = grouped.transform("min")
    max_val = grouped.transform("max")

    denom = (max_val - min_val).replace(0, 1.0)

    data["l2_norm_norm"] = (data["l2_norm"] - min_val) / denom
    return data

def normalize_l2_per_campaign(data, method="p95"):
    """
    Normalize l2_norm independently per campaign.
    """
    data = data.copy()

    if method == "p95":
        scale = (
            data
            .groupby("campaign_id")["l2_norm"]
            .transform(lambda x: x.quantile(0.95))
        )

    elif method == "median":
        scale = (
            data
            .groupby("campaign_id")["l2_norm"]
            .transform("median")
        )

    else:
        raise ValueError(f"Unknown normalization method: {method}")

    data["l2_norm_norm"] = data["l2_norm"] / scale
    return data


def load_logq_campaigns(logQ):
    """
    Load campaigns for a fixed logQ configuration.
    """
    filters = {
        "library": ("str", BASELINE_LIBRARY),
        "stage": ("str", BASELINE_STAGE),
        "logN": ("int", BASELINE_LOGN),
        "logSlots": ("int", BASELINE_LOGSLOTS),
        "logQ": ("int", logQ),
        "logDelta": ("int", LOGDELTA_VALUES[logQ]),
        "bitPerCoeff": ("int", BIT_PER_COEFF[logQ]),
    }

    return load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

def stats_by_bit_uniform_coeff(data, drop_dc=True):
    """
    Aggregate L2 error statistics per bit, averaging uniformly over coefficients.
    """

    if drop_dc:
        data = data[data["coeff"] != 0]

    # 1) promedio por coeficiente (evita sesgo por multiplicidad)
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
    all_stats = {}

    for logQ in LOGQ_VALUES:
        filters = {
            "library": ("str", BASELINE_LIBRARY),
            "stage": ("str", BASELINE_STAGE),
            "logN": ("int", BASELINE_LOGN),
            "logSlots": ("int", BASELINE_LOGSLOTS),
            "logQ": ("int", logQ),
            "logDelta": ("int", LOGDELTA_VALUES[logQ]),
            "bitPerCoeff": ("int", BIT_PER_COEFF[logQ]),
        }

        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

        if selected.empty:
            print(f"[WARN] No campaigns for logQ={logQ}")
            continue

        print(f"[OK] logQ={logQ}, campaigns={len(selected)}")

        data = load_campaign_data(selected, config.DATA_DIR)
       # data = minmax_normalize_per_campaign(data)
        if data.empty:
            print(f"[WARN] No bitflip data for logQ={logQ}")
            continue
        stats = stats_by_bit_uniform_coeff(data)

        all_stats[logQ] = stats

    # ----------------------------
    # Plot
    # ----------------------------
    plt.figure(figsize=(8, 5))

    for logQ, df in all_stats.items():
        bit_idx = df["bit"].to_numpy()
        x_scaled = bit_idx / logQ
        y = df["mean_l2"].to_numpy()

        plt.plot(x_scaled, y, marker='o', label=f"logQ={logQ}")

    plt.axvline(1.0, linestyle="--",color="green", linewidth=2, label="logQ")
    plt.axvline(.74, linestyle="--",color="orange", linewidth=2, label="logDelta")
    plt.yscale("symlog")
    plt.ylim(0)
    plt.xlabel("Bit position / logQ")
    plt.ylabel("Mean L2 error")
    plt.legend()
    plt.grid(True)

    if config.show:
        plt.show()
    else:
        plt.savefig("logQ_scaled_analysis.pdf", bbox_inches="tight")


if __name__ == "__main__":
    main()


