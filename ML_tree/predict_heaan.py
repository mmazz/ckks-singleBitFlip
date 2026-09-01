#!/usr/bin/env python3
"""
Score a new prepared HEAAN run with a saved 3-class severity model.

Takes a model bundle written by train_heaan_multiclass_site_within_stage.py
(--save-model) plus a directory prepared by prepare_heaan.py, and reports an
aggregated view: predicted severity mix per injection site, predicted SDC rate,
and the riskiest bit positions.

If the prepared rows carry rel_error, it is used ONLY to score the predictions
after the fact — never as a model input — so you also get accuracy, macro F1
and a confusion matrix. Rows prepared without rel_error are still scored, just
without the comparison.

The feature matrix is built by importing the trainer module, so there is exactly
one implementation of the feature policy and predictions cannot silently drift
from training.

Examples:
  python3 predict_heaan.py heaan_sev3.joblib results-new/ml

  python3 predict_heaan.py heaan_sev3.joblib results-new/ml \
      --by campaign --out summary.csv

  python3 predict_heaan.py heaan_sev3.joblib results-new/ml \
      --by stage --top-bits 25
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(os.path.dirname(os.path.abspath(__file__)))
TRAINER = HERE / "train_heaan_multiclass_site_within_stage.py"

BUNDLE_FORMAT = 6


def load_trainer():
    """Import the trainer so features are built by the exact same code."""
    if not TRAINER.exists():
        sys.exit(f"cannot find {TRAINER.name} next to this script")

    spec = importlib.util.spec_from_file_location("heaan_trainer", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bundle(path: str):
    import joblib

    if not os.path.exists(path):
        sys.exit(f"no model at {path}")

    bundle = joblib.load(path)

    fmt = bundle.get("format")
    if fmt != BUNDLE_FORMAT:
        sys.exit(
            f"model bundle format {fmt} is not supported (expected {BUNDLE_FORMAT}) "
            "— retrain with the current train_heaan_multiclass_site_within_stage.py"
        )

    for key in ("model", "columns", "classes", "thresholds"):
        if key not in bundle:
            sys.exit(f"model bundle has no '{key}' — it was not written by the trainer")

    return bundle


# ---------------------------------------------------------------------------
# Column alignment
# ---------------------------------------------------------------------------

class Aligner:
    """Maps this run's feature columns onto the columns the model was fit on.

    A new run can carry a stage the model never saw (extra stage_* column) or be
    missing one it did (absent stage_* column). Both are handled the way the
    trainer's own reindex did: unknown columns are dropped, absent ones are
    filled with 0.
    """

    def __init__(self, ds_columns: list[str], model_columns: list[str]):
        pos = {c: i for i, c in enumerate(ds_columns)}
        self.idx = np.array([pos.get(c, -1) for c in model_columns], dtype=np.int64)
        self.take = self.idx >= 0

        self.missing = [c for c, i in zip(model_columns, self.idx) if i < 0]
        self.extra = [c for c in ds_columns if c not in set(model_columns)]
        self.n_out = len(model_columns)

    def __call__(self, X: np.ndarray) -> np.ndarray:
        if self.take.all() and len(self.idx) == X.shape[1] and np.array_equal(
            self.idx, np.arange(X.shape[1])
        ):
            return X

        out = np.zeros((len(X), self.n_out), dtype=np.float32)
        out[:, self.take] = X[:, self.idx[self.take]]
        return out


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class Aggregator:
    """Per-group predicted class counts, plus per-group confusion when truth exists."""

    def __init__(self, n_groups: int, n_bits: int, has_truth: bool, n_classes: int):
        self.k = n_classes
        self.n_groups = n_groups
        self.has_truth = has_truth

        self.pred = np.zeros(n_groups * n_classes, dtype=np.int64)
        self.bits = np.zeros((n_bits + 1) * n_classes, dtype=np.int64)
        self.bits_true = (
            np.zeros((n_bits + 1) * n_classes, dtype=np.int64) if has_truth else None
        )
        self.cm = (
            np.zeros(n_groups * n_classes * n_classes, dtype=np.int64)
            if has_truth
            else None
        )

    def add(self, gid, bit, pred, true=None):
        k = self.k
        gid = gid.astype(np.int64)
        pred = pred.astype(np.int64)
        bit = np.clip(bit.astype(np.int64), 0, len(self.bits) // k - 1)

        self.pred += np.bincount(gid * k + pred, minlength=len(self.pred))
        self.bits += np.bincount(bit * k + pred, minlength=len(self.bits))

        if self.has_truth and true is not None:
            true = true.astype(np.int64)
            self.cm += np.bincount(
                gid * k * k + true * k + pred, minlength=len(self.cm)
            )
            self.bits_true += np.bincount(bit * k + true, minlength=len(self.bits_true))

    def group_pred(self) -> np.ndarray:
        return self.pred.reshape(self.n_groups, self.k)

    def group_cm(self) -> np.ndarray | None:
        if not self.has_truth:
            return None
        return self.cm.reshape(self.n_groups, self.k, self.k)

    def bit_pred(self) -> np.ndarray:
        return self.bits.reshape(-1, self.k)

    def bit_true(self) -> np.ndarray | None:
        if not self.has_truth:
            return None
        return self.bits_true.reshape(-1, self.k)


def metrics_from_cm(cm: np.ndarray, Stats) -> dict:
    s = Stats()
    s.cm = cm.astype(np.int64)
    return {
        "accuracy": s.accuracy,
        "macro_f1": s.macro_f1,
        "sdc_accuracy": s.sdc_accuracy,
        "sdc_f1": s.sdc_f1,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    ap.add_argument("model", help="joblib bundle from --save-model")
    ap.add_argument("ml_dir", help="prepared directory to score")

    ap.add_argument(
        "--by",
        choices=["site", "campaign", "stage", "nn-site", "nn-stage"],
        default="site",
        help=(
            "aggregation level for the summary (default: site). nn-site and "
            "nn-stage group by original_stage/original_op_step, i.e. where the "
            "injection really happened before NN_modeling.py rewrote stage and "
            "op_step — predictions still come from the mapped features"
        ),
    )
    ap.add_argument("--out", default=None, metavar="CSV", help="write the summary table")
    ap.add_argument(
        "--top-bits",
        type=int,
        default=15,
        metavar="N",
        help="show the N riskiest bit positions (0 to skip)",
    )
    ap.add_argument(
        "--min-rows",
        type=int,
        default=200,
        metavar="N",
        help="ignore bit positions with fewer than N rows (default: 200)",
    )
    ap.add_argument("--block", type=int, default=2_000_000, metavar="N")
    ap.add_argument("--rebuild-cache", action="store_true")

    args = ap.parse_args()

    T = load_trainer()
    bundle = load_bundle(args.model)

    classes = list(bundle["classes"])
    if classes != T.CLASS_NAMES:
        sys.exit(
            f"model classes {classes} do not match this script's {T.CLASS_NAMES}"
        )

    thresholds = bundle["thresholds"]
    correct_max = float(thresholds["correct_max"])
    corrupted_max = float(thresholds["corrupted_max"])

    policy = bundle.get("feature_policy", {})
    extra = bool(policy.get("extra_features"))

    model = bundle["model"]
    model_columns = list(bundle["columns"])

    # -- load the run ------------------------------------------------------

    ds = T.Dataset(
        os.path.abspath(args.ml_dir),
        extra_features=extra,
        rebuild=args.rebuild_cache,
    )

    aligner = Aligner(ds.columns, model_columns)

    print(f"model:   {os.path.abspath(args.model)}")
    print(
        f"         {len(model_columns)} features · 3 classes · "
        f"correct <= {correct_max:g} < corrupted <= {corrupted_max:g} < failed"
        + (" · extra features ON" if extra else "")
    )

    cv = bundle.get("cv") or {}
    if cv:
        print(
            f"         trained CV ({cv.get('split', '?')}): "
            f"macro F1 {cv.get('macro_f1', float('nan')):.4f} · "
            f"SDC F1 {cv.get('sdc_f1', float('nan')):.4f}"
        )

    print(
        f"dataset: {ds.n_rows:,} rows · {ds.n_campaigns:,} campaigns · "
        + ("rel_error present" if ds.has_truth else "no rel_error (prediction only)")
    )

    if aligner.missing:
        print(
            f"  warning: {len(aligner.missing)} column(s) the model expects are "
            "absent here and are filled with 0: " + ", ".join(aligner.missing[:10])
            + (" ..." if len(aligner.missing) > 10 else "")
        )
    if aligner.extra:
        print(
            f"  warning: {len(aligner.extra)} column(s) present here are unknown to "
            "the model and are dropped: " + ", ".join(aligner.extra[:10])
            + (" ..." if len(aligner.extra) > 10 else "")
        )

    # -- coverage ----------------------------------------------------------

    train_sites = set(bundle.get("train_sites") or [])
    train_stages = set(bundle.get("train_stages") or [])

    run_sites = sorted(set(ds.site.tolist()))
    run_stages = sorted(set(ds.stage.tolist()))

    new_sites = [s for s in run_sites if s not in train_sites]
    new_stages = [s for s in run_stages if s not in train_stages]

    print()
    print(
        f"coverage: {len(run_sites) - len(new_sites)}/{len(run_sites)} sites in this "
        f"run were seen during training"
    )
    if new_stages:
        print(
            f"  {len(new_stages)} UNSEEN stage(s) — extrapolation, treat with care: "
            + ", ".join(new_stages[:10])
            + (" ..." if len(new_stages) > 10 else "")
        )
    if new_sites:
        print(
            f"  {len(new_sites)} unseen site(s) — this is the case the CV score above "
            "actually estimates: "
            + ", ".join(new_sites[:8])
            + (" ..." if len(new_sites) > 8 else "")
        )

    # -- grouping ----------------------------------------------------------

    def need(col: str):
        if col not in ds.meta.columns:
            sys.exit(
                f"--by {args.by} needs the '{col}' column in heaan_campaigns.csv. "
                "It is written by NN_modeling.py and passed through by "
                "prepare_heaan.py — re-run both if this run predates them."
            )
        return ds.meta[col].astype(str).to_numpy()

    if args.by == "site":
        keys = ds.site
    elif args.by == "stage":
        keys = ds.stage
    elif args.by == "nn-stage":
        keys = need("original_stage")
    elif args.by == "nn-site":
        keys = np.char.add(
            np.char.add(need("original_stage"), "/"), need("original_op_step")
        )
    else:
        keys = ds.meta.campaign_id.astype(str).to_numpy()

    group_names = sorted(set(keys.tolist()))
    group_of = {g: i for i, g in enumerate(group_names)}
    group_of_campaign = np.array([group_of[k] for k in keys], dtype=np.int64)

    site_of_campaign = ds.site
    seen_group = np.zeros(len(group_names), dtype=bool)
    for c in range(ds.n_campaigns):
        if site_of_campaign[c] in train_sites:
            seen_group[group_of_campaign[c]] = True

    # -- score -------------------------------------------------------------

    max_bit = 0
    for start, stop in T.blocks(ds.n_rows, args.block):
        b = ds.col["bit"][start:stop]
        if len(b):
            max_bit = max(max_bit, int(b.max()))

    agg = Aggregator(len(group_names), max_bit, ds.has_truth, len(classes))

    for start, stop in T.blocks(ds.n_rows, args.block):
        idx = np.arange(start, stop, dtype=np.int64)
        cidx = ds.col["cidx"][start:stop]

        X = aligner(ds.features(idx))
        pred = np.asarray(model.predict(X)).astype(np.int8)

        true = None
        if ds.has_truth:
            true = T.labels_from_rel_error(
                ds.col["rel_error"][start:stop], correct_max, corrupted_max
            )

        agg.add(group_of_campaign[cidx], ds.col["bit"][start:stop], pred, true)

    # -- overall -----------------------------------------------------------

    gp = agg.group_pred()
    totals = gp.sum(axis=0)
    n = int(totals.sum())

    print()
    print("Predicted class distribution")
    for i, name in enumerate(classes):
        print(f"  {name:<12}{int(totals[i]):>14,}{totals[i] / n:>10.3%}")
    print(f"  {'SDC rate':<12}{int(totals[1:].sum()):>14,}{totals[1:].sum() / n:>10.3%}")

    gcm = agg.group_cm()

    if gcm is not None:
        overall = gcm.sum(axis=0)
        stats = T.Stats()
        stats.cm = overall

        true_totals = overall.sum(axis=1)
        print()
        print("Actual class distribution (from rel_error)")
        for i, name in enumerate(classes):
            print(
                f"  {name:<12}{int(true_totals[i]):>14,}{true_totals[i] / n:>10.3%}"
            )
        print(
            f"  {'SDC rate':<12}{int(true_totals[1:].sum()):>14,}"
            f"{true_totals[1:].sum() / n:>10.3%}"
        )

        print()
        print("Scored against rel_error")
        print(f"  accuracy     {stats.accuracy:.4f}")
        print(f"  macro F1     {stats.macro_f1:.4f}")
        print(f"  weighted F1  {stats.weighted_f1:.4f}")
        print(f"  SDC accuracy {stats.sdc_accuracy:.4f}")
        print(f"  SDC F1       {stats.sdc_f1:.4f}")
        print()
        print("Per class")
        print(stats.report())
        print()
        print("Confusion matrix (rows=actual, cols=predicted)")
        print(stats.confusion())

        if cv and np.isfinite(cv.get("macro_f1", np.nan)):
            delta = stats.macro_f1 - float(cv["macro_f1"])
            verdict = (
                "in line with training CV"
                if abs(delta) < 0.05
                else ("BETTER than training CV" if delta > 0 else "WORSE than training CV")
            )
            print()
            print(
                f"  macro F1 here {stats.macro_f1:.4f} vs CV {cv['macro_f1']:.4f} "
                f"({delta:+.4f}) — {verdict}"
            )

    # -- per-group table ---------------------------------------------------

    rows = []
    for g, name in enumerate(group_names):
        total = int(gp[g].sum())
        if total == 0:
            continue

        rec = {
            args.by: name,
            "rows": total,
            "seen_in_training": bool(seen_group[g]),
        }
        for i, cname in enumerate(classes):
            rec[f"pred_{cname}"] = int(gp[g, i])
        rec["pred_sdc_rate"] = float(gp[g, 1:].sum() / total)

        if gcm is not None:
            cm = gcm[g]
            true_counts = cm.sum(axis=1)
            rec["true_sdc_rate"] = float(true_counts[1:].sum() / total)
            rec.update(metrics_from_cm(cm, T.Stats))

        rows.append(rec)

    summary = pd.DataFrame(rows).sort_values("pred_sdc_rate", ascending=False)

    print()
    print(f"Per {args.by} (sorted by predicted SDC rate)")

    show = [args.by, "rows"] + [f"pred_{c}" for c in classes] + ["pred_sdc_rate"]
    if gcm is not None:
        show += ["true_sdc_rate", "accuracy", "macro_f1"]
    show += ["seen_in_training"]

    with pd.option_context("display.max_rows", 200, "display.width", 200):
        print(
            summary[show].to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}",
            )
        )

    # -- riskiest bits -----------------------------------------------------

    if args.top_bits > 0:
        bp = agg.bit_pred()
        counts = bp.sum(axis=1)
        keep = counts >= args.min_rows

        if keep.any():
            rate = np.zeros(len(counts))
            rate[keep] = bp[keep, 1:].sum(axis=1) / counts[keep]

            order = np.argsort(-rate)
            order = [b for b in order if keep[b]][: args.top_bits]

            print()
            print(
                f"Riskiest bit positions (predicted SDC rate, "
                f">={args.min_rows:,} rows each)"
            )
            header = f"  {'bit':>5}{'rows':>12}{'pred SDC':>11}"
            if gcm is not None:
                header += f"{'true SDC':>11}"
            print(header)

            bt = agg.bit_true()
            for b in order:
                line = f"  {b:>5}{int(counts[b]):>12,}{rate[b]:>11.3%}"
                if bt is not None:
                    line += f"{bt[b, 1:].sum() / counts[b]:>11.3%}"
                print(line)

    # -- write -------------------------------------------------------------

    if args.out:
        out = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        summary.to_csv(out, index=False)
        print(f"\nsummary written to {out} ({len(summary)} rows)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
