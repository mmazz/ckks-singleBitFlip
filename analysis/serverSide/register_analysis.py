import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import sys
import os
import copy
sys.path.append(os.path.abspath("../"))
from utils import config
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns
from pathlib import Path

# ------------------------------------------------------------------ #
# Config (mezcla de insideOp_analysis + registerPlotter)
# ------------------------------------------------------------------ #
show = config.show
width = int(config.width)
colors = config.colors
s = config.size
dir = "../img/"
SAVENAME = "add"

fontSize = 24
fontLabelSize = 24
fontSize2 = fontSize - 8
fontAxisName = 24
circleSize = 0.01
circleFont = 25
circleYpos = -0.05
coeffLabel = 0.05
scatterSize = 60
withLegend = False
stagesCircles = False  # no hay "stage" acá, solo op_step; se puede activar si querés numerarlos

green = '#008000'
yellow = '#FFFF00'
orange = '#FFA500'
red = '#FF0000'
cmap = mcolors.LinearSegmentedColormap.from_list("red_to_black", [red, "black"])

# Valor que se usa para colorear cada punto (bit, coeff).
# ASUNCION: usamos l2_norm con los mismos umbrales que registerPlotter usaba
# para mrep (0.1 / 10 / 100). Si l2_norm vive en otra escala, avisame y
# ajusto los umbrales de metric_color.
METRIC_COL = "l2_norm"
show=False

def metric_color(val, metric_max):
    if val < 0.1:
        return green
    elif val < 10:
        return yellow
    elif val < 100:
        return orange
    else:
        t = (val - 100) / (metric_max - 100) if metric_max > 100 else 1
        t = max(0, min(t, 1))
        return cmap(t)


def add_legend(fig, metric_max):
    fig.canvas.draw()
    y_label = .95
    y_patch = y_label + 0.08
    patch_w = 0.025
    fig_w, fig_h = fig.get_size_inches()
    aspect = fig_h / fig_w
    patch_h = patch_w / aspect

    items = [
        (0.08, green, 'Masked', '<= ε'),
        (0.22, yellow, 'Minor SDC', '<= 10%'),
        (0.42, orange, 'Moderate SDC', '10% - 100%'),
    ]

    for x, color, name, rng in items:
        ax_p = fig.add_axes([x - patch_w / 2, y_patch - patch_h / 2, patch_w, patch_h])
        ax_p.set_facecolor(color)
        ax_p.set_xticks([])
        ax_p.set_yticks([])
        for sp in ax_p.spines.values():
            sp.set_linewidth(0.5)
        fig.text(x + patch_w / 2 + 0.01, y_patch, name, va='center', fontsize=fontSize2)
        fig.text(x, y_label, rng, ha='center', va='center', fontsize=fontSize2, color='black')

    cb_x = 0.76
    cb_w = 0.22
    ax_cb = fig.add_axes([cb_x - cb_w / 2, y_patch - patch_h / 2, cb_w, patch_h])
    cb_cmap = mcolors.LinearSegmentedColormap.from_list('severe', [red, '#1a0000'])
    cb = plt.colorbar(plt.cm.ScalarMappable(cmap=cb_cmap), cax=ax_cb, orientation='horizontal')
    cb.set_ticks([])
    for sp in ax_cb.spines.values():
        sp.set_linewidth(0.5)

    fig.text(cb_x + cb_w / 2 + 0.01, y_patch, 'Severe SDC', va='center', fontsize=fontSize2)
    fig.text(cb_x - cb_w / 2, y_label, '100%', ha='center', va='center', fontsize=fontSize - 4, color='black')
    metric_max_str = f'{metric_max:.2e}' if metric_max >= 1e6 else f'{metric_max:.0f}'
    fig.text(cb_x + cb_w / 2, y_label, metric_max_str, ha='center', va='center', fontsize=fontSize2, color='black')


def plot_coeff_bit_metric(df, ax, metric_max, title=None):
    """Scatter estilo registerPlotter, pero un unico panel (sin separar por gap)."""
    coeff_order = sorted(df['coeff'].unique())
    coeff_idx = {c: i for i, c in enumerate(coeff_order)}

    point_colors = [metric_color(v, metric_max) for v in df[METRIC_COL]]
    x = [coeff_idx[c] for c in df['coeff']]
    y = df['bit'].tolist()

    ax.scatter(x, y, c=point_colors, s=scatterSize, linewidths=0.8, zorder=3)
    ax.set_xticks([0, len(coeff_order) - 1])
    ax.set_xticklabels([coeff_order[0], coeff_order[-1]], rotation=0, ha='right', fontsize=fontSize)
    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    if title:
        ax.set_title(title, fontsize=fontSize)


def main():
    ########################## ARGS ################################
    base_args = parse_args()
    savename = SAVENAME
    if base_args.title:
        savename = base_args.title
    args = copy.deepcopy(base_args)
    filters = build_filters(args)
    print(filters)

    op_type, op_step = filters["op_step"]
    ########################## LOOP POR op_step ################################
    while op_step >= 0:
        filters["op_step"] = (op_type, op_step)
        print(f"\n--- Processing op_step={op_step} ---")
        selected = load_and_filter_campaigns("../" + config.CAMPAIGNS_CSV, filters)
        print(selected)
        if selected.empty:
            print(f"WARNING: no campaigns for op_step={op_step}, skipped")
            op_step -= 1
            continue

        data = load_campaign_data(selected, Path("../") / config.DATA_DIR)
        # Sin split_by_gap: todo en un solo dataset, a nivel (bit, coeff)
        df = data.groupby(['bit', 'coeff'], as_index=False)[METRIC_COL].mean()
        metric_max = data[METRIC_COL].max()

        fig, ax = plt.subplots(1, 1, figsize=(10, 8))

        ########################## PLOT ################################
        plot_coeff_bit_metric(df, ax, metric_max, title=f"op_step={op_step}")

        ax.set_ylabel('i-th Bit of Register', fontsize=fontAxisName, fontweight='bold')
        fig.text(0.55, coeffLabel, 'Coefficients', ha='center', fontsize=fontAxisName, fontweight='bold')
        ax.tick_params(axis='both', labelsize=fontLabelSize)

        fig.tight_layout(rect=[0, 0.06, 1, 0.88])

        if withLegend:
            add_legend(fig, metric_max=metric_max)

        op_savename = f"{savename}_op_step_{op_step}"
        fig.savefig(dir + f"{op_savename}.pdf", bbox_inches='tight')
        fig.savefig(dir + f"{op_savename}.png", bbox_inches='tight')

        if show:
            plt.show()

        plt.close(fig)
        op_step -= 1


if __name__ == "__main__":
    main()
