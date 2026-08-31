#!/usr/bin/env python3
"""
Build a compact per-bit-flip HEAAN NN evaluation dataset.

Input layout:

    <root>/
    ├── campaigns_start.csv
    └── data/
        ├── campaign_000001.csv
        ├── campaign_000002.csv
        └── ...

Each row in data/campaign_NNNNNN.csv corresponds to one injected bit flip.
The campaign id is obtained from the filename and links the row to
campaigns_start.csv.

Unlike prepare_heaan.py, this script:
  * does NOT use correct/degraded/corrupted/failed
  * does NOT use l2_norm or any measured rel_error
  * keeps `is_sdc` as the original ground truth
  * derives a synthetic rel_error only for compatibility/evaluation:
        is_sdc = 0 -> rel_error = 0.0
        is_sdc = 1 -> rel_error = 10.0

The saved rel_error is therefore NOT a measured regression target from the NN.
It is only a binary ground-truth encoding. The model still predicts a continuous
rel_error and predicted_is_sdc should be obtained with the desired threshold
(e.g. predicted_rel_error > 0.1).

Outputs:
    ml/heaan_sdc_rows.npz
    ml/heaan_sdc_campaigns.csv

Usage:
    python3 prepare_heaan_sdc.py
    python3 prepare_heaan_sdc.py /path/to/results-heaan
    python3 prepare_heaan_sdc.py --stages mul_inside rescale_inside
    python3 prepare_heaan_sdc.py --op-depth 1 2
    python3 prepare_heaan_sdc.py --seeds 0 1
    python3 prepare_heaan_sdc.py --all-seeds
    python3 prepare_heaan_sdc.py --every-nth-bit 4
    python3 prepare_heaan_sdc.py --format csv
"""

import argparse
import glob
import os
import re
import sys
import time

import numpy as np
import pandas as pd


HERE = os.path.dirname(os.path.abspath(__file__))

CAMPAIGN_RE = re.compile(r"campaign_(\d+)\.csv$")

# Read only the original per-injection information needed from the NN data.
# rel_error is derived below from is_sdc; it is not read from the raw CSV.
RAW_COLUMNS = ["limb", "coeff", "bit", "is_sdc"]

READ_DTYPES = {
    "limb": np.int64,
    "coeff": np.int64,
    "bit": np.int64,
    "is_sdc": np.int64,
}

ROW_DTYPES = {
    "campaign_id": np.int32,
    "limb": np.int64,
    "coeff": np.int64,
    "bit": np.int64,
    "is_sdc": np.int64,
    "rel_error": np.float64,
}

SDC_REL_ERROR_0 = 0.0
SDC_REL_ERROR_1 = 1.0


def load_campaigns(
    root: str,
    stages: list[str] | None,
    op_depths: list[int] | None,
    seeds: list[int] | None,
) -> pd.DataFrame:
    """Read campaign-level metadata and apply optional filters."""

    path = os.path.join(root, "campaigns_start_NN.csv")
    if not os.path.exists(path):
        sys.exit(f"no campaigns_start.csv under {root}")

    meta = pd.read_csv(path)

    if "campaign_id" not in meta.columns:
        sys.exit("campaigns_start.csv has no 'campaign_id' column")

    if stages:
        if "stage" not in meta.columns:
            sys.exit("campaigns_start.csv has no 'stage' column")
        meta = meta[meta.stage.isin(stages)]
        if meta.empty:
            sys.exit(f"no campaigns for stages={stages}")

    if op_depths is not None:
        if "op_depth" not in meta.columns:
            sys.exit("campaigns_start.csv has no 'op_depth' column")
        meta = meta[meta.op_depth.isin(op_depths)]
        if meta.empty:
            sys.exit(f"no campaigns for op_depth={op_depths}")

    if seeds is not None:
        seed_col = next(
            (c for c in ("seed", "seed_input") if c in meta.columns),
            None,
        )
        if seed_col is None:
            sys.exit(
                "no 'seed' or 'seed_input' column in campaigns_start.csv "
                "-- can't filter by --seeds"
            )

        meta = meta[meta[seed_col].isin(seeds)]
        if meta.empty:
            sys.exit(f"no campaigns for {seed_col}={seeds}")

    return meta.reset_index(drop=True)


def read_rows(
    root: str,
    wanted: set[int],
    every_nth_bit: int,
    quiet: bool,
) -> pd.DataFrame:
    """Read the selected per-campaign CSVs and concatenate their bit-flip rows."""

    paths = sorted(glob.glob(os.path.join(root, "data", "campaign_*.csv")))

    if not paths:
        sys.exit(
            f"no data/campaign_*.csv under {root} — "
            "the .csv.gz files may still need decompressing"
        )

    frames = []
    empty_campaigns = []
    t0 = time.time()

    matched = 0

    for i, path in enumerate(paths, 1):
        match = CAMPAIGN_RE.search(os.path.basename(path))
        if not match:
            continue

        campaign_id = int(match.group(1))

        if campaign_id not in wanted:
            continue

        matched += 1

        try:
            # Read only the columns needed for the SDC dataset.
            rows = pd.read_csv(
                path,
                usecols=RAW_COLUMNS,
                dtype=READ_DTYPES,
            )
        except pd.errors.EmptyDataError:
            empty_campaigns.append(campaign_id)
            continue
        except ValueError as exc:
            sys.exit(f"{path}: expected columns {RAW_COLUMNS}: {exc}")

        if every_nth_bit > 1:
            rows = rows[rows.bit % every_nth_bit == 0]

        if rows.empty:
            continue

        # Keep the original binary ground truth and add a synthetic rel_error
        # representation compatible with the rel_error prediction pipeline.
        # This is NOT a measured rel_error from the NN.
        rows["rel_error"] = np.where(
            rows["is_sdc"].to_numpy() == 1,
            SDC_REL_ERROR_1,
            SDC_REL_ERROR_0,
        ).astype(np.float64)

        rows.insert(0, "campaign_id", campaign_id)
        frames.append(rows)

        if not quiet and (matched % 200 == 0):
            print(
                f"  read {matched:,} selected campaigns "
                f"({time.time() - t0:.0f}s)",
                flush=True,
            )

    if not frames:
        sys.exit("no campaigns matched the filters")

    if empty_campaigns:
        print(
            f"note: {len(empty_campaigns)} campaign(s) had no data and were skipped: "
            f"{sorted(empty_campaigns)}"
        )

    return pd.concat(frames, ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "root",
        nargs="?",
        default=HERE,
        help="results-heaan directory (default: this script's directory)",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        default=None,
        metavar="DIR",
        help="output directory (default: <root>/ml)",
    )
    parser.add_argument(
        "--format",
        choices=["npz", "csv"],
        default="npz",
        help="output format: compressed npz (default) or gzipped CSV",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        default=None,
        metavar="S",
        help="keep only these stages",
    )
    parser.add_argument(
        "--op-depth",
        nargs="+",
        type=int,
        default=None,
        metavar="D",
        help="keep only these op_depth values",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=[0, 1],
        metavar="N",
        help="keep only these seed/seed_input values (default: 0 1)",
    )
    parser.add_argument(
        "--all-seeds",
        action="store_true",
        help="disable the --seeds filter",
    )
    parser.add_argument(
        "--every-nth-bit",
        type=int,
        default=1,
        metavar="K",
        help="keep bit indices divisible by K (default: 1, keep all)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress progress output",
    )

    args = parser.parse_args()

    if args.every_nth_bit < 1:
        parser.error("--every-nth-bit must be >= 1")

    root = os.path.abspath(args.root)
    out_dir = os.path.abspath(args.out_dir or os.path.join(root, "ml"))
    os.makedirs(out_dir, exist_ok=True)

    meta = load_campaigns(
        root,
        args.stages,
        args.op_depth,
        None if args.all_seeds else args.seeds,
    )

    if not args.quiet:
        print(f"{len(meta):,} campaigns selected")
        if "stage" in meta.columns:
            print(f"stages: {sorted(meta.stage.unique())}")

    rows = read_rows(
        root,
        set(meta.campaign_id.astype(int)),
        args.every_nth_bit,
        args.quiet,
    )

    # Sanity check: is_sdc is expected to be binary.
    values = sorted(rows.is_sdc.dropna().unique().tolist())
    invalid = [v for v in values if v not in (0, 1)]

    if invalid:
        sys.exit(f"is_sdc contains non-binary values: {invalid[:20]}")

    n_rows = len(rows)
    n_sdc = int(rows.is_sdc.sum())
    n_no_sdc = n_rows - n_sdc

    print(f"\n{n_rows:,} bit-flip rows")
    print(f"  is_sdc = 0   {n_no_sdc:>12,}  {n_no_sdc / n_rows:7.3%}")
    print(f"  is_sdc = 1   {n_sdc:>12,}  {n_sdc / n_rows:7.3%}")
    print(
        "  synthetic rel_error mapping: "
        f"is_sdc=0 -> {SDC_REL_ERROR_0:g}, "
        f"is_sdc=1 -> {SDC_REL_ERROR_1:g}"
    )

    expected_rel = np.where(
        rows["is_sdc"].to_numpy() == 1,
        SDC_REL_ERROR_1,
        SDC_REL_ERROR_0,
    )
    if not np.array_equal(rows["rel_error"].to_numpy(), expected_rel):
        sys.exit("internal error: synthetic rel_error does not match is_sdc")

    if n_sdc == 0:
        print(
            "\nwarning: is_sdc is 0 on every selected row; "
            "synthetic rel_error will therefore be 0 on every row."
        )
    elif n_no_sdc == 0:
        print(
            "\nwarning: is_sdc is 1 on every selected row; "
            "synthetic rel_error will therefore be 10 on every row."
        )

    # Keep campaign-level metadata separate, linked through campaign_id.
    meta_path = os.path.join(out_dir, "heaan_sdc_campaigns.csv")
    meta.to_csv(meta_path, index=False)

    if args.format == "csv":
        data_path = os.path.join(out_dir, "heaan_sdc_rows.csv.gz")
        rows.to_csv(data_path, index=False, compression="gzip")
    else:
        data_path = os.path.join(out_dir, "heaan_sdc_rows.npz")
        arrays = {
            column: rows[column].to_numpy(dtype=dtype)
            for column, dtype in ROW_DTYPES.items()
        }
        np.savez_compressed(data_path, **arrays)

    print(f"\nwrote {data_path}")
    print(f"      {meta_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
