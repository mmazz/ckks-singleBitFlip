import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config


width = int(config.width)
colors = config.colors

green = '#008000'
yellow = '#FFFF00'
orange ='#FFA500'
red = '#FF0000'
blue = '#4382B4'
cmap = mcolors.LinearSegmentedColormap.from_list(
    "red_to_black", [red, "black"]
)
def sdc_color(v, mrep_max=1):
    # Normalizar si corresponde
    if mrep_max != 0:
        v = v / mrep_max

    if 0 <= v <= 0.1:
        return "green"
    elif v <= 0.5:
        return "yellow"
    elif v <= 0.8:
        return "orange"
    else:
        return "red"
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


def plot_bits(stats, ax=None, label_prefix="", color=config.colors["red"], scatter=False, size=40, alpha=1):

    if ax is None:
        ax = plt.gca()
    x = stats["bit"].to_numpy()


    mean = stats["l2_norm"].to_numpy()

    if scatter:
        ax.scatter(
            x,
            mean, color=color,
            s=size,                # 👈 tamaño del punto
            alpha=alpha,
            zorder=4,            # 👈 arriba del plot
            label=f"Encrypt {label_prefix} Mean $L_2$"
        )
    else:
        ax.plot(
            x,
            mean,
            linewidth=2,
            marker="o",
            markersize=6,
            color=color,
            zorder=2,            # 👈 abajo del scatter
            label=f"Encrypt {label_prefix} Mean $L_2$"
        )

    ax.set_yscale("symlog")
    ax.set_xlabel("Bit index")
    ax.set_ylabel("$L_2$ norm (symlog)")
    ax.grid(True, which="both")
    ax.legend()
    plt.tight_layout()

def plot_bit_max_min(stats, ax=None, label_prefix="",  size=40):
    if ax is None:
        ax = plt.gca()

    x = stats["bit"]
    mean = stats["mean_l2"]
    std = stats["std_l2"]

    plt.figure(figsize=(12, 5))

    plt.scatter(
        x, mean,
        s=size,
        label="Mean $L_2$ error",
        zorder=2
    )

    plt.fill_between(
        x,
        mean - std,
        mean + std,
        alpha=0.3,
        label="±1 std",
        zorder=1
    )

    plt.scatter(x, stats["min_l2"], s=size, marker="_", color = colors["red"], label="Global Min", zorder=3)
    plt.scatter(x, stats["max_l2"], s=size, marker="+", color = colors["green"], label="Global Max", zorder=3)

    plt.yscale("symlog")
    plt.xlabel("Bit index")
    plt.ylabel("$L_2$ error (symlog)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()


def plot_bit(stats, ax=None, label_prefix="", color=colors["red"], scatter=True, xlabel="Bit index", label="Mean $L_2$", size=40, plot_std=False, alpha=1.0, dataType="l2"):

    if ax is None:
        ax = plt.gca()
    x = stats["bit"].to_numpy()

    mean = stats[f"mean_{dataType}"].to_numpy()
    if plot_std:
        std  = stats[f"std_{dataType}"]
    if scatter:
        ax.scatter(
            x,
            mean, color=color,
            alpha=alpha,
            s=size,                # 👈 tamaño del punto
            zorder=4,            # 👈 arriba del plot
            label=f"{label_prefix} {label}"
        )
    else:
        ax.plot(
            x,
            mean,
            linewidth=2,
            marker="o",
            markersize=6,
            color=color,
            zorder=2,            # 👈 abajo del scatter
            label=f"{label_prefix} {label}"
        )

    if plot_std:
        plt.fill_between(
            x,
            mean - std,
            mean + std,
            alpha=0.3,
            label="±1 std",
            zorder=1
        )
    ax.set_yscale("symlog")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("$L_2$ norm (symlog)")
    ax.grid(True, which="both")
    ax.legend()



def plot_bit_cat(stats, ax=None, label_prefix="", color=colors["red"], scatter=True, xlabel="Bit index", size=40, plot_std=False, alpha=1.0, dataType="sdc"):

    if ax is None:
        ax = plt.gca()
    x = stats["bit"].to_numpy()

    mean = stats[f"mean_{dataType}"].to_numpy()
    std = stats[f"std_{dataType}"]
    if scatter:
        ax.scatter(
            x,
            mean, color=color,
            alpha=alpha,
            s=size,
            zorder=4,
            label=f"{label_prefix} Mean SDC"
        )
    else:
        ax.plot(
            x,
            mean,
            linewidth=2,
            marker="o",
            markersize=6,
            color=color,
            zorder=2,
            label=f"{label_prefix} Mean SDC"
        )

    if plot_std:
        plt.fill_between(
            x,
            mean - std,
            mean + std,
            alpha=0.3,
            label="±1 std",
            zorder=1
        )
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0.0, 1.0])
    ax.set_yticklabels(["Mask", "SDC"])
    ax.set_xlabel(xlabel)
    ax.set_ylabel("SDC rate")
    ax.grid(True, which="both")
    ax.legend()


def add_legend(fig, mrep_max, fontSize):
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
                 va='center', fontsize=fontSize)

        # Rango centrado bajo el cuadro
        fig.text(x, y_label, rng,
                 ha='center', va='center', fontsize=fontSize, color='black')

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
             va='center', fontsize=fontSize)

    # "100%" centrado bajo el inicio del rectángulo
    fig.text(cb_x - cb_w/2, y_label, '100%',
             ha='center', va='center', fontsize=fontSize - 4, color='black')

    # Valor máximo centrado bajo el final del rectángulo
    mrep_max_str = f'{mrep_max:.2e}%' if mrep_max >= 1e6 else f'{mrep_max:.0f}%'
    fig.text(cb_x + cb_w/2, y_label, mrep_max_str,
             ha='center', va='center', fontsize=fontSize, color='black')

def plot_coeff_bit_mrep(df, ax, mrep_max, scatterSize, fontSize, fontSizeLegend=0, title=None):
    df = df[df['coeff'].isin(range(8))].copy()

    coeff_order = list(range(8))
    coeff_idx = {c: i for i, c in enumerate(coeff_order)}

    colors = [mrep_color(v, mrep_max) for v in df['mrep']]
    x = [coeff_idx[c] for c in df['coeff']]
    y = df['bit'].tolist()

    ax.scatter(x, y, c=colors, s=scatterSize,  linewidths=0.8, zorder=3)
    ax.set_xticks([0, 7])
    ax.set_xticklabels([coeff_order[0], coeff_order[7]],
                   rotation=0, ha='right', fontsize=fontSize)

    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    if title:
        ax.set_title(title, fontsize=fontSize)

def plot_coeff_bit_mrep_gap(df, ax, gap, mrep_max, scatterSize, fontSize, fontSizeLegend=0, title=None):
    df_group0 = df[df['coeff'] % gap == 0].copy()
    df_group1 = df[df['coeff'] % gap != 0].copy()

    # Promediar mrep por bit
    g0 = df_group0.groupby('bit')['mrep'].mean().reset_index()
    g1 = df_group1.groupby('bit')['mrep'].mean().reset_index()

    # X positions (dos columnas)
    x0 = [0] * len(g0)
    x1 = [1] * len(g1)

    # Colores según promedio de mrep
    colors0 = [mrep_color(v, mrep_max) for v in g0['mrep']]
    colors1 = [mrep_color(v, mrep_max) for v in g1['mrep']]

    # Scatter
    ax.scatter(x0, g0['bit'], c=colors0, s=scatterSize, linewidths=0.8, zorder=3)
    ax.scatter(x1, g1['bit'], c=colors1, s=scatterSize, linewidths=0.8, zorder=3)

    # Eje X
    ax.set_xticks([0, 1])
    ax.set_xticklabels(
        [f'coeff % {gap} == 0', f'coeff % {gap} != 0'],
        fontsize=fontSize
    )

    # Grid
    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    # Título
    if title:
        ax.set_title(title, fontsize=fontSize)

def plot_coeff_bit_sdc_gap(df, ax, gap,  scatterSize, fontSize, fontSizeLegend=0, title=None):
    df_group0 = df[df['coeff'] % gap == 0].copy()
    df_group1 = df[df['coeff'] % gap != 0].copy()

    # Promediar mrep por bit
    g0 = df_group0.groupby('bit')['is_sdc'].mean().reset_index()
    g1 = df_group1.groupby('bit')['is_sdc'].mean().reset_index()

    # X positions (dos columnas)
    x0 = [0] * len(g0)
    x1 = [1] * len(g1)

    # Colores según promedio de mrep
    colors0 = [sdc_color(v, 1) for v in g0['is_sdc']]
    colors1 = [sdc_color(v, 1) for v in g1['is_sdc']]

    # Scatter
    ax.scatter(x0, g0['bit'], c=colors0, s=scatterSize, linewidths=0.8, zorder=3)
    ax.scatter(x1, g1['bit'], c=colors1, s=scatterSize, linewidths=0.8, zorder=3)

    # Eje X
    ax.set_xticks([0, 1])
    ax.set_xticklabels(
        [f'coeff % {gap} == 0', f'coeff % {gap} != 0'],
        fontsize=fontSize
    )

    # Grid
    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    # Título
    if title:
        ax.set_title(title, fontsize=fontSize)


def plot_coeff_bit_sdc_modulo(df, ax, coeff_mod, scatterSize, fontSize, title=None):
    df = df.copy()

    # Crear grupo por resto
    df['group'] = df['coeff'] % coeff_mod  # gap = 8 en tu caso

    # Promediar por (grupo, bit)
    g = df.groupby(['group', 'bit'])['is_sdc'].mean().reset_index()

    # Plotear cada grupo como una columna
    for grp in sorted(g['group'].unique()):
        data = g[g['group'] == grp]

        x = [grp] * len(data)
        y = data['bit']
        colors = [sdc_color(v, 1) for v in data['is_sdc']]

        ax.scatter(x, y, c=colors, s=scatterSize, linewidths=0.8, zorder=3)

    # Eje X
    ax.set_xticks(range(coeff_mod))
    ax.set_xticklabels([f'% {coeff_mod} = {i}' for i in range(coeff_mod)], fontsize=fontSize)
    ax.set_xticks([0, 7])
    ax.set_xticklabels([0, 7],
                   rotation=0, ha='right', fontsize=fontSize)
    # Grid
    ax.grid(True, linestyle='--', alpha=0.3, zorder=0)

    # Título
    if title:
        ax.set_title(title, fontsize=fontSize)
