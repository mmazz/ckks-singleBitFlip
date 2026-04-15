from matplotlib.patches import Patch
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerPatch
import matplotlib.patches as mpatches

import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.plotters import add_legend, plot_coeff_bit_sdc_gap, plot_coeff_bit_sdc_modulo
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns

show = True
width = int(config.width)
colors = config.colors
s = config.size
fontSize = 24
fontLabelSize = 24
fontSize2 = fontSize - 8


withLegend = False
figSizeX = 6
figSizeY = 6
stagesCircles = True

fontAxisName = 24
circleSize = 0.01
circleFont = 25
circleYpos = -0.1

coeffLabel = -0.08
scatterSize =135
dir = "img/"
SAVENAME = "encrypt"
idx_mul1=[0,1,2,3,4,5,6]
idx_mul2=[7,8,9,10,11,12]



#stages = ["encrypt_c0", "encrypt_c1"]
idx_inside1=[0,1,2,3,4]
idx_inside2=[5,6,7,8,9]

idx_outside1=[0,1,2,3,4,5,6,7]
idx_outside2=[8,9,10,11,12,13]
def main():
    args = parse_args()
    savename = SAVENAME
    if args.title:
        savename = args.title

    filters = build_filters(args)
    title_select = filters["title"][1]
    steps = []
    camp_csv = config.CAMPAIGNS_CSV
    data_csv = config.DATA_DIR

    if filters["library"][1] == "heaanNN":
        camp_csv = config.CAMPAIGNS_NN_CSV
        data_csv = config.DATA_NN_DIR

    if "cheby1" in title_select:
        steps=idx_inside1
    elif "cheby2" in title_select:
        steps=idx_inside2
    elif "hidden1" in title_select:
        steps=idx_outside1
    elif "hidden2" in title_select:
        steps=idx_outside2
    elif "mul1" in title_select:
        steps = idx_mul1
    elif "mul2" in title_select:
        steps = idx_mul2

    n = len(steps)
    fig, axes = plt.subplots(1, n, figsize=(n * 2, figSizeY), sharey=True)
    fig.subplots_adjust(wspace=0.01)
    mrep_max = 0
    for i, (step, ax) in enumerate(zip(steps, axes)):  # FIX: era (df, ax) pero zip era sobre stages
        filters = build_filters(args)
        filters["op_index"] = ("int", step)
        print(filters["op_index"])

        selected = load_and_filter_campaigns(camp_csv, filters)
        data = load_campaign_data(selected, data_csv)
        df = data.groupby(['coeff', 'bit'])['is_sdc'].mean().reset_index()
        plot_coeff_bit_sdc_modulo(df, ax, 8, scatterSize, fontSize)

        # spines
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        if i == 0:
            ax.spines['right'].set_visible(False)
        else:
            ax.spines['left'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.axvline(x=-0.5, color='gray', linestyle='--', linewidth=1.2, zorder=2)
        if(stagesCircles):
            ax.annotate(str(steps[i]), xy=(0.5, circleYpos), xycoords='axes fraction',
                        ha='center', va='center', fontsize=circleFont, color='white', fontweight='bold',
                        bbox=dict(boxstyle=f'circle,pad={circleFont*circleSize}', facecolor=colors["blue"], edgecolor='none'))

    axes[0].set_ylabel('i-th Bit of Register', fontsize=fontAxisName, fontweight='bold')
    fig.text(0.55, coeffLabel, 'Coefficients', ha='center', fontsize=fontAxisName, fontweight='bold')
    for ax in axes:
        ax.tick_params(axis='both', labelsize=fontLabelSize)
    # FIX: tight_layout ANTES de leer posiciones
 #   plt.tight_layout(rect=[0, 0.06, 1, 0.88])
    fig.canvas.draw()

    # línea top continua
    spine = axes[0].spines['left']
    bbox = spine.get_window_extent(fig.canvas.get_renderer())
    x_left = fig.transFigure.inverted().transform((bbox.x0, 0))[0]
    y_top = axes[0].get_position().y1
    x_right = axes[-1].get_position().x1

    fig.add_artist(plt.Line2D([x_left, x_right], [y_top, y_top],
                              transform=fig.transFigure,
                              color='black', linewidth=0.8,
                              clip_on=False))

    # línea bottom continua
    for ax in axes:
        ax.axhline(y=ax.get_ylim()[0], color='black', linewidth=0.8, zorder=5)
    if(withLegend):
        add_legend(fig, mrep_max=mrep_max)
    plt.savefig("img/"+savename, bbox_inches='tight')
    plt.savefig("img/"+savename+".pdf", bbox_inches='tight')
    if(show):
        plt.show()


if __name__ == "__main__":
    main()
