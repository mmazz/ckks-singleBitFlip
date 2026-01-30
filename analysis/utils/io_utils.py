import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

REQUIRED_FILTERS = {"library", "stage"}

OPTIONAL_DEFAULTS = {
    "withNTT": 0,
    "logN": 6,
    "logSlots": 5,
    "logQ": 60,
    "logDelta": 50,
    "mult_depth": 0,
    "logMin": 0,
    "logMax": 0,
    "doAdd": 0,
    "doMul": 0,
    "doRot": 0,
    "bitPerCoeff": 64,
    "dnum": 3,
}

OPTIONAL_NO_FILTER = {"seed", "seed_input", "isExhaustive", "scaleTech"}


def load_and_filter_campaigns(csv_path, filters):
    campaigns = pd.read_csv(csv_path)

    # --- Normalization ---
    for c in campaigns.columns:
        if campaigns[c].dtype == object:
            campaigns[c] = (
                campaigns[c]
                .astype(str)
                .str.strip()
                .str.lower()
            )

    for c in campaigns.columns:
        if c not in ["library", "stage", "scaleTech"]:
            campaigns[c] = pd.to_numeric(campaigns[c], errors="coerce")

    missing = REQUIRED_FILTERS - filters.keys()
    if missing:
        raise ValueError(
            f"Missing mandatory filters: {sorted(missing)}"
        )

    effective_filters = {}
    for k in REQUIRED_FILTERS:
        effective_filters[k] = filters[k]

    for k, default in OPTIONAL_DEFAULTS.items():
        if k in filters:
            effective_filters[k] = filters[k]
        elif default is not None:
            effective_filters[k] = ("int", default)

    for k in OPTIONAL_NO_FILTER:
        if k in filters:
            effective_filters[k] = filters[k]

    mask = np.ones(len(campaigns), dtype=bool)

    print("=== MATCHES BY FILTERS ===")
    for col, (dtype, value) in effective_filters.items():
        if col not in campaigns.columns:
            raise KeyError(f"The column '{col}' does not exist in the CSV")

        if dtype == "str":
            value = str(value).strip().lower()
        elif dtype == "int":
            value = int(value)
        else:
            raise ValueError(f"Unknown filter type: {dtype}")

        m = campaigns[col] == value
        print(f"{col} == {value}: {m.sum()}")
        mask &= m

    selected = campaigns[mask]
    print(f"\nSelected campaigns: {len(selected)}")

    return selected

def load_campaign_data(selected_campaigns, data_dir):
    dfs = []

    for _, row in selected_campaigns.iterrows():
        cid = int(row["campaign_id"])
        filename = f"campaign_{cid:06d}.csv.gz"
        path = data_dir / filename

        if not path.exists():
            print(f"WARNING: {path} does not exist, is skipped")
            continue

        df = pd.read_csv(path, compression="gzip")
        df["campaign_id"] = cid
        dfs.append(df)

    if not dfs:
        raise RuntimeError("No data file was uploaded")

    data = pd.concat(dfs, ignore_index=True)
    print("Total data uploaded:", data.shape)
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
            f"No campaigns were found for the selected IDs"
            f"(IDs={len(selected_campaigns)}, CSV rows={len(df)})"
        )

    return filtered_df

