from matplotlib.patches import Patch
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerPatch
import matplotlib.patches as mpatches
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns

show = config.show
width = int(config.width)
colors = config.colors
s = config.size
fontSize = config.fontSize
fontSize2 = fontSize - 8
figSizeX = config.figSizeX
figSizeY = config.figSizeY
withLegend = False
dir = "img/"
SAVENAME = "encrypt"
#stages = ["encrypt_c0", "encrypt_c1"]
stages = ["encode", "encrypt_c0", "encrypt_c1", "decrypt_c0", "decrypt_c1", "decode"]
green = '#008000'
yellow = '#FFFF00'
orange ='#FFA500'
red = '#FF0000'



def mrep_color(val):
    if val < 0.1:
        return green
    elif val < 10:
        return yellow
    elif val < 100:
        return orange
    else:
        return red


class HandlerColorbar(HandlerPatch):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        import matplotlib.colors as mcolors
        import numpy as np
        from matplotlib.image import AxesImage

        # dibuja el gradiente rojo->negro como rectangulo
        ax = legend.axes if hasattr(legend, 'axes') else None
        p = mpatches.FancyArrow(0, height/2, width, 0,
                                width=height, head_width=0, head_length=0,
                                transform=trans)
        return [p]


def add_legend(fig, mrep_max):
    fig.canvas.draw()

    y_patch  = 0.88   # altura de los parches
    y_label  = 0.85   # altura de los rangos (debajo de los parches)
    patch_h  = 0.030
    patch_w  = 0.035

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

def plot_coeff_bit_mrep(df, ax, title=None):
    df = df[df['coeff'].isin(range(8))].copy()

    coeff_order = list(range(8))
    coeff_idx = {c: i for i, c in enumerate(coeff_order)}

    colors = [mrep_color(v) for v in df['mrep']]
    x = [coeff_idx[c] for c in df['coeff']]
    y = df['bit'].tolist()

    ax.scatter(x, y, c=colors, s=180,  linewidths=0.8, zorder=3)
    ax.set_xticks([i for i in range(len(coeff_order)) if i % 3 == 0])
    ax.set_xticklabels([coeff_order[i] for i in range(len(coeff_order)) if i % 3 == 0],
                       rotation=0, ha='right', fontsize=fontSize)

    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    if title:
        ax.set_title(title, fontsize=fontSize)


def main():
    args = parse_args()
    savename = SAVENAME
    if args.title:
        savename = args.title

    n = len(stages)
    fig, axes = plt.subplots(1, n, figsize=(n * 5, figSizeY), sharey=True)
    mrep_max = 0
    for i, (stage, ax) in enumerate(zip(stages, axes)):  # FIX: era (df, ax) pero zip era sobre stages
        filters = build_filters(args)
        filters["stage"] = ("str", stage)
        selected = load_and_filter_campaigns(config.CAMPAIGNS_CSV, filters)
        data = load_campaign_data(selected, config.DATA_DIR)
        data['mrep'] = data['rel_error']*100
        plot_coeff_bit_mrep(data, ax)

        # spines
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        if i == 0:
            ax.spines['right'].set_visible(False)
        else:
            ax.spines['left'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.axvline(x=-0.5, color='gray', linestyle='--', linewidth=1.2, zorder=2)

        ax.annotate(str(i + 1), xy=(0.5, -0.18), xycoords='axes fraction',
                    ha='center', va='center', fontsize=fontSize, color='white', fontweight='bold',
                    bbox=dict(boxstyle='circle,pad=0.4', facecolor=red, edgecolor='none'))

        mrep_max_temp = data['mrep'].max()  # o el max global de todos los dfs
        if mrep_max_temp >= mrep_max:
            mrep_max = mrep_max_temp
    axes[0].set_ylabel('i-th Bit of Register', fontsize=fontSize, fontweight='bold')
    fig.text(0.5, 0.02, 'Coeficiente', ha='center', fontsize=fontSize, fontweight='bold')

    # FIX: tight_layout ANTES de leer posiciones
    plt.tight_layout(rect=[0, 0.06, 1, 0.88])
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
    plt.show()


if __name__ == "__main__":
    main()
