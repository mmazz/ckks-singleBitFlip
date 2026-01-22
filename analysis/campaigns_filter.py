import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
CAMPAIGNS_CSV = "../results/campaigns_start.csv"
CAMPAIGNS_END_CSV = "../results/campaigns_end.csv"
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
        "mult_depth", "seed", "seed_input", "withNTT"
        "nums_limbs", "logMin", "logMax", "doAdd", "doMul", "doRot", "fileType"
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

    print(mask)
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

def load_end_data(selected_campaigns, csv_file, id_col="campaign_id"):

    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()

    # forzar tipo int en el CSV
    df[id_col] = pd.to_numeric(df[id_col], errors="raise")

    # convertir selected_ids a set de ints
    selected_campaigns = set(int(x) for x in selected_campaigns)

    filtered_df = df[df[id_col].isin(selected_campaigns)]

    if filtered_df.empty:
        raise ValueError(
            f"No se encontraron campañas para los IDs seleccionados "
            f"(IDs={len(selected_campaigns)}, CSV rows={len(df)})"
        )

    return filtered_df

