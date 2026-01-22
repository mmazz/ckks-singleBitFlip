import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
import config

import matplotlib.pyplot as plt
from utils_parser import parse_args, build_filters
from campaigns_filter import load_and_filter_campaigns,load_end_data,CAMPAIGNS_CSV,CAMPAIGNS_END_CSV

def main():
    args = parse_args()
    filters = build_filters(args)

    print("Filtros activos:", filters)

    selected = load_and_filter_campaigns(CAMPAIGNS_CSV, filters)

    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    selected_ids = selected["campaign_id"].tolist()
    data = load_end_data(selected_ids, CAMPAIGNS_END_CSV)
    cols = ["l2_P95", "l2_P99"]
    block_sizes = [10, 100 ,300, 500, 800]

    for block in block_sizes:
        if len(data) >= block:
            mean_block = data.iloc[:block][cols].mean()
            print(f"Promedio de las primeras {block} filas:")
            print(mean_block)
            print()
if __name__ == "__main__":
    main()

