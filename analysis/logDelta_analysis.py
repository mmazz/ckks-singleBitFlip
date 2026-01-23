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

BASELINE_LOGN = 3
BASELINE_LOGSLOTS = 2
BASELINE_LIBRARY = "heaan"
BASELINE_STAGE = "encrypt_c0"
LOGDELTA_VALUES = [20, 30, 40, 50]



def stats_by_bit_and_coeff_avg_campaigns(data: pd.DataFrame) -> pd.DataFrame:
    """
    Average only across campaigns.
    Keeps each coefficient separate.
    """
    return (
        data
        .groupby(["logDelta", "bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )


def plot_by_logdelta(stats: pd.DataFrame, logdeltas: list[int]):
    plt.figure(figsize=(14, 5))

    max_bit = stats["bit"].max()
    B = max_bit + 1

    for logDelta in logdeltas:
        sub = stats[stats["logDelta"] == logDelta].copy()

        # ordenar para que la concatenación sea correcta
        sub = sub.sort_values(["coeff", "bit"])

        # índice X concatenado
        sub["x"] = sub["coeff"] * B + sub["bit"]

        plt.plot(
            sub["x"],
            sub["l2_mean"],
            linewidth=1.5,
            label=f"logΔ = {logDelta}"
        )

    plt.yscale("symlog")
    plt.xlabel("Concatenated (coeff, bit) index")
    plt.ylabel("$L_2$ error")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def main():
    args = parse_args()
    base_filters = build_filters(args)

    logdeltas = LOGDELTA_VALUES

    all_stats = []
    for ld in logdeltas:
        filters = dict(base_filters)
        filters["logDelta"] = ("int", ld)

        selected = load_and_filter_campaigns(
            config.CAMPAIGNS_CSV, filters
        )
        if selected.empty:
            print(f"[WARN] No campaigns for logDelta={ld}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        data["logDelta"] = ld

        stats = stats_by_bit_and_coeff_avg_campaigns(data)
        all_stats.append(stats)

    if not all_stats:
        raise RuntimeError("No data loaded for any logDelta")

    stats = pd.concat(all_stats, ignore_index=True)
    plot_by_logdelta(stats, logdeltas)


if __name__ == "__main__":
    main()

