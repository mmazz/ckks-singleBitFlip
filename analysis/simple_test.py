import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath('./'))
from utils import config

import matplotlib.pyplot as plt
from utils.args import parse_args, build_filters
from utils.io_utils import load_campaign_data, load_and_filter_campaigns

show = config.show
width = int(config.width)


def main():
    args = parse_args()
    filters = build_filters(args)

    print("Filtros activos:", filters)

    selected = load_and_filter_campaigns(
        config.CAMPAIGNS_CSV, filters
    )

    if selected.empty:
        raise RuntimeError("No hay campañas que cumplan los filtros")

    data = load_campaign_data(selected, config.DATA_DIR)

    limb1 = data[data["limb"]==1]
    print(limb1)

if __name__ == "__main__":
    main()
