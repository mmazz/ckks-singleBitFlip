import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.plotters import plot_bit
from utils.df_utils import shift_bits

show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
SAVENAME = "encrypt"
def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title
    filters_c0 = build_filters(args)
    print("Filtros activos:", filters_c0)

    filters_c1 = filters_c0.copy()
    filters_c1["stage"] = ("str", "encrypt_c1")

    ########################## DATA ################################
    selected_c0 = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_c0)
    selected_c1 = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_c1)

    if selected_c1.empty:
        raise RuntimeError("There is no campaigns with those filters")
    if selected_c0.empty:
        raise RuntimeError("There is no campaigns with those filters")

    data_c0 = load_campaign_data(selected_c0, config.DATA_DIR)
    data_c1 = load_campaign_data(selected_c1, config.DATA_DIR)

    ########################## STATS ###############################
    c0 = data_c0.copy()
    c0["bit"] = c0["coeff"] * args.bitPerCoeff + c0["bit"]
    c1 = data_c1.copy()
    c1["bit"] = c1["coeff"] * args.bitPerCoeff + c1["bit"]


    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))

    offset = c0["bit"].max() + 1
    c1_shifted = shift_bits(c1, offset)
    c0 = c0.rename(columns={"l2_norm": "mean_l2"})
    c1 = c1_shifted.rename(columns={"l2_norm": "mean_l2"})
    plot_bit(c0, ax=ax, label_prefix=f"C0", color=colors["blue"], plot_std=False, label="" )
    plot_bit(c1, ax=ax, label_prefix=f"C1", color=colors["red"], plot_std=False, label="")

    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
