#!/usr/bin/env python3
"""
Predict NN SDCs with a rel_error regressor trained only on basic HEAAN pipelines.

Expected input produced by prepare_heaan_sdc.py:

    <ml_dir>/
        heaan_sdc_rows.npz
        heaan_sdc_campaigns.csv

or, with --format csv:

    <ml_dir>/
        heaan_sdc_rows.csv.gz
        heaan_sdc_campaigns.csv

The NN dataset keeps the measured binary ground truth `is_sdc` and also stores
an artificial rel_error only for compatibility/inspection:

    is_sdc = 0 -> rel_error = 0.0
    is_sdc = 1 -> rel_error = 10.0

The model itself was trained on measured rel_error from BASIC pipelines.
It is NOT retrained here.

Prediction flow:

    basic-pipeline rel_error model
              |
              v
      predicted_rel_error
              |
          threshold 0.1
              |
      +-------+-------+
      |               |
   <= 0.1          > 0.1
 is_sdc=0         is_sdc=1

The synthetic NN rel_error (0/10) is not treated as a quantitative regression
measurement. Classification metrics are computed against the original is_sdc.

Usage:
    python3 predict_heaan_sdc.py heaan.joblib results/ml

    python3 predict_heaan_sdc.py heaan.joblib results/ml \
        -o predictions.csv

    python3 predict_heaan_sdc.py heaan.joblib results/ml \
        --threshold 0.1
"""

import argparse
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Reuse EXACTLY the same feature engineering as training.
from train_heaan_large import (
    NUMERIC,
    build_features,
    derive,
    from_log,
)


SDC_THRESHOLD = 0.1
SUPPORTED_BUNDLE_FORMATS = {3, 4}


def load_sdc_dataset(ml_dir: str) -> pd.DataFrame:
    """Load prepared NN rows and join campaign metadata."""
    ml_dir = os.path.abspath(ml_dir)

    meta_path = os.path.join(ml_dir, "heaan_sdc_campaigns.csv")
    npz_path = os.path.join(ml_dir, "heaan_sdc_rows.npz")
    csv_path = os.path.join(ml_dir, "heaan_sdc_rows.csv.gz")

    if not os.path.exists(meta_path):
        sys.exit(
            f"no heaan_sdc_campaigns.csv under {ml_dir}\n"
            "run prepare_heaan_sdc.py first"
        )

    if os.path.exists(npz_path):
        with np.load(npz_path, allow_pickle=False) as z:
            rows = pd.DataFrame({name: z[name] for name in z.files})
        source = npz_path
    elif os.path.exists(csv_path):
        rows = pd.read_csv(csv_path)
        source = csv_path
    else:
        sys.exit(
            f"no heaan_sdc_rows.npz or heaan_sdc_rows.csv.gz under {ml_dir}\n"
            "run prepare_heaan_sdc.py first"
        )

    meta = pd.read_csv(meta_path)

    required_rows = {
        "campaign_id",
        "limb",
        "coeff",
        "bit",
        "is_sdc",
        "rel_error",
    }
    missing_rows = sorted(required_rows - set(rows.columns))
    if missing_rows:
        sys.exit(
            f"{os.path.basename(source)} is missing required columns: "
            + ", ".join(missing_rows)
            + "\nRe-run the updated prepare_heaan_sdc.py."
        )

    if "campaign_id" not in meta.columns:
        sys.exit("heaan_sdc_campaigns.csv has no campaign_id column")

    # Avoid type mismatches during merge.
    rows["campaign_id"] = pd.to_numeric(
        rows["campaign_id"], errors="raise"
    ).astype(np.int64)
    meta["campaign_id"] = pd.to_numeric(
        meta["campaign_id"], errors="raise"
    ).astype(np.int64)

    if meta["campaign_id"].duplicated().any():
        duplicates = (
            meta.loc[meta["campaign_id"].duplicated(), "campaign_id"]
            .head(10)
            .tolist()
        )
        sys.exit(
            "heaan_sdc_campaigns.csv has duplicated campaign_id values, e.g. "
            + ", ".join(map(str, duplicates))
        )

    # Validate measured is_sdc.
    is_sdc = pd.to_numeric(rows["is_sdc"], errors="coerce")
    if is_sdc.isna().any():
        sys.exit("is_sdc contains missing/non-numeric values")

    bad_is_sdc = sorted(set(is_sdc.astype(int).unique()) - {0, 1})
    if bad_is_sdc:
        sys.exit(f"is_sdc must contain only 0/1; found {bad_is_sdc}")

    # Validate that prepare_heaan_sdc.py used the agreed 0/10 mapping.
    rel = pd.to_numeric(rows["rel_error"], errors="coerce")
    if rel.isna().any():
        sys.exit("synthetic rel_error contains missing/non-numeric values")

    expected_rel = np.where(is_sdc.to_numpy(dtype=int) == 1, 10.0, 0.0)
    if not np.allclose(rel.to_numpy(dtype=float), expected_rel):
        sys.exit(
            "prepared NN rel_error does not match the expected mapping: "
            "is_sdc=0 -> 0.0, is_sdc=1 -> 10.0"
        )

    df = rows.merge(
        meta,
        on="campaign_id",
        how="left",
        suffixes=("", "_meta"),
        validate="many_to_one",
    )

    # Any row without campaign metadata has invalid model features.
    meta_columns = [c for c in meta.columns if c != "campaign_id"]
    if meta_columns:
        no_meta = df[meta_columns].isna().all(axis=1)
        if no_meta.any():
            ids = df.loc[no_meta, "campaign_id"].drop_duplicates().head(10)
            sys.exit(
                f"{int(no_meta.sum()):,} rows have no campaign metadata; "
                f"campaign ids include {ids.tolist()}"
            )

    return df


def validate_bundle(bundle: dict, model_path: str) -> None:
    """Validate compatibility with the current rel_error-only trainer."""
    if not isinstance(bundle, dict):
        sys.exit(f"{model_path}: expected a model bundle dictionary")

    fmt = bundle.get("format")
    if fmt not in SUPPORTED_BUNDLE_FORMATS:
        sys.exit(
            f"{model_path}: unsupported model bundle format={fmt!r}; "
            f"expected one of {sorted(SUPPORTED_BUNDLE_FORMATS)}"
        )

    required = {
        "model",
        "columns",
        "regression",
        "target",
        "transform",
    }
    missing = sorted(required - set(bundle))
    if missing:
        sys.exit("model bundle is missing fields: " + ", ".join(missing))

    if bundle["regression"] is not True:
        sys.exit("this predictor requires a regression model")

    if bundle["target"] != "rel_error":
        sys.exit(
            f"this predictor requires target='rel_error'; "
            f"model has target={bundle['target']!r}"
        )

    if bundle["transform"] not in {"log1p", "identity"}:
        sys.exit(
            f"unsupported target transform={bundle['transform']!r}; "
            "expected 'log1p' or 'identity'"
        )

    if not isinstance(bundle["columns"], (list, tuple)) or not bundle["columns"]:
        sys.exit("model bundle has no feature columns")


def validate_raw_features(df: pd.DataFrame, bundle: dict) -> None:
    """
    Fail loudly when a raw input needed by the trained model is missing.

    One-hot stage columns are allowed to be absent after encoding because
    build_features(..., columns=...) intentionally reindexes them. Numeric
    dependencies cannot silently disappear.
    """
    model_columns = set(bundle["columns"])

    # Dependencies of engineered features generated by derive().
    deps = {
        "n": {"logN"},
        "rel_bit": {"bit", "logDelta"},
        "bit_minus_logq": {"bit", "logQ"},
        "bit_ge_logq": {"bit", "logQ"},
        "gaps": {"logN", "logSlots"},
        "coeff_mod_gaps": {"coeff", "logN", "logSlots"},
        "is_slot": {"coeff", "logN", "logSlots"},
        "coeff_ge_half": {"coeff", "logN"},
        "is_N2_coeff": {"coeff", "logN"},
        "n_add": {"doAdd"},
        "n_plainmul": {"doPlainMul"},
        "n_mul": {"doMul"},
        "n_rot": {"doRot"},
        "n_ops": {"doAdd", "doPlainMul", "doMul", "doRot"},
        "does_boot": {"doBoot"},
    }

    required_raw = set()

    for col in model_columns:
        if col in NUMERIC:
            if col in deps:
                required_raw.update(deps[col])
            else:
                required_raw.add(col)

    if any(col.startswith("stage_") for col in model_columns):
        required_raw.add("stage")

    missing = sorted(c for c in required_raw if c not in df.columns)
    if missing:
        sys.exit(
            "dataset is missing raw feature columns required by this model: "
            + ", ".join(missing)
            + "\nThese should normally come from heaan_sdc_campaigns.csv "
              "after NN_modeling.py has translated the NN pipeline."
        )

    bad = []
    for col in sorted(required_raw):
        if col == "stage":
            if df[col].isna().any():
                bad.append(col)
        else:
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.isna().any():
                bad.append(col)

    if bad:
        sys.exit(
            "required feature columns contain missing/non-numeric values: "
            + ", ".join(bad)
        )


def model_predict_rel_error(X: pd.DataFrame, bundle: dict) -> np.ndarray:
    """Return predictions in REAL rel_error space, not transformed space."""
    raw_pred = np.asarray(bundle["model"].predict(X), dtype=float)

    if bundle["transform"] == "log1p":
        pred_rel_error = from_log(raw_pred)
    else:
        pred_rel_error = np.clip(raw_pred, 0.0, None)

    if not np.isfinite(pred_rel_error).all():
        sys.exit("model produced NaN/inf rel_error predictions")

    return np.asarray(pred_rel_error, dtype=float)


def prediction_to_is_sdc(
    predicted_rel_error,
    threshold: float = SDC_THRESHOLD,
) -> np.ndarray:
    """Convert predicted rel_error to binary SDC."""
    return (
        np.asarray(predicted_rel_error, dtype=float) > threshold
    ).astype(np.int8)


def site_series(df: pd.DataFrame) -> pd.Series:
    """Same site representation stored by train_heaan_large.py."""
    return (
        df["stage"].astype(str)
        + "/"
        + df["op_step"].astype(str)
        + "@"
        + df["op_depth"].astype(str)
    )


def report_is_sdc(actual, predicted) -> None:
    """Print binary classification metrics against measured NN is_sdc."""
    a = pd.to_numeric(pd.Series(actual), errors="coerce")
    p = pd.to_numeric(pd.Series(predicted), errors="coerce")

    valid = a.notna() & p.notna()
    if not valid.all():
        print(
            f"warning: dropping {int((~valid).sum()):,} rows with missing "
            "is_sdc/predicted_is_sdc"
        )
        a = a[valid]
        p = p[valid]

    a = a.astype(int).to_numpy()
    p = p.astype(int).to_numpy()

    bad_actual = sorted(set(np.unique(a)) - {0, 1})
    bad_pred = sorted(set(np.unique(p)) - {0, 1})
    if bad_actual:
        sys.exit(f"is_sdc must contain only 0/1; found {bad_actual}")
    if bad_pred:
        sys.exit(f"predicted_is_sdc must contain only 0/1; found {bad_pred}")

    print("\nSDC score against measured NN is_sdc")
    print(f"  rows       {len(a):,}")
    print(f"  accuracy   {accuracy_score(a, p):.4f}")
    print(f"  precision  {precision_score(a, p, zero_division=0):.4f}")
    print(f"  recall     {recall_score(a, p, zero_division=0):.4f}")
    print(f"  F1         {f1_score(a, p, zero_division=0):.4f}")

    print("\nMeasured distribution")
    print(f"  is_sdc=0   {(a == 0).sum():,}  {(a == 0).mean():.2%}")
    print(f"  is_sdc=1   {(a == 1).sum():,}  {(a == 1).mean():.2%}")

    print("\nPredicted distribution")
    print(f"  is_sdc=0   {(p == 0).sum():,}  {(p == 0).mean():.2%}")
    print(f"  is_sdc=1   {(p == 1).sum():,}  {(p == 1).mean():.2%}")

    print()
    print(
        classification_report(
            a,
            p,
            labels=[0, 1],
            target_names=["is_sdc=0", "is_sdc=1"],
            zero_division=0,
        )
    )

    print(
        "Confusion matrix "
        "(rows = actual is_sdc, cols = predicted is_sdc)"
    )
    cm = confusion_matrix(a, p, labels=[0, 1])
    print(
        pd.DataFrame(
            cm,
            index=["actual 0", "actual 1"],
            columns=["pred 0", "pred 1"],
        ).to_string()
    )


def report_by_stage(df: pd.DataFrame) -> None:
    """Useful diagnostics after NN stages have been mapped to basic stages."""
    if "stage" not in df.columns:
        return

    actual = df["is_sdc"].to_numpy(dtype=int)
    pred = df["predicted_is_sdc"].to_numpy(dtype=int)

    work = pd.DataFrame({
        "stage": df["stage"].astype(str).to_numpy(),
        "actual": actual,
        "pred": pred,
    })
    work["hit"] = work["actual"] == work["pred"]

    grouped = (
        work.groupby("stage", dropna=False)
        .agg(
            rows=("hit", "size"),
            accuracy=("hit", "mean"),
            actual_sdc_rate=("actual", "mean"),
            predicted_sdc_rate=("pred", "mean"),
        )
        .sort_values("rows", ascending=False)
    )

    if len(grouped):
        print("\nScore by mapped basic stage")
        print(grouped.to_string(float_format=lambda x: f"{x:.4f}"))


def report_seen_unseen(df: pd.DataFrame, bundle: dict) -> None:
    """Optional accuracy split for exact basic sites seen/unseen in training."""
    train_sites = bundle.get("train_sites")
    needed = {"stage", "op_step", "op_depth"}

    if not train_sites or not needed.issubset(df.columns):
        return

    trained = set(map(str, train_sites))
    current = site_series(df)
    seen = current.isin(trained).to_numpy()

    actual = pd.to_numeric(df["is_sdc"], errors="coerce").to_numpy()
    pred = df["predicted_is_sdc"].to_numpy()

    valid = np.isfinite(actual)
    actual = actual[valid].astype(int)
    pred = pred[valid].astype(int)
    seen = seen[valid]

    if not len(actual):
        return

    hit = actual == pred

    print("\nExact mapped injection site coverage")

    if seen.any():
        print(
            f"  seen:    {int(seen.sum()):,} rows  "
            f"accuracy={hit[seen].mean():.4f}"
        )
    else:
        print("  seen:    0 rows")

    if (~seen).any():
        print(
            f"  unseen:  {int((~seen).sum()):,} rows  "
            f"accuracy={hit[~seen].mean():.4f}"
        )
    else:
        print("  unseen:  0 rows")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    ap.add_argument(
        "model_path",
        help=".joblib written by train_heaan_large.py --save-model",
    )
    ap.add_argument(
        "ml_dir",
        help="directory written by prepare_heaan_sdc.py",
    )
    ap.add_argument(
        "-o",
        "--out",
        default=None,
        metavar="CSV",
        help="write per-row predictions to CSV",
    )
    ap.add_argument(
        "--stages",
        nargs="+",
        default=None,
        metavar="S",
        help="only predict these MAPPED basic stages",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=SDC_THRESHOLD,
        metavar="X",
        help=(
            "predicted rel_error > X -> predicted_is_sdc=1 "
            f"(default: {SDC_THRESHOLD})"
        ),
    )

    args = ap.parse_args()

    if args.threshold < 0:
        ap.error("--threshold must be >= 0")

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    bundle = joblib.load(args.model_path)
    validate_bundle(bundle, args.model_path)

    print(f"model: {args.model_path}")
    print(f"  bundle format: {bundle['format']}")
    print("  target: rel_error regression")
    print(f"  transform: {bundle['transform']}")
    print(f"  features: {len(bundle['columns'])}")

    provenance = bundle.get("provenance", {})
    if "rows_fitted" in provenance:
        print(f"  trained on: {provenance['rows_fitted']:,} rows")
    if "split" in provenance:
        print(f"  split: {provenance['split']}")
    if "model_kind" in provenance:
        print(f"  model: {provenance['model_kind']}")

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------
    df = load_sdc_dataset(args.ml_dir)

    if args.stages:
        if "stage" not in df.columns:
            sys.exit(
                "--stages requested but heaan_sdc_campaigns.csv "
                "has no stage column"
            )
        df = df[df["stage"].isin(args.stages)].reset_index(drop=True)
        if df.empty:
            sys.exit(f"no rows for mapped stages={args.stages}")

    print(f"\ndata: {os.path.abspath(args.ml_dir)}")
    print(f"  rows: {len(df):,}")
    print(f"  campaigns: {df['campaign_id'].nunique():,}")
    print("  NN ground truth mapping: is_sdc=0 -> rel_error=0; is_sdc=1 -> rel_error=10")

    if "stage" in df.columns:
        print(f"  mapped stages: {sorted(df['stage'].astype(str).unique().tolist())}")

    validate_raw_features(df, bundle)

    # ------------------------------------------------------------------
    # EXACT same feature derivation as training
    # ------------------------------------------------------------------
    df = derive(df)

    numeric_model_features = [
        c for c in bundle["columns"] if c in NUMERIC
    ]
    missing_after_derive = [
        c for c in numeric_model_features if c not in df.columns
    ]
    if missing_after_derive:
        sys.exit(
            "could not build numeric features required by model: "
            + ", ".join(missing_after_derive)
        )

    X, _ = build_features(
        df,
        columns=bundle["columns"],
    )

    if list(X.columns) != list(bundle["columns"]):
        sys.exit("internal error: feature columns do not match saved model")

    # ------------------------------------------------------------------
    # Predict measured rel_error learned from BASIC pipelines.
    # ------------------------------------------------------------------
    predicted_rel_error = model_predict_rel_error(X, bundle)

    df["predicted_rel_error"] = predicted_rel_error
    df["predicted_is_sdc"] = prediction_to_is_sdc(
        predicted_rel_error,
        threshold=args.threshold,
    )

    print(f"\nscored {len(df):,} rows")
    print(
        "predicted rel_error: "
        f"min={np.min(predicted_rel_error):.4g}  "
        f"median={np.median(predicted_rel_error):.4g}  "
        f"p90={np.percentile(predicted_rel_error, 90):.4g}  "
        f"max={np.max(predicted_rel_error):.4g}"
    )
    print(
        f"decision rule: rel_error <= {args.threshold} -> is_sdc=0; "
        f"> {args.threshold} -> is_sdc=1"
    )

    # ------------------------------------------------------------------
    # Compare thresholded prediction against measured is_sdc.
    # ------------------------------------------------------------------
    report_is_sdc(
        df["is_sdc"],
        df["predicted_is_sdc"],
    )

    report_by_stage(df)
    report_seen_unseen(df, bundle)

    # ------------------------------------------------------------------
    # Optional CSV
    # ------------------------------------------------------------------
    if args.out:
        preferred = [
            "campaign_id",
            "original_stage",
            "original_op_step",
            "nn_stage",
            "nn_op_step",
            "stage",
            "op_step",
            "op_depth",
            "limb",
            "coeff",
            "bit",
            "doAdd",
            "doPlainMul",
            "doMul",
            "doRot",
            "doBoot",
            "is_sdc",
            "rel_error",               # synthetic NN ground truth: 0/10
            "predicted_rel_error",     # model prediction from basic pipelines
            "predicted_is_sdc",
        ]
        cols = [c for c in preferred if c in df.columns]

        df[cols].to_csv(args.out, index=False)
        print(f"\nwrote {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
