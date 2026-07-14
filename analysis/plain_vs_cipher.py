import matplotlib.pyplot as plt
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.df_utils import stats_by_bit
from utils.plotters import plot_bit

show = config.show
width = int(config.width)
colors = config.colors
alpha = config.alpha
c = [colors["red"], colors["blue"], colors["green"], colors["orange"], colors["violet"]]
s = config.size

dir = "img/"
SAVENAME = "plain_vs_cipher"


BASELINE_LOGN = 6
BASELINE_LOGQ = 60
BASELINE_LOGSLOTS = 5
LIBRARY =  "openfhe"
LIBRARY =  "heaan"
STAGES = ["encode", "encrypt_c0", "encrypt_c1"]
BASELINE_LOGDELTA =  40
BASELINE_BITS = 64



def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title

    base_filters = build_filters(args)
    all_stats = {}
    for stage in STAGES:
        filters = base_filters.copy()
        filters["library"]    =  ("str", LIBRARY)
        filters["stage"]      =  ("str", stage)
        filters["logN"]       =  ("int", BASELINE_LOGN)
        filters["logSlots"]   =  ("int", BASELINE_LOGSLOTS)
        filters["logQ"]       =  ("int", BASELINE_LOGQ)
        filters["logDelta"]   =  ("int", BASELINE_LOGDELTA)
        filters["bitPerCoeff"]= ("int", BASELINE_BITS)

    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

        if selected.empty:
            print(f"[WARN] No campaigns for stage={stage}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        if data.empty:
            print(f"[WARN] No bitflip data for stafe={stage}")
            continue
    ########################## STATS ###############################
        stats = stats_by_bit(data)
        all_stats[stage] = stats

    if not all_stats:
        raise RuntimeError("No data loaded for any logQ")

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))
    i = 0
    s = config.size
    for stage, df in all_stats.items():
        if LIBRARY == "heaan":
            if stage == "encode":
                # Eliminar las filas con bit <= logQ
                df = df[df["bit"] > BASELINE_LOGQ].copy()
                df["bit"] = df["bit"] - BASELINE_LOGQ
        plot_bit(df, ax=ax, label_prefix=f"stage={stage}", color=c[i], size=s-i*20, alpha=alpha, plot_std=True)
        i+=1

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()



if __name__ == "__main__":
    main()


