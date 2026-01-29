import matplotlib.pyplot as plt
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config


show = config.show
width = int(config.width)
s = config.size
colors = config.colors


def plot_bits(stats, ax=None, label_prefix="", color=colors["red"], scatter=False):

    if ax is None:
        ax = plt.gca()
    x = stats["bit"].to_numpy()


    mean = stats["l2_norm"].to_numpy()

    if scatter:
        ax.scatter(
            x,
            mean, color=color,
            s=s,                # 👈 tamaño del punto
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

def plot_bit(stats, Q=None, Delta=None, ax=None, label_prefix="", color=colors["red"], scatter=False, ylabel="Bit index"):

    if ax is None:
        ax = plt.gca()
    x = stats["bit"].to_numpy()


    x_norm = np.empty_like(x, dtype=float)
    if(Q and Delta):
        print("Masking")
        mask = x < Delta
        x_norm[mask] = x[mask] / Delta
        x_norm[~mask] = 1.0 + (x[~mask] - Delta) / (Q - Delta)
    else:
         x_norm = x

    mean = stats["mean_l2"].to_numpy()

    if scatter:
        ax.scatter(
            x_norm,
            mean, color=color,
            s=s,                # 👈 tamaño del punto
            zorder=4,            # 👈 arriba del plot
            label=f"{label_prefix} Mean $L_2$"
        )
    else:
        ax.plot(
            x_norm,
            mean,
            linewidth=2,
            marker="o",
            markersize=6,
            color=color,
            zorder=2,            # 👈 abajo del scatter
            label=f"{label_prefix} Mean $L_2$"
        )

    ax.set_yscale("symlog")
    ax.set_xlabel(ylabel)
    ax.set_ylabel("$L_2$ norm (symlog)")
    ax.grid(True, which="both")
