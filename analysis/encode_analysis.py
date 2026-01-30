import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from utils.plotters import plot_bit
from utils.df_utils import filter_coeff_by_library, stats_by_bit, normalizer

show = config.show
width = int(config.width)
colors = config.colors
s = config.size

dir = "img/"
SAVENAME = "encode"


def main():
    ########################## ARGS ################################
    args = parse_args()
    savename =  SAVENAME
    if args.title:
        savename = args.title

    filters_heaan = build_filters(args)
    print("Filtros activos:", filters_heaan)

    filters_openfhe = filters_heaan.copy()
    filters_openfhe["library"] = ("str", "openfhe")
    filters_openfhe["bitPerCoeff"] = ("int", 64)

    ########################## DATA ################################
    selected_heaan   = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_heaan)
    selected_openfhe = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters_openfhe)

    if selected_openfhe.empty:
        raise RuntimeError("There is no campaigns with those filters")
    if selected_heaan.empty:
        raise RuntimeError("There is no campaigns with those filters")

    data_openfhe = load_campaign_data(selected_openfhe, config.DATA_DIR)
    data_heaan   = load_campaign_data(selected_heaan, config.DATA_DIR)

    ########################## STATS ################################
    openfhe_filter      = filter_coeff_by_library(data_openfhe, "openfhe", args.logN)
    heaan_filter        = filter_coeff_by_library(data_heaan, "heaan", args.logN)
    openfhe      = stats_by_bit(openfhe_filter)
    heaan        = stats_by_bit(heaan_filter)

    Q_openfhe     = filters_openfhe["logQ"][1]
    Delta_openfhe = filters_openfhe["logDelta"][1]
    Q_HEAAN       = 2*filters_heaan["logQ"][1]
    Delta_HEAAN   = filters_heaan["logDelta"][1] + filters_heaan["logQ"][1]

    openfhe_norm = normalizer(openfhe, Q_openfhe, Delta_openfhe)
    heaan_norm   = normalizer(heaan,   Q_HEAAN,   Delta_HEAAN)
    ########################## PLOT ################################
    fig, ax = plt.subplots(figsize=(12, 5))

    plot_bit(openfhe_norm, ax=ax, label_prefix="OpenFHE", color=colors["red"],  scatter=True, xlabel="Normalize Bit index", size=80)
    plot_bit(heaan_norm,   ax=ax, label_prefix="HEAAN",   color=colors["blue"], scatter=True, xlabel="Normalize Bit index", size=50)


    plt.savefig(dir+f"{savename}.pdf", bbox_inches='tight')
    plt.savefig(dir+f"{savename}.png", bbox_inches='tight')
    if show:
        plt.show()


if __name__ == "__main__":
    main()
