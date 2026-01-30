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
SAVENAME = "logQ"


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



def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title

    base_filters = build_filters(args)
    all_stats = {}
    for logQ in LOGQ_VALUES:
        filters = base_filters.copy()
        filters["library"]    =  ("str", BASELINE_LIBRARY)
        filters["stage"]      =  ("str", BASELINE_STAGE)
        filters["logN"]       =  ("int", BASELINE_LOGN)
        filters["logSlots"]   =  ("int", BASELINE_LOGSLOTS)
        filters["logQ"]       =  ("int", logQ)
        filters["logDelta"]   =  ("int", LOGDELTA_VALUES[logQ])
        filters["bitPerCoeff"]= ("int", BIT_PER_COEFF[logQ])

    ########################## DATA ################################
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

        if selected.empty:
            print(f"[WARN] No campaigns for logQ={logQ}")
            continue

        data = load_campaign_data(selected, config.DATA_DIR)
        if data.empty:
            print(f"[WARN] No bitflip data for logQ={logQ}")
            continue
    ########################## STATS ###############################
        stats = stats_by_bit(data)
        all_stats[logQ] = stats

    if not all_stats:
        raise RuntimeError("No data loaded for any logQ")

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))
    i = 0
    s = config.size
    for logQ, df in all_stats.items():
        df["bit"] = df["bit"]/logQ
        plot_bit(df, ax=ax, label_prefix=f"logQ={logQ}", color=c[i], size=s-i*20, alpha=alpha)
        i+=1

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()



if __name__ == "__main__":
    main()


