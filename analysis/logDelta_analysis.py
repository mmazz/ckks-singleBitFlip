import numpy as np
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config

import matplotlib.pyplot as plt
from utils.args import parse_args, build_filters
from  utils.bitflip_utils import bits_to_flip_generator
from utils.io_utils import load_campaign_data, load_and_filter_campaigns

show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
savename = "logDelta"



BASELINE_LOGN = 3
BASELINE_LOGSLOTS = 2
BASELINE_LIBRARY = "heaan"
BASELINE_STAGE = "encrypt_c0"
LOGDELTA_VALUES = [25, 35, 45, 55]





def stats_by_bit_per_coeff(data_avg: pd.DataFrame) -> pd.DataFrame:
    return (
        data_avg
        .groupby(["logDelta", "bit"], as_index=False)
        .agg(
            mean_l2=("l2_mean", "mean"),
            std_l2=("l2_mean", lambda x: x.std(ddof=0)),
            min_l2=("l2_mean", "min"),
            max_l2=("l2_mean", "max"),
            n_coeff=("l2_mean", "count"),
        )
    )

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
        sub = sub.sort_values("bit")

        # índice X concatenado
        #sub["x"] = sub["coeff"] * B + sub["bit"]

        plt.scatter(
            sub["bit"],
            sub["mean_l2"],
            s=s,
            label=f"logΔ = {logDelta}"
        )

    plt.yscale("symlog")
    plt.xlabel("Bit index")
    plt.ylabel("$L_2$ norm (symlog)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

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
        # 1️⃣ promedio sobre campañas (crea l2_mean)
        data_avg = stats_by_bit_and_coeff_avg_campaigns(data)

        # 2️⃣ estadística entre coeficientes
        stats = stats_by_bit_per_coeff(data_avg)

        all_stats.append(stats)

    if not all_stats:
        raise RuntimeError("No data loaded for any logDelta")

    stats = pd.concat(all_stats, ignore_index=True)
    plot_by_logdelta(stats, logdeltas)
    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()


