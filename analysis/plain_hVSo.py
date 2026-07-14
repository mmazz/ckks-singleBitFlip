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
SAVENAME = "plain_hean_VS_openfhe"


BASELINE_LOGN = 6
BASELINE_LOGQ = 60
BASELINE_LOGSLOTS = 5
LIBRARYS = { 128: "heaan", 64: "openfhe"}
BASELINE_STAGE = "encode"
BASELINE_LOGDELTA =  40

BIT_PER_COEFF = [ 128, 64]


def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title

    base_filters = build_filters(args)
    all_stats = {}
    for bit_per_coeff in BIT_PER_COEFF:
        filters = base_filters.copy()
        filters["library"]    =  ("str", LIBRARYS[bit_per_coeff])
        filters["stage"]      =  ("str", BASELINE_STAGE)
        filters["logN"]       =  ("int", BASELINE_LOGN)
        filters["logSlots"]   =  ("int", BASELINE_LOGSLOTS)
        filters["logQ"]       =  ("int", BASELINE_LOGQ)
        filters["logDelta"]   =  ("int", BASELINE_LOGDELTA)
        filters["bitPerCoeff"]= ("int", bit_per_coeff)

    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

        if selected.empty:
            print(f"[WARN] No campaigns for bit_per_coeff={bit_per_coeff}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        if data.empty:
            print(f"[WARN] No bitflip data for bit_per_coeff={bit_per_coeff}")
            continue
    ########################## STATS ###############################
        stats = stats_by_bit(data)
        all_stats[bit_per_coeff] = stats

    if not all_stats:
        raise RuntimeError("No data loaded for any logQ")

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))
    i = 0
    s = config.size
    for bit_per_coeff, df in all_stats.items():
        if LIBRARYS[bit_per_coeff] == "heaan":
            # Eliminar las filas con bit <= logQ
            df = df[df["bit"] > BASELINE_LOGQ].copy()
            df["bit"] = df["bit"] - BASELINE_LOGQ
        plot_bit(df, ax=ax, label_prefix=f"library={LIBRARYS[bit_per_coeff]}", color=c[i], size=s-i*20, alpha=alpha)
        i+=1

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()



if __name__ == "__main__":
    main()


