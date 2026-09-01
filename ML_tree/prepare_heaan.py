#!/usr/bin/env python3
"""
Prepare raw HEAAN bit-flip campaign data for rel_error regression.

The prepared per-row dataset contains only:
    campaign_id, limb, coeff, bit, rel_error

Campaign configuration is written to heaan_campaigns.csv and joined by
campaign_id during training.

IMPORTANT:
- rel_error is the only training outcome.
- Outcome/severity columns such as correct/degraded/corrupted/failed,
  is_sdc, n_wrong, slot counters and l2_norm are never read from the raw
  per-injection files.
- Campaign metadata is written through a strict whitelist, so accidental
  outcome/severity columns in campaigns_start.csv are also excluded.

Usage:
    python3 prepare_heaan_updated.py RESULTS_DIR
    python3 prepare_heaan_updated.py RESULTS_DIR -o RESULTS_DIR/ml
    python3 prepare_heaan_updated.py RESULTS_DIR --format csv
    python3 prepare_heaan_updated.py RESULTS_DIR --stages mul_inside rescale_inside
    python3 prepare_heaan_updated.py RESULTS_DIR --every-nth-bit 4
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

# These are the only raw per-injection columns needed by the rel_error model.
RAW_COLUMNS = ["limb", "coeff", "bit", "rel_error"]
READ_DTYPES = {
    "limb": np.int64,
    "coeff": np.int64,
    "bit": np.int64,
    "rel_error": np.float64,
}
ROW_DTYPES = {
    "campaign_id": np.int32,
    "limb": np.int64,
    "coeff": np.int64,
    "bit": np.int64,
    "rel_error": np.float64,
}

# Strict whitelist for campaign-level model inputs/grouping variables.
# Anything not listed here is intentionally removed from prepared metadata.
META_KEEP = [
    "campaign_id",
    "stage",
    "op_step",
    "op_depth",
    "seed",
    "seed_input",
    "logN",
    "logQ",
    "logDelta",
    "logSlots",
    "dnum",
    "withNTT",
    "mult_depth",
    "isComplex",
    "bitPerCoeff",
    "doAdd",
    "doPlainMul",
    "doMul",
    "doRot",
    "doBoot",
    # Written by NN_modeling.py: where the injection really happened, before the
    # pipeline mapping rewrote stage/op_step. Never used as a model input (the
    # trainer's feature list does not mention them) — they exist so results can
    # be reported against the real NN location instead of the mapped one.
    "original_stage",
    "original_op_step",
    "original_op_depth",
]

# Needed by the current trainer regardless of which optional features exist.
REQUIRED_META = [
    "campaign_id",
    "stage",
    "op_step",
    "op_depth",
    "logN",
    "logQ",
    "logDelta",
    "logSlots",
]


def _validate_required_meta(meta: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_META if c not in meta.columns]
    if missing:
        sys.exit(
            "campaigns_start.csv is missing metadata required by the trainer: "
            + ", ".join(missing)
        )


def _keep_only_model_metadata(meta: pd.DataFrame) -> pd.DataFrame:
    """Remove every campaign metadata column that the trainer does not need."""
    kept = [c for c in META_KEEP if c in meta.columns]
    return meta.loc[:, kept].copy()


def load_campaigns(
    root: str,
    stages: list[str] | None,
    op_depths: list[int] | None,
    seeds: list[int] | None,
) -> pd.DataFrame:
    """Load campaign configuration, filter it, then apply the metadata whitelist."""
    path = os.path.join(root, "campaigns_start.csv")
    if not os.path.exists(path):
        sys.exit(f"no campaigns_start.csv under {root}")

    meta = pd.read_csv(path)
    _validate_required_meta(meta)

    if stages:
        meta = meta[meta.stage.isin(stages)]
        if meta.empty:
            sys.exit(f"no campaigns for stages={stages}")

    if op_depths is not None:
        meta = meta[meta.op_depth.isin(op_depths)]
        if meta.empty:
            sys.exit(f"no campaigns for op_depth={op_depths}")

    if seeds is not None:
        seed_col = next((c for c in ("seed", "seed_input") if c in meta.columns), None)
        if seed_col is None:
            sys.exit(
                "no 'seed' or 'seed_input' column in campaigns_start.csv "
                "-- can't filter by --seeds"
            )
        meta = meta[meta[seed_col].isin(seeds)]
        if meta.empty:
            sys.exit(f"no campaigns for {seed_col}={seeds}")

    meta = _keep_only_model_metadata(meta)
    return meta.reset_index(drop=True)


def read_rows(
    root: str,
    wanted: set[int],
    every_nth_bit: int,
    quiet: bool,
) -> pd.DataFrame:
    """Read only the raw columns needed for rel_error regression."""
    paths = sorted(glob.glob(os.path.join(root, "data", "campaign_*.csv")))
    if not paths:
        sys.exit(
            f"no data/campaign_*.csv under {root} — if only .csv.gz files exist, "
            "decompress them first"
        )

    frames: list[pd.DataFrame] = []
    empty_campaigns: list[int] = []
    t0 = time.time()
    matched = 0
    rows_so_far = 0

    for i, path in enumerate(paths, 1):
        m = CAMPAIGN_RE.search(os.path.basename(path))
        if not m:
            continue

        cid = int(m.group(1))
        if cid not in wanted:
            continue

        matched += 1
        try:
            # usecols is deliberate: no categorical severity/outcome columns,
            # slot counters, is_sdc, n_wrong or l2_norm are loaded at all.
            d = pd.read_csv(path, usecols=RAW_COLUMNS, dtype=READ_DTYPES)
        except pd.errors.EmptyDataError:
            empty_campaigns.append(cid)
            continue
        except ValueError as exc:
            sys.exit(f"{path}: expected raw columns {RAW_COLUMNS}: {exc}")

        if every_nth_bit > 1:
            d = d[d.bit % every_nth_bit == 0]

        if d.empty:
            continue

        d.insert(0, "campaign_id", cid)
        frames.append(d)
        rows_so_far += len(d)

        if not quiet and (matched % 100 == 0 or i == len(paths)):
            print(
                f"  read {matched:,} selected campaigns · {rows_so_far:,} rows "
                f"({time.time() - t0:.0f}s)",
                flush=True,
            )

    if not frames:
        sys.exit("no campaigns matched the filters or all matching campaigns were empty")

    if empty_campaigns:
        print(
            f"note: {len(empty_campaigns)} campaign(s) had no data and were skipped: "
            f"{sorted(empty_campaigns)[:20]}"
            + (" ..." if len(empty_campaigns) > 20 else "")
        )

    return pd.concat(frames, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "root",
        nargs="?",
        default=HERE,
        help="results-heaan directory (default: script directory)",
    )
    ap.add_argument(
        "-o",
        "--out-dir",
        default=None,
        metavar="DIR",
        help="where to write (default: <root>/ml)",
    )
    ap.add_argument(
        "--format",
        choices=["npz", "csv"],
        default="npz",
        help="npz (default) or gzipped CSV",
    )
    ap.add_argument("--stages", nargs="+", default=None, metavar="S")
    ap.add_argument("--op-depth", nargs="+", type=int, default=None, metavar="D")
    ap.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=[0, 1],
        metavar="N",
        help="keep these seed/seed_input values (default: 0 1)",
    )
    ap.add_argument(
        "--all-seeds",
        action="store_true",
        help="disable the seed filter",
    )
    ap.add_argument(
        "--every-nth-bit",
        type=int,
        default=1,
        metavar="K",
        help="keep bit indices divisible by K (default: 1, keep all)",
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.every_nth_bit <= 0:
        ap.error("--every-nth-bit must be > 0")

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
        stages = sorted(meta.stage.astype(str).unique())
        print(f"{len(meta):,} campaigns · stages {stages}")
        print(f"metadata columns kept: {', '.join(meta.columns)}")

    rows = read_rows(
        root,
        set(meta.campaign_id.astype(int)),
        args.every_nth_bit,
        args.quiet,
    )

    # rel_error = +inf is a legitimate outcome (the error overflowed) and the
    # 3-class trainer maps it to 'failed'. NaN and negative values are real
    # problems, but the trainer drops and reports them, so neither is worth
    # aborting a multi-hour prepare over. Report, do not exit.
    rel = rows.rel_error.to_numpy()
    n_nan = int(np.isnan(rel).sum())
    n_neg = int((rel < 0).sum())
    n_inf = int(np.isposinf(rel).sum())

    if n_inf:
        print(f"note: {n_inf:,} rows have rel_error = inf -> class 'failed'")
    if n_nan or n_neg:
        print(
            f"warning: rel_error has {n_nan:,} NaN and {n_neg:,} negative values; "
            "the trainer drops those rows"
        )

    # Keep metadata only for campaigns that actually contributed rows.
    present = set(rows.campaign_id.astype(int).unique())
    meta = meta[meta.campaign_id.astype(int).isin(present)].reset_index(drop=True)

    meta_path = os.path.join(out_dir, "heaan_campaigns.csv")
    meta.to_csv(meta_path, index=False)

    if args.format == "csv":
        data_path = os.path.join(out_dir, "heaan_rows.csv.gz")
        rows.to_csv(data_path, index=False, compression="gzip")
    else:
        data_path = os.path.join(out_dir, "heaan_rows.npz")
        arrays = {c: rows[c].to_numpy(dtype=dt) for c, dt in ROW_DTYPES.items()}
        np.savez_compressed(data_path, **arrays)

    print(f"\n{len(rows):,} prepared rows")
    print(
        f"rel_error: min={rows.rel_error.min():.4g}  "
        f"median={rows.rel_error.median():.4g}  "
        f"max={rows.rel_error.max():.4g}"
    )
    print(f"wrote {data_path}")
    print(f"      {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
