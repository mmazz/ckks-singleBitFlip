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
SAVENAME = "input"


BASELINE_LOGN = 6
BASELINE_LOGQ = 60
BASELINE_LOGDELTA = 20
BASELINE_LOGSLOTS = 5
BASELINE_LIBRARY = "heaan"
BASELINE_LIBRARY = "openfhe"

BASELINE_STAGE = "encrypt_c0"
LOGMIN_VALUES= [9, 19, 29, 39]
LOGMAX_VALUES = {
        9:10,
        19:20,
        29:30,
        39:40
    }

BIT_PER_COEFF = 64


def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title

    base_filters = build_filters(args)
    all_stats = {}
    for logMin in LOGMIN_VALUES:
        filters = base_filters.copy()
        filters["library"]    =  ("str", BASELINE_LIBRARY)
        filters["stage"]      =  ("str", BASELINE_STAGE)
        filters["logN"]       =  ("int", BASELINE_LOGN)
        filters["logSlots"]   =  ("int", BASELINE_LOGSLOTS)
        filters["logQ"]       =  ("int", BASELINE_LOGQ)
        filters["logDelta"]   =  ("int", BASELINE_LOGDELTA)
        filters["bitPerCoeff"]= ("int", BIT_PER_COEFF)
        filters["logMin"]= ("int", logMin)
        filters["logMax"]= ("int", LOGMAX_VALUES[logMin])

    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

        if selected.empty:
            print(f"[WARN] No campaigns for logMin={logMin} with logMax={LOGMAX_VALUES[logMin]}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        if data.empty:
            print(f"[WARN] No bitflip data for logMin={logMin} with logMax={LOGMAX_VALUES[logMin]}")
            continue
    ########################## STATS ###############################
        stats = stats_by_bit(data)
        all_stats[logMin] = stats

    if not all_stats:
        raise RuntimeError("No data loaded for any logMin/Max")

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))
    i = 0
    s = config.size
    for logMin, df in all_stats.items():
        plot_bit(df, ax=ax, label_prefix=f"logMin={logMin}", color=c[i], size=s-i*20, alpha=alpha, xlabel="Bit index")
        i+=1

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()



if __name__ == "__main__":
    main()


