import matplotlib.pyplot as plt
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config


width = int(config.width)
colors = config.colors
alpha = config.alpha

def plot_bits(stats, ax=None, label_prefix="", color=config.colors["red"], scatter=False, size=40):

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


def plot_bit(stats, ax=None, label_prefix="", color=colors["red"], scatter=False, ylabel="Bit index", size=40, plot_std=False):

    if ax is None:
        ax = plt.gca()
    x = stats["bit"].to_numpy()

    mean = stats["mean_l2"].to_numpy()
    std = stats["std_l2"]
    if scatter:
        ax.scatter(
            x,
            mean, color=color,
            s=size,                # 👈 tamaño del punto
            zorder=4,            # 👈 arriba del plot
            label=f"{label_prefix} Mean $L_2$"
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
            label=f"{label_prefix} Mean $L_2$"
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
    ax.set_xlabel(ylabel)
    ax.set_ylabel("$L_2$ norm (symlog)")
    ax.grid(True, which="both")
    ax.legend()
    plt.tight_layout()
