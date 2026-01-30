import matplotlib.pyplot as plt
import sys
import os
sys.path.append(os.path.abspath('./'))

from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.plotters import plot_bit_max_min
from utils.df_utils import stats_by_bit, filter_coeff_by_library

show = config.show
width = int(config.width)
s = config.size
colors = config.colors
dir = "img/"
SAVENAME = "encode"


def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title

    filters = build_filters(args)

    print("Filtros activos:", filters)

    ########################## DATA ################################
    selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)

    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data = load_campaign_data(selected, config.DATA_DIR)

    ########################## STATS ################################
    data_filter = filter_coeff_by_library(data, "heaan", args.logN)
    stats = stats_by_bit(data_filter)

    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))

    plot_bit_max_min(stats, ax=ax)
    plt.savefig(dir + f"{savename}.pdf", bbox_inches="tight")
    plt.savefig(dir + f"{savename}.png", bbox_inches="tight")
    if show:
        plt.show()

if __name__ == "__main__":
    main()

