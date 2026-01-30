import pandas as pd
import numpy as np


def shift_bits(df, offset):
    df = df.copy()
    df["bit"] = df["bit"] + offset
    return df

def normalizer(data, logQ=None, logDelta=None):
    x = data["bit"].to_numpy(dtype=float)

    if logQ is None or logDelta is None:
        data = data.copy()
        data["bit_norm"] = x
        return data

    if logDelta >= logQ:
        raise ValueError("logDelta must be < logQ")

    x_norm = np.empty_like(x, dtype=float)

    mask = x < logDelta
    x_norm[mask] = x[mask] / logDelta
    x_norm[~mask] = 1.0 + (x[~mask] - logDelta) / (logQ - logDelta)

    data = data.copy()
    data["bit"] = x_norm
    return data

def split_by_gap(data, logN, logSlot):
    """
    - remove central coefficient N/2
    - classify coefficients by gap alignment
    """
    N = 1 << logN
    target_coeff = N // 2

    data = data[data["coeff"] != target_coeff].copy()

    gap = (1 << (logN - 1)) // (1 << logSlot)

    data["gap_class"] = np.where(
        data["coeff"] % gap == 0,
        "aligned",
        "non_aligned"
    )

    return data, gap

def stats_for_logslots_per_class(data, logN, logSlots):
    data, gap = split_by_gap(data, logN, logSlots)
    stats = stats_by_bit_per_class(data)

    out = {}

    for cls in ["aligned", "non_aligned"]:
        s = stats[stats["gap_class"] == cls]

        out[cls] = s[["bit", "mean_l2", "std_l2"]]

    return out, gap

def filter_coeff_by_library(data, library=None, logN=1):
    N = 1 << logN
    target_coeff = N // 2

    if library == "openfhe":
        print("No zero coeff")
        data = data[data["coeff"] != 0]
    if library == "heaan":
        print("No N/2 coeff")
        data = data[data["coeff"] != target_coeff]
    return data

def stats_by_bit_sdc(data):
    """
    Two-stage averaging:
    - mean over campaigns per (gap_class, bit, coeff)
    - stats over coefficients per bit
    """

    per_coeff = (
        data
        .groupby(["gap_class", "bit", "coeff"], as_index=False)
        .agg(sdc_rate=("is_sdc", "mean"))
    )

    per_bit = (
        per_coeff
        .groupby(["gap_class", "bit"], as_index=False)
        .agg(
            mean_sdc=("sdc_rate", "mean"),
            std_sdc=("sdc_rate", lambda x: x.std(ddof=0)),
            min_sdc=("sdc_rate", "min"),
            max_sdc=("sdc_rate", "max"),
            n_coeff=("sdc_rate", "count"),
        )
    )

    return per_bit


def stats_by_bit(data):
    # (1) global extremes by bit
    extrema = (
        data
        .groupby("bit", as_index=False)
        .agg(
            min_l2=("l2_norm", "min"),
            max_l2=("l2_norm", "max"),
        )
    )

    # if many seeds, we take average.
    per_coeff = (
        data
        .groupby(["bit", "coeff"], as_index=False)
        .agg(l2_mean=("l2_norm", "mean"))
    )

    # (3) stats entre coeficientes por bit
    stats = (
        per_coeff
        .groupby("bit", as_index=False)
        .agg(
            mean_l2=("l2_mean", "mean"),
            std_l2=("l2_mean", lambda x: x.std(ddof=0)),
        )
    )
    return stats.merge(extrema, on="bit")
