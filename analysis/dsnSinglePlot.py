from matplotlib.patches import Patch
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerPatch
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns

show = True
width = int(config.width)
colors = config.colors
s = config.size
fontSize = 24
fontLabelSize = 24
fontSize2 = fontSize - 8

NUM_COEFF_DISPLAY = 8
NUM_COEFF_DISPLAY = 2**12
withLegend = False
figSizeX = 6
figSizeY = 12
stagesCircles = True

fontAxisName = 24
circleSize = 0.01
circleFont = 55
circleYpos = -0.15

coeffLabel = 0.0
scatterSize = 50
dir = "img/"
SAVENAME = "encrypt"


#stages = ["encrypt_c0", "encrypt_c1"]
green = '#008000'
yellow = '#FFFF00'
orange ='#FFA500'
red = '#FF0000'
cmap = mcolors.LinearSegmentedColormap.from_list(
    "red_to_black", [red, "black"]
)


def mrep_color(val, mrep_max):
    if val < 0.1:
        return green
    elif val < 10:
        return yellow
    elif val < 100:
        return orange
    else:
        t = (val - 100) / (mrep_max - 100) if mrep_max > 100 else 1
        t = max(0, min(t, 1))
        return cmap(t)


#class HandlerColorbar(HandlerPatch):
#    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
#        import matplotlib.colors as mcolors
#        import numpy as np
#        from matplotlib.image import AxesImage
#
#        # dibuja el gradiente rojo->negro como rectangulo
#        ax = legend.axes if hasattr(legend, 'axes') else None
#        p = mpatches.FancyArrow(0, height/2, width, 0,
#                                width=height, head_width=0, head_length=0,
#                                transform=trans)
#        return [p]


def add_legend(fig, mrep_max):
    fig.canvas.draw()

    y_label  = .95   # altura de los rangos (debajo de los parches)
    y_patch  = y_label+0.08   # altura de los parches
    patch_h  = 0.030
    patch_w  = 0.035
    fig_w, fig_h = fig.get_size_inches()
    aspect = fig_h / fig_w

    patch_w = 0.025
    patch_h = patch_w / aspect
    items = [
        (0.08, green , 'Masked',       '<= ε'),
        (0.22, yellow, 'Minor SDC',    '<= 10%'),
        (0.42, orange, 'Moderate SDC', '10% - 100%'),
    ]

    for x, color, name, rng in items:
        # Cuadro de color
        ax_p = fig.add_axes([x - patch_w/2, y_patch - patch_h/2, patch_w, patch_h])
        ax_p.set_facecolor(color)
        ax_p.set_xticks([])
        ax_p.set_yticks([])
        for sp in ax_p.spines.values():
            sp.set_linewidth(0.5)

        # Nombre a la derecha del cuadro
        fig.text(x + patch_w/2 + 0.01, y_patch, name,
                 va='center', fontsize=fontSize2)

        # Rango centrado bajo el cuadro
        fig.text(x, y_label, rng,
                 ha='center', va='center', fontsize=fontSize2, color='black')

    # --- Severe SDC: colorbar ---
    cb_x = 0.76
    cb_w = 0.22

    ax_cb = fig.add_axes([cb_x - cb_w/2, y_patch - patch_h/2, cb_w, patch_h])
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list(
        'severe', [red, '#1a0000']
    )
    cb = plt.colorbar(
        plt.cm.ScalarMappable(cmap=cmap), cax=ax_cb, orientation='horizontal'
    )
    cb.set_ticks([])
    for sp in ax_cb.spines.values():
        sp.set_linewidth(0.5)

    # Nombre a la derecha del rectángulo
    fig.text(cb_x + cb_w/2 + 0.01, y_patch, 'Severe SDC',
             va='center', fontsize=fontSize2)

    # "100%" centrado bajo el inicio del rectángulo
    fig.text(cb_x - cb_w/2, y_label, '100%',
             ha='center', va='center', fontsize=fontSize - 4, color='black')

    # Valor máximo centrado bajo el final del rectángulo
    mrep_max_str = f'{mrep_max:.2e}%' if mrep_max >= 1e6 else f'{mrep_max:.0f}%'
    fig.text(cb_x + cb_w/2, y_label, mrep_max_str,
             ha='center', va='center', fontsize=fontSize2, color='black')

def plot_coeff_bit_mrep(df, ax, mrep_max ,title=None):
    df = df[df['coeff'].isin(range(NUM_COEFF_DISPLAY))].copy()

    coeff_order = list(range(NUM_COEFF_DISPLAY))
    coeff_idx = {c: i for i, c in enumerate(coeff_order)}

    colors = [mrep_color(v, mrep_max) for v in df['mrep']]
    x = [coeff_idx[c] for c in df['coeff']]
    y = df['bit'].tolist()

    ax.scatter(x, y, c=colors, s=scatterSize,  linewidths=0.8, zorder=3)
    ax.set_xticks([0, NUM_COEFF_DISPLAY-1])
    ax.set_xticklabels([coeff_order[0], coeff_order[NUM_COEFF_DISPLAY-1]],
                   rotation=0, ha='right', fontsize=fontSize)

    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    if title:
        ax.set_title(title, fontsize=fontSize)


def main():
    args = parse_args()
    savename = SAVENAME
    if args.title:
        savename = args.title

    fig, ax = plt.subplots(1, 1, figsize=( 5, figSizeY), sharey=True)
    mrep_max = 0
    campaign_dir =  config.CAMPAIGNS_CSV
    data_dir = config.DATA_DIR
    if("NN" in args.library):
        campaign_dir =  config.CAMPAIGNS_NN_CSV
        data_dir = config.DATA_NN_DIR
    filters = build_filters(args)
    selected = load_and_filter_campaigns(campaign_dir, filters)
    data = load_campaign_data(selected, data_dir)
    data['mrep'] = data['rel_error']*100
    df = data.groupby(['coeff', 'bit'])['mrep'].mean().reset_index()
    print(df['mrep'].head(100))
    plot_coeff_bit_mrep(df, ax, 1e153)

    mrep_max_temp = data['mrep'].max()  # o el max global de todos los dfs
    ax.set_ylabel('i-th Bit of Register', fontsize=fontAxisName, fontweight='bold')

    fig.text(0.55, coeffLabel, 'Coefficients', ha='center', fontsize=fontAxisName, fontweight='bold')

    # FIX: tight_layout ANTES de leer posiciones
    plt.tight_layout(rect=[0, 0.06, 1, 0.88])
    fig.canvas.draw()

    if(withLegend):
        add_legend(fig, mrep_max=mrep_max)
    plt.savefig("img/"+savename, bbox_inches='tight')
    plt.savefig("img/"+savename+".pdf", bbox_inches='tight')
    if(show):
        plt.show()


if __name__ == "__main__":
    main()
