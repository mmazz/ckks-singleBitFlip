import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
import config

import matplotlib.pyplot as plt
from utils_parser import parse_args, build_filters

show = config.show
width = int(config.width)

CAMPAIGNS_CSV = "../results/campaigns_start.csv"
DATA_DIR = Path("../results/data")

def load_and_filter_campaigns(csv_path, filters):
    campaigns = pd.read_csv(csv_path)

    cat_cols = ["library", "stage"]
    for c in cat_cols:
        if c in campaigns.columns:
            campaigns[c] = (
                campaigns[c]
                .astype(str)
                .str.strip()
                .str.lower()
            )

    int_cols = [
        "campaign_id", "bitPerCoeff", "logN", "logQ", "logDelta", "logSlots",
        "mult_depth", "seed", "seed_input",
        "withNTT", "num_limbs", "logMin", "logMax"
    ]

    for c in int_cols:
        if c in campaigns.columns:
            campaigns[c] = pd.to_numeric(campaigns[c], errors="raise")

    mask = np.ones(len(campaigns), dtype=bool)

    print("=== MATCHES POR FILTRO ===")
    for col, (dtype, value) in filters.items():
        if col not in campaigns.columns:
            raise KeyError(f"Columna '{col}' no existe en el CSV")

        if dtype == "str":
            value = str(value).strip().lower()
        elif dtype == "int":
            value = int(value)
        else:
            raise ValueError(f"Tipo de filtro desconocido: {dtype}")

        m = campaigns[col] == value
        print(f"{col} == {value}: {m.sum()}")
        mask &= m

    selected = campaigns[mask]
    print(f"\nCampañas seleccionadas: {len(selected)}")

    return selected


def load_campaign_data(selected_campaigns, data_dir):
    dfs = []

    for _, row in selected_campaigns.iterrows():
        cid = int(row["campaign_id"])
        filename = f"campaign_{cid:06d}.csv.gz"
        path = data_dir / filename

        if not path.exists():
            print(f"WARNING: {path} no existe, se saltea")
            continue

        df = pd.read_csv(path, compression="gzip")
        df["campaign_id"] = cid
        dfs.append(df)

    if not dfs:
        raise RuntimeError("No se cargó ningún archivo de data")

    data = pd.concat(dfs, ignore_index=True)
    print("Data total cargada:", data.shape)
    return data


def mean_by_coeff_and_bit(data):
    print("coeff únicos en data:", data["coeff"].nunique())
    print("min/max coeff:", data["coeff"].min(), data["coeff"].max())
    mean_data = (
        data
        .groupby(["coeff", "bit"], as_index=False)
        .agg(mean_l2=("l2_norm", "mean"))
    )
    print("coeff únicos en mean_data:", mean_data["coeff"].nunique())
    return mean_data

def l2_norm_by_bit(mean_data):
    norm2 = (
        mean_data
        .groupby("bit")
        .apply(lambda g: np.linalg.norm(g["mean_l2"].values, ord=2))
        .reset_index(name="l2_norm")
    )
    return norm2


# ============================================================
# 5. PLOT
# ============================================================

def plot_l2(norm2_by_bit):
    plt.figure(figsize=(8, 5))
    plt.plot(norm2_by_bit["bit"], norm2_by_bit["l2_norm"], marker="o")
    plt.xlabel("Bit")
    plt.ylabel("Norma L2 del error promedio")
    plt.title("Norma L2 por bit (promediado sobre campañas)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_per_coefficient(mean_data, max_coeff=None):
    plt.figure(figsize=(10, 6))

    for coeff, g in mean_data.groupby("coeff"):
        if max_coeff is not None and coeff >= max_coeff:
            continue

        g = g.sort_values("bit")
        plt.plot(
            g["bit"],
            g["mean_l2"],
            alpha=0.4,
            linewidth=1
        )

    plt.xlabel("Bit")
    plt.ylabel("Mean L2 norm (avg over campaigns)")
    plt.title("Error per bit, one curve per coefficient")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_concatenated_coeffs(mean_data, bits_per_coeff=64):
    """
    Eje X: coeff * bits_per_coeff + bit
    Eje Y: mean_l2
    """

    # Construir eje X global
    x = mean_data["coeff"] * bits_per_coeff + mean_data["bit"]
    y = mean_data["mean_l2"]

    # Ordenar por eje X (importante)
    order = np.argsort(x)
    x = x.iloc[order]
    y = y.iloc[order]

    plt.figure(figsize=(12, 5))
    plt.plot(x, y, linewidth=width, color=config.colors["blue"])
    plt.yscale('symlog')
    plt.ylabel('$L_2$ norm (Symlog scale)')
    plt.xlabel('Modified Bit Index')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main():
    args = parse_args()
    filters = build_filters(args)

    print("Filtros activos:", filters)

    selected = load_and_filter_campaigns(CAMPAIGNS_CSV, filters)

    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data = load_campaign_data(selected, DATA_DIR)

    mean_data = mean_by_coeff_and_bit(data)
    norm2 = l2_norm_by_bit(mean_data)

    print("\n=== NORMA L2 POR BIT ===")
    print(norm2)
    print(args.bitPerCoeff)
    plot_concatenated_coeffs(mean_data, args.bitPerCoeff)


if __name__ == "__main__":
    main()

