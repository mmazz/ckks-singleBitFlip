#!/usr/bin/env python3
"""
Memory-bounded HEAAN severity classifier, 3 classes derived from rel_error.

    correct    : rel_error <= 0.1
    corrupted  : 0.1 < rel_error <= 10.0
    failed     : rel_error > 10.0

Input (same prepare pipeline as before), under ml_dir:
  - heaan_rows.npz  or  heaan_rows.csv.gz   with campaign_id, limb, coeff, bit,
    rel_error   (one row per injected fault)
  - heaan_campaigns.csv                     with one row per campaign

rel_error is used ONLY to build the label. It is never a model input.

Model inputs are the RAW recorded columns, nothing engineered:

    per row       bit, coeff, limb
    per campaign  op_step, op_depth, logN, logQ, logDelta, logSlots, dnum,
                  withNTT, mult_depth, isComplex, bitPerCoeff,
                  doAdd, doPlainMul, doMul, doRot, doBoot, stage (one-hot)

--extra-features adds back the handful of derived columns that an axis-aligned
tree provably cannot build on its own (differences and a modulo). Everything
else the old version derived was either a monotone transform of an existing
column (n = 2**logN, gaps) or a literal copy (n_add = doAdd, ...), which is
dead weight for a tree. See EXTRA_FEATURES below.

How it stays memory-bounded
---------------------------
The first run streams the prepared rows once into a compact binary cache
(.heaan_cache/, 17 bytes per row) and then never re-reads the source. Folds,
sampling and scoring all run over memmaps of that cache, so a 50M-row dataset
costs ~850 MB of disk and almost no RAM. Campaign columns are never stored per
row: they are looked up from a small per-campaign matrix at the moment a
feature block is built.

Examples
--------
  python3 train_heaan_multiclass_site_within_stage.py results/ml

  python3 train_heaan_multiclass_site_within_stage.py results/ml \
      --model forest --trees 200 --depth 16 \
      --save-model heaan_sev3_forest.joblib

  # sanity check: in-distribution split (optimistic, leaks sibling rows)
  python3 train_heaan_multiclass_site_within_stage.py results/ml --split random
"""

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text


HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_TREES = 200
DEFAULT_DEPTH = 8
DEFAULT_SAMPLE = 1_000_000
DEFAULT_BLOCK = 2_000_000

CORRECT_MAX = 0.1
CORRUPTED_MAX = 10.0

CLASS_NAMES = ["correct", "corrupted", "failed"]
N_CLASSES = 3


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

# Recorded per injected fault, in heaan_rows.
ROW_FEATURES = ["bit", "coeff", "limb"]

# Recorded per campaign, in heaan_campaigns. Missing ones are dropped with a
# warning instead of being silently filled.
CAMPAIGN_NUMERIC = [
    "op_step",
    "op_depth",
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
]

CAMPAIGN_CATEGORICAL = ["stage"]

# Only the derived columns a tree cannot express as a split on the raw inputs.
# Each is either a difference of two raw columns or a modulo, both of which are
# invisible to axis-aligned splits.
EXTRA_FEATURES = [
    "rel_bit",         # bit - logDelta   (bit position relative to the scale)
    "bit_minus_logq",  # bit - logQ       (is the bit above the modulus?)
    "coeff_mod_gaps",  # coeff % gaps     (slot alignment)
    "is_slot",         # coeff_mod_gaps == 0
    "coeff_ge_half",   # coeff >= N/2
    "n_ops",           # doAdd + doPlainMul + doMul + doRot
]

CACHE_FORMAT = 2

# Compact on-disk row cache. 17 bytes/row.
CACHE_COLUMNS = {
    "cidx": np.int32,       # index into the campaign table, not the raw id
    "limb": np.int32,
    "coeff": np.int32,
    "bit": np.int32,
    "rel_error": np.float32,  # kept raw so thresholds stay tunable
}

# rel_error is optional: without it the rows can still be scored by a saved
# model, they just cannot be trained on or compared against ground truth.
REQUIRED_ROW_COLUMNS = ["campaign_id", "limb", "coeff", "bit"]
TRUTH_COLUMN = "rel_error"

REQUIRED_META_COLUMNS = [
    "campaign_id",
    "stage",
    "op_step",
    "op_depth",
    "logN",
    "logQ",
    "logDelta",
    "logSlots",
]


def labels_from_rel_error(rel, correct_max: float, corrupted_max: float) -> np.ndarray:
    """0 = correct, 1 = corrupted, 2 = failed. NaN must be filtered upstream."""
    rel = np.asarray(rel, dtype=np.float32)
    out = np.zeros(len(rel), dtype=np.int8)
    out[rel > correct_max] = 1
    out[rel > corrupted_max] = 2
    return out


def blocks(n: int, size: int):
    for start in range(0, n, size):
        yield start, min(start + size, n)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class Dataset:
    """Campaign table + a memmapped compact copy of the prepared rows."""

    def __init__(self, ml_dir: str, extra_features: bool, rebuild: bool = False):
        self.dir = Path(ml_dir)
        self.extra = bool(extra_features)

        self.meta_path = self.dir / "heaan_campaigns.csv"
        self.csv_path = self.dir / "heaan_rows.csv.gz"
        self.npz_path = self.dir / "heaan_rows.npz"
        self.cache_dir = self.dir / ".heaan_cache"

        if not self.meta_path.exists():
            sys.exit(f"no heaan_campaigns.csv under {self.dir}")

        if self.npz_path.exists():
            self.source = self.npz_path
        elif self.csv_path.exists():
            self.source = self.csv_path
        else:
            sys.exit(f"no heaan_rows.npz or heaan_rows.csv.gz under {self.dir}")

        self._load_meta()
        self._build_campaign_matrix()

        if rebuild and self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        self._ensure_cache()
        self._open_cache()

    # -- campaign table ----------------------------------------------------

    def _load_meta(self):
        meta = pd.read_csv(self.meta_path)

        missing = [c for c in REQUIRED_META_COLUMNS if c not in meta.columns]
        if missing:
            sys.exit(
                "heaan_campaigns.csv is missing required columns: "
                + ", ".join(missing)
            )

        if meta.campaign_id.duplicated().any():
            dup = int(meta.campaign_id.duplicated().sum())
            sys.exit(f"heaan_campaigns.csv has {dup:,} duplicate campaign_id rows")

        self.meta = meta.reset_index(drop=True)
        self.n_campaigns = len(meta)

        self.stage = self.meta.stage.astype(str).to_numpy()
        self.site = (
            self.meta.stage.astype(str)
            + "/"
            + self.meta.op_step.astype(str)
            + "@"
            + self.meta.op_depth.astype(str)
        ).to_numpy()

        # campaign_id -> row index, integer fast path plus a string fallback
        cid = self.meta.campaign_id.to_numpy()
        if cid.dtype.kind in "iu":
            order = np.argsort(cid)
            self._cid_sorted = cid[order].astype(np.int64)
            self._cid_order = order.astype(np.int32)
        else:
            self._cid_sorted = None
            self._cid_map = {
                str(c): i for i, c in enumerate(self.meta.campaign_id.tolist())
            }

    def _map_campaign_ids(self, values) -> np.ndarray:
        v = np.asarray(values)

        if self._cid_sorted is not None and v.dtype.kind in "iu":
            pos = np.searchsorted(self._cid_sorted, v.astype(np.int64))
            pos = np.clip(pos, 0, len(self._cid_sorted) - 1)
            bad = self._cid_sorted[pos] != v
            if bad.any():
                sys.exit(
                    f"{int(bad.sum()):,} rows reference a campaign_id that is not "
                    "in heaan_campaigns.csv — rows and campaigns are out of step"
                )
            return self._cid_order[pos]

        s = pd.Series(np.asarray(values).astype(str)).map(self._cid_map)
        if s.isna().any():
            sys.exit(
                f"{int(s.isna().sum()):,} rows reference a campaign_id that is not "
                "in heaan_campaigns.csv — rows and campaigns are out of step"
            )
        return s.to_numpy(dtype=np.int32)

    def _build_campaign_matrix(self):
        """One float32 row per campaign, holding every campaign-level feature."""
        present = [c for c in CAMPAIGN_NUMERIC if c in self.meta.columns]
        self.missing_campaign_columns = [
            c for c in CAMPAIGN_NUMERIC if c not in self.meta.columns
        ]

        num = self.meta[present].apply(pd.to_numeric, errors="coerce").fillna(-1)

        stage_dummies = pd.get_dummies(self.meta[CAMPAIGN_CATEGORICAL], columns=CAMPAIGN_CATEGORICAL)

        camp = pd.concat([num, stage_dummies], axis=1).astype(np.float32)

        self.campaign_columns = list(camp.columns)
        self.campaign_matrix = np.ascontiguousarray(camp.to_numpy(dtype=np.float32))

        self.columns = ROW_FEATURES + self.campaign_columns + (
            EXTRA_FEATURES if self.extra else []
        )

        # column offsets used by the extra features
        self._cpos = {name: i for i, name in enumerate(self.campaign_columns)}
        if self.extra:
            need = ["logDelta", "logQ", "logN", "logSlots"]
            miss = [c for c in need if c not in self._cpos]
            if miss:
                sys.exit(
                    "--extra-features needs these campaign columns: " + ", ".join(miss)
                )

    # -- row cache ---------------------------------------------------------

    def _stamp(self) -> dict:
        st = self.source.stat()
        return {
            "format": CACHE_FORMAT,
            "source": self.source.name,
            "size": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "n_campaigns": self.n_campaigns,
        }

    def _ensure_cache(self):
        manifest = self.cache_dir / "manifest.json"

        if manifest.exists():
            try:
                old = json.loads(manifest.read_text())
                if old.get("stamp") == self._stamp():
                    self.cache_info = old
                    return
            except Exception:
                pass

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        tmp = self.cache_dir.with_suffix(".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)

        print(f"building row cache from {self.source.name} (one time) ...", flush=True)
        t0 = time.time()
        self._has_truth = True

        if self.source is self.npz_path:
            n_rows, n_bad = self._fill_cache_from_npz(tmp)
        else:
            n_rows, n_bad = self._fill_cache_from_csv(tmp)

        if n_rows == 0:
            sys.exit("prepared rows are empty after filtering")

        info = {
            "stamp": self._stamp(),
            "n_rows": int(n_rows),
            "n_dropped_bad_rel_error": int(n_bad),
            "has_truth": bool(self._has_truth),
        }
        (tmp / "manifest.json").write_text(json.dumps(info, indent=2))
        tmp.rename(self.cache_dir)

        self.cache_info = info
        print(
            f"  cached {n_rows:,} rows in {time.time() - t0:.1f}s"
            + (f" ({n_bad:,} dropped: NaN or negative rel_error)" if n_bad else ""),
            flush=True,
        )

    def _write_block(self, handles, cidx, limb, coeff, bit, rel):
        handles["cidx"].write(np.ascontiguousarray(cidx, dtype=np.int32).tobytes())
        handles["limb"].write(np.ascontiguousarray(limb, dtype=np.int32).tobytes())
        handles["coeff"].write(np.ascontiguousarray(coeff, dtype=np.int32).tobytes())
        handles["bit"].write(np.ascontiguousarray(bit, dtype=np.int32).tobytes())
        handles["rel_error"].write(
            np.ascontiguousarray(rel, dtype=np.float32).tobytes()
        )

    def _fill_cache_from_csv(self, tmp: Path):
        n_rows = 0
        n_bad = 0

        handles = {k: open(tmp / f"{k}.bin", "wb") for k in CACHE_COLUMNS}
        try:
            for chunk in pd.read_csv(self.csv_path, chunksize=500_000):
                missing = [c for c in REQUIRED_ROW_COLUMNS if c not in chunk.columns]
                if missing:
                    sys.exit(
                        "prepared rows are missing required columns: "
                        + ", ".join(missing)
                    )

                if TRUTH_COLUMN in chunk.columns:
                    rel = pd.to_numeric(chunk[TRUTH_COLUMN], errors="coerce").to_numpy(
                        dtype=np.float64
                    )
                    good = ~np.isnan(rel) & (rel >= 0)
                else:
                    self._has_truth = False
                    rel = np.zeros(len(chunk), dtype=np.float64)
                    good = np.ones(len(chunk), dtype=bool)

                n_bad += int((~good).sum())
                if not good.any():
                    continue

                self._write_block(
                    handles,
                    self._map_campaign_ids(chunk.campaign_id.to_numpy()[good]),
                    chunk.limb.to_numpy()[good],
                    chunk.coeff.to_numpy()[good],
                    chunk.bit.to_numpy()[good],
                    rel[good],
                )
                n_rows += int(good.sum())
        finally:
            for f in handles.values():
                f.close()

        return n_rows, n_bad

    def _fill_cache_from_npz(self, tmp: Path):
        """Column-wise so at most one source column is in RAM at a time."""
        with np.load(self.npz_path, allow_pickle=True) as z:
            missing = [c for c in REQUIRED_ROW_COLUMNS if c not in z.files]
            if missing:
                sys.exit(
                    "prepared npz is missing required columns: " + ", ".join(missing)
                )

            if TRUTH_COLUMN in z.files:
                rel = np.asarray(z[TRUTH_COLUMN])
                good = ~np.isnan(rel) & (rel >= 0)
            else:
                self._has_truth = False
                n = len(np.asarray(z["campaign_id"]))
                rel = np.zeros(n, dtype=np.float32)
                good = np.ones(n, dtype=bool)
            n_bad = int((~good).sum())

            (tmp / "rel_error.bin").write_bytes(
                np.ascontiguousarray(rel[good], dtype=np.float32).tobytes()
            )
            n_rows = int(good.sum())
            del rel

            cidx = self._map_campaign_ids(np.asarray(z["campaign_id"])[good])
            (tmp / "cidx.bin").write_bytes(
                np.ascontiguousarray(cidx, dtype=np.int32).tobytes()
            )
            del cidx

            for key in ("limb", "coeff", "bit"):
                arr = np.asarray(z[key])[good]
                (tmp / f"{key}.bin").write_bytes(
                    np.ascontiguousarray(arr, dtype=np.int32).tobytes()
                )
                del arr

        return n_rows, n_bad

    def _open_cache(self):
        self.n_rows = int(self.cache_info["n_rows"])
        self.has_truth = bool(self.cache_info.get("has_truth", True))
        self.col = {}
        for name, dt in CACHE_COLUMNS.items():
            self.col[name] = np.memmap(
                self.cache_dir / f"{name}.bin",
                dtype=dt,
                mode="r",
                shape=(self.n_rows,),
            )

    # -- access ------------------------------------------------------------

    def labels(self, start: int, stop: int, correct_max, corrupted_max) -> np.ndarray:
        return labels_from_rel_error(
            self.col["rel_error"][start:stop], correct_max, corrupted_max
        )

    def features(self, idx: np.ndarray) -> np.ndarray:
        """Feature matrix for arbitrary row indices (must be sorted for speed)."""
        n = len(idx)
        X = np.empty((n, len(self.columns)), dtype=np.float32)

        bit = self.col["bit"][idx].astype(np.float32)
        coeff = self.col["coeff"][idx].astype(np.float32)

        X[:, 0] = bit
        X[:, 1] = coeff
        X[:, 2] = self.col["limb"][idx]

        k = len(ROW_FEATURES)
        camp = self.campaign_matrix[self.col["cidx"][idx]]
        X[:, k : k + camp.shape[1]] = camp

        if self.extra:
            j = k + camp.shape[1]
            log_delta = camp[:, self._cpos["logDelta"]]
            log_q = camp[:, self._cpos["logQ"]]
            log_n = camp[:, self._cpos["logN"]]
            log_slots = camp[:, self._cpos["logSlots"]]

            half = np.exp2(np.maximum(log_n - 1.0, 0.0))
            gaps = np.maximum(half / np.exp2(log_slots), 1.0)
            coeff_mod_gaps = np.mod(coeff, gaps)

            X[:, j + 0] = bit - log_delta
            X[:, j + 1] = bit - log_q
            X[:, j + 2] = coeff_mod_gaps
            X[:, j + 3] = coeff_mod_gaps == 0
            X[:, j + 4] = coeff >= half

            n_ops = np.zeros(n, dtype=np.float32)
            for c in ("doAdd", "doPlainMul", "doMul", "doRot"):
                if c in self._cpos:
                    n_ops += camp[:, self._cpos[c]]
            X[:, j + 5] = n_ops

        return X


# ---------------------------------------------------------------------------
# Folds
# ---------------------------------------------------------------------------

@dataclass
class Fold:
    """A fold is a rule for marking rows as test. Both kinds are cheap.

    campaign-level : held-out sites/stages, a lookup on the campaign index
    random         : a hash of the row position (in-distribution sanity check)
    """

    name: str
    test_campaigns: np.ndarray | None = None
    random_part: int | None = None

    def test_mask(self, ds: Dataset, start: int, stop: int) -> np.ndarray:
        if self.test_campaigns is not None:
            return self.test_campaigns[ds.col["cidx"][start:stop]]

        x = np.arange(start, stop, dtype=np.uint64)
        x ^= x >> np.uint64(30)
        x *= np.uint64(0xBF58476D1CE4E5B9)
        x ^= x >> np.uint64(27)
        x *= np.uint64(0x94D049BB133111EB)
        x ^= x >> np.uint64(31)
        return (x % np.uint64(5)) == np.uint64(self.random_part)


def build_folds(ds: Dataset, how: str, stages: list[str] | None):
    """Returns (split_name, allowed_campaigns_mask, folds)."""
    allowed = np.ones(ds.n_campaigns, dtype=bool)

    if stages:
        allowed &= np.isin(ds.stage, np.asarray(stages, dtype=object).astype(str))
        if not allowed.any():
            sys.exit(f"no campaigns for stages={stages}")

    if how == "random":
        return (
            "random 5-fold (in-distribution)",
            allowed,
            [Fold(f"fold {i + 1}", random_part=i) for i in range(5)],
        )

    if how == "stage":
        levels = sorted(set(ds.stage[allowed].tolist()))
        if len(levels) < 2:
            sys.exit(f"--split stage needs >=2 stages; found {levels}")
        return (
            "leave-one-stage-out",
            allowed,
            [Fold(s, test_campaigns=allowed & (ds.stage == s)) for s in levels],
        )

    # site and site-within-stage
    sites = sorted(set(ds.site[allowed].tolist()))

    if how == "site-within-stage":
        # A stage is usable only if it keeps >=2 distinct sites, so holding one
        # out never removes a whole stage from training.
        by_stage: dict[str, set] = {}
        for st, si in zip(ds.stage[allowed], ds.site[allowed]):
            by_stage.setdefault(st, set()).add(si)

        keep_stages = {s for s, v in by_stage.items() if len(v) >= 2}
        singletons = sorted(s for s, v in by_stage.items() if len(v) < 2)

        sites = sorted(s for s in sites if s.split("/", 1)[0] in keep_stages)

        if not sites:
            sys.exit(
                "--split site-within-stage found no stage with >=2 distinct "
                "sites; use --split site or --split random"
            )

        print(
            f"  site-within-stage: {len(sites)} eligible sites "
            f"from {len(keep_stages)} stages"
        )
        if singletons:
            print(
                "  singleton stages stay in training but are never held out: "
                + ", ".join(singletons)
            )

        name = "leave-one-site-out-within-known-stage"
    else:
        if len(sites) < 2:
            sys.exit(f"--split site needs >=2 sites; found {sites}")
        name = "leave-one-site-out"

    return (
        name,
        allowed,
        [Fold(s, test_campaigns=allowed & (ds.site == s)) for s in sites],
    )


def limit_folds(folds: list[Fold], max_folds: int) -> list[Fold]:
    if not max_folds or len(folds) <= max_folds:
        return folds
    keep = np.linspace(0, len(folds) - 1, max_folds).round().astype(int)
    return [folds[i] for i in sorted(set(keep.tolist()))]


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def sample_train_indices(
    ds: Dataset,
    allowed: np.ndarray,
    fold: Fold | None,
    cap: int,
    rng: np.random.Generator,
    block: int,
) -> tuple[np.ndarray, int]:
    """Exact uniform sample of the training rows, without replacement.

    Two passes over the block masks: count per block, then draw the per-block
    quota with a multivariate hypergeometric. That is exactly equivalent to
    sampling from the whole population, and never materialises an index array
    over all rows.
    """
    bounds = list(blocks(ds.n_rows, block))
    counts = np.zeros(len(bounds), dtype=np.int64)

    for i, (start, stop) in enumerate(bounds):
        m = allowed[ds.col["cidx"][start:stop]]
        if fold is not None:
            m &= ~fold.test_mask(ds, start, stop)
        counts[i] = int(m.sum())

    total = int(counts.sum())
    if total == 0:
        return np.empty(0, dtype=np.int64), 0

    if cap <= 0 or cap >= total:
        quota = counts
    else:
        quota = rng.multivariate_hypergeometric(counts, cap)

    out = []
    for i, (start, stop) in enumerate(bounds):
        if quota[i] == 0:
            continue
        m = allowed[ds.col["cidx"][start:stop]]
        if fold is not None:
            m &= ~fold.test_mask(ds, start, stop)
        idx = np.flatnonzero(m) + start
        if quota[i] < len(idx):
            idx = np.sort(rng.choice(idx, size=int(quota[i]), replace=False))
        out.append(idx)

    return np.concatenate(out), total


def training_set(ds, allowed, fold, cap, rng, block, correct_max, corrupted_max):
    idx, available = sample_train_indices(ds, allowed, fold, cap, rng, block)
    if len(idx) == 0:
        return None, None, available
    X = ds.features(idx)
    y = labels_from_rel_error(ds.col["rel_error"][idx], correct_max, corrupted_max)
    return X, y, available


# ---------------------------------------------------------------------------
# Metrics — computed straight from the confusion matrix
# ---------------------------------------------------------------------------

class Stats:
    def __init__(self):
        self.cm = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)

    def add(self, actual, predicted):
        a = np.asarray(actual, dtype=np.int64)
        p = np.asarray(predicted, dtype=np.int64)
        flat = np.bincount(a * N_CLASSES + p, minlength=N_CLASSES * N_CLASSES)
        self.cm += flat.reshape(N_CLASSES, N_CLASSES)

    def merge(self, other: "Stats"):
        self.cm += other.cm

    @property
    def n(self) -> int:
        return int(self.cm.sum())

    @property
    def accuracy(self) -> float:
        return float(np.trace(self.cm) / self.n) if self.n else float("nan")

    def per_class(self):
        tp = np.diag(self.cm).astype(float)
        support = self.cm.sum(axis=1).astype(float)
        predicted = self.cm.sum(axis=0).astype(float)

        with np.errstate(divide="ignore", invalid="ignore"):
            precision = np.where(predicted > 0, tp / predicted, 0.0)
            recall = np.where(support > 0, tp / support, 0.0)
            denom = precision + recall
            f1 = np.where(denom > 0, 2 * precision * recall / denom, 0.0)

        return precision, recall, f1, support

    @property
    def macro_f1(self) -> float:
        if not self.n:
            return float("nan")
        return float(self.per_class()[2].mean())

    @property
    def weighted_f1(self) -> float:
        if not self.n:
            return float("nan")
        _, _, f1, support = self.per_class()
        return float(np.average(f1, weights=support)) if support.sum() else 0.0

    def _sdc_counts(self):
        """correct -> not SDC; corrupted/failed -> SDC."""
        tn = float(self.cm[0, 0])
        fp = float(self.cm[0, 1:].sum())
        fn = float(self.cm[1:, 0].sum())
        tp = float(self.cm[1:, 1:].sum())
        return tn, fp, fn, tp

    @property
    def sdc_accuracy(self) -> float:
        if not self.n:
            return float("nan")
        tn, fp, fn, tp = self._sdc_counts()
        return (tn + tp) / (tn + fp + fn + tp)

    @property
    def sdc_f1(self) -> float:
        if not self.n:
            return float("nan")
        _, fp, fn, tp = self._sdc_counts()
        denom = 2 * tp + fp + fn
        return 2 * tp / denom if denom > 0 else 0.0

    def report(self) -> str:
        precision, recall, f1, support = self.per_class()
        lines = [f"  {'':<12}{'prec':>9}{'recall':>9}{'f1':>9}{'support':>12}"]
        for i, name in enumerate(CLASS_NAMES):
            lines.append(
                f"  {name:<12}{precision[i]:>9.4f}{recall[i]:>9.4f}"
                f"{f1[i]:>9.4f}{int(support[i]):>12,}"
            )
        lines.append(
            f"  {'macro avg':<12}{precision.mean():>9.4f}{recall.mean():>9.4f}"
            f"{f1.mean():>9.4f}{self.n:>12,}"
        )
        return "\n".join(lines)

    def confusion(self) -> str:
        return pd.DataFrame(
            self.cm,
            index=[f"actual {c}" for c in CLASS_NAMES],
            columns=[f"pred {c}" for c in CLASS_NAMES],
        ).to_string()


def score_fold(ds, allowed, fold, model, block, majority, correct_max, corrupted_max):
    stats = Stats()
    baseline_hits = 0

    for start, stop in blocks(ds.n_rows, block):
        m = fold.test_mask(ds, start, stop) & allowed[ds.col["cidx"][start:stop]]
        if not m.any():
            continue

        idx = np.flatnonzero(m) + start
        y = labels_from_rel_error(ds.col["rel_error"][idx], correct_max, corrupted_max)
        pred = model.predict(ds.features(idx)).astype(np.int8)

        stats.add(y, pred)
        baseline_hits += int(np.count_nonzero(y == majority))

    baseline = baseline_hits / stats.n if stats.n else float("nan")
    return stats, baseline


def print_distribution(y, prefix="  "):
    counts = np.bincount(np.asarray(y, dtype=np.int8), minlength=N_CLASSES)
    n = len(y)
    for i, name in enumerate(CLASS_NAMES):
        rate = counts[i] / n if n else 0.0
        print(f"{prefix}{name:<10}{int(counts[i]):>14,}{rate:>10.3%}")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def make_model(kind, depth, trees, min_leaf, class_weight, n_jobs):
    max_depth = None if depth <= 0 else depth
    min_leaf = 1 if min_leaf is None else min_leaf

    if kind == "forest":
        return RandomForestClassifier(
            n_estimators=trees,
            max_depth=max_depth,
            min_samples_leaf=min_leaf,
            class_weight=class_weight,
            random_state=0,
            n_jobs=n_jobs,
        )

    if kind == "hgb":
        kwargs = {"max_depth": max_depth, "random_state": 0}
        if class_weight is not None:
            kwargs["class_weight"] = class_weight
        return HistGradientBoostingClassifier(**kwargs)

    return DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=min_leaf,
        class_weight=class_weight,
        random_state=0,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    ap.add_argument("ml_dir", nargs="?", default=os.path.join(HERE, "ml"))

    ap.add_argument("--model", choices=["tree", "forest", "hgb"], default="tree")
    ap.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"max tree depth (default {DEFAULT_DEPTH}; 0 = unlimited)",
    )
    ap.add_argument("--trees", type=int, default=DEFAULT_TREES)
    ap.add_argument("--min-leaf", type=int, default=None, metavar="N")
    ap.add_argument(
        "--class-weight", choices=["none", "balanced"], default="none"
    )
    ap.add_argument("--n-jobs", type=int, default=-1)

    ap.add_argument(
        "--split",
        default="site-within-stage",
        choices=["site-within-stage", "site", "stage", "random"],
        help="cross-validation scheme (default: site-within-stage)",
    )
    ap.add_argument("--max-folds", type=int, default=0, metavar="N")
    ap.add_argument("--stages", nargs="+", default=None, metavar="S")

    ap.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE,
        metavar="N",
        help=(
            f"fit on at most N training rows per fold (default {DEFAULT_SAMPLE:,}; "
            "0 = every row), sampled uniformly without replacement"
        ),
    )
    ap.add_argument(
        "--block",
        type=int,
        default=DEFAULT_BLOCK,
        metavar="N",
        help=f"rows per scoring block (default {DEFAULT_BLOCK:,})",
    )

    ap.add_argument(
        "--extra-features",
        action="store_true",
        help="add the derived columns a tree cannot express: " + ", ".join(EXTRA_FEATURES),
    )
    ap.add_argument(
        "--correct-max", type=float, default=CORRECT_MAX, metavar="X"
    )
    ap.add_argument(
        "--corrupted-max", type=float, default=CORRUPTED_MAX, metavar="X"
    )

    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--save-model", default=None, metavar="PATH")

    args = ap.parse_args()

    if args.sample < 0:
        ap.error("--sample must be >= 0")
    if args.block <= 0:
        ap.error("--block must be > 0")
    if args.depth < 0:
        ap.error("--depth must be >= 0")
    if args.trees <= 0:
        ap.error("--trees must be > 0")
    if not (0 < args.correct_max < args.corrupted_max):
        ap.error("need 0 < --correct-max < --corrupted-max")

    class_weight = None if args.class_weight == "none" else "balanced"

    ds = Dataset(
        os.path.abspath(args.ml_dir),
        extra_features=args.extra_features,
        rebuild=args.rebuild_cache,
    )

    if not ds.has_truth:
        sys.exit(
            "the prepared rows have no rel_error column, so there is nothing to "
            "learn from — this dataset can only be scored by an already trained "
            "model (see predict_heaan.py)"
        )

    print(
        f"dataset: {ds.n_rows:,} rows · {ds.n_campaigns:,} campaigns · "
        f"{len(ds.columns)} features"
    )

    if ds.missing_campaign_columns:
        print(
            "  campaign columns absent from heaan_campaigns.csv (dropped): "
            + ", ".join(ds.missing_campaign_columns)
        )

    dropped_bad = int(ds.cache_info.get("n_dropped_bad_rel_error", 0))
    if dropped_bad:
        print(f"  {dropped_bad:,} rows dropped: NaN or negative rel_error")

    print(
        "target: 3-class severity  "
        f"correct <= {args.correct_max:g} < corrupted <= {args.corrupted_max:g} < failed"
    )
    print("SDC rule: correct -> is_sdc=0; corrupted/failed -> is_sdc=1")
    print(
        "features: RAW columns only"
        + (" + extra derived" if args.extra_features else "")
    )
    print(
        f"training cap: {args.sample:,} rows per fold"
        if args.sample
        else "training cap: none, every eligible row is used"
    )

    split_name, allowed, all_folds = build_folds(ds, args.split, args.stages)
    folds = limit_folds(all_folds, args.max_folds)

    print(
        f"split: {split_name} ({len(folds)} folds"
        + (f" of {len(all_folds)}" if len(folds) != len(all_folds) else "")
        + ")"
    )
    if args.split == "random":
        print(
            "  warning: random keeps sibling rows of the same injection site on "
            "both sides — treat the score as an upper bound"
        )

    pooled = Stats()
    pooled_base_hits = 0.0
    pooled_base_n = 0

    print()
    print(
        f"  {'held out':<28}{'train':>11}{'test':>12}{'base':>8}{'acc':>8}"
        f"{'macroF1':>10}{'SDCacc':>9}{'SDCF1':>9}{'secs':>8}",
        flush=True,
    )

    for i, fold in enumerate(folds, 1):
        t0 = time.time()
        rng = np.random.default_rng(1000 + i)

        X, y, _ = training_set(
            ds, allowed, fold, args.sample, rng, args.block,
            args.correct_max, args.corrupted_max,
        )

        if X is None:
            print(f"  {fold.name:<28}{0:>11}{0:>12}    (skipped: no train rows)")
            continue

        if len(np.unique(y)) < 2:
            only = CLASS_NAMES[int(y[0])]
            print(
                f"  {fold.name:<28}{len(y):>11,}{0:>12}    "
                f"(skipped: train has only class {only})"
            )
            continue

        model = make_model(
            args.model, args.depth, args.trees, args.min_leaf, class_weight, args.n_jobs
        )
        model.fit(X, y)

        majority = int(np.argmax(np.bincount(y, minlength=N_CLASSES)))
        n_fit = len(y)
        del X, y

        stats, base = score_fold(
            ds, allowed, fold, model, args.block, majority,
            args.correct_max, args.corrupted_max,
        )

        if stats.n == 0:
            print(f"  {fold.name:<28}{n_fit:>11,}{0:>12}    (skipped: no test rows)")
            continue

        pooled.merge(stats)
        pooled_base_hits += base * stats.n
        pooled_base_n += stats.n

        print(
            f"  {fold.name:<28}{n_fit:>11,}{stats.n:>12,}{base:>8.3f}"
            f"{stats.accuracy:>8.3f}{stats.macro_f1:>10.3f}"
            f"{stats.sdc_accuracy:>9.3f}{stats.sdc_f1:>9.3f}"
            f"{time.time() - t0:>8.1f}",
            flush=True,
        )
        del model

    if pooled.n == 0:
        sys.exit("every fold was skipped — nothing to report")

    baseline = pooled_base_hits / pooled_base_n if pooled_base_n else float("nan")

    print("\nPooled over folds")
    print(f"  rows         {pooled.n:,}")
    print(f"  base acc     {baseline:.4f}")
    print(f"  accuracy     {pooled.accuracy:.4f}")
    print(f"  macro F1     {pooled.macro_f1:.4f}")
    print(f"  weighted F1  {pooled.weighted_f1:.4f}")
    print(f"  SDC accuracy {pooled.sdc_accuracy:.4f}")
    print(f"  SDC F1       {pooled.sdc_f1:.4f}")

    print("\nPooled per class")
    print(pooled.report())

    print("\nPooled confusion matrix (rows=actual, cols=predicted)")
    print(pooled.confusion())

    # -- final fit ---------------------------------------------------------

    print("\nFinal fit ...", flush=True)

    X_all, y_all, n_available = training_set(
        ds, allowed, None, args.sample, np.random.default_rng(424242), args.block,
        args.correct_max, args.corrupted_max,
    )

    if X_all is None:
        sys.exit("no rows available for the final fit")

    print("\nFinal training sample class distribution")
    print_distribution(y_all)

    final = make_model(
        args.model, args.depth, args.trees, args.min_leaf, class_weight, args.n_jobs
    )
    final.fit(X_all, y_all)

    train_stats = Stats()
    train_stats.add(y_all, final.predict(X_all).astype(np.int8))

    print("\nFinal-fit score on its own training rows (optimistic — use the CV above)")
    print(f"  accuracy     {train_stats.accuracy:.4f}")
    print(f"  macro F1     {train_stats.macro_f1:.4f}")
    print(f"  SDC F1       {train_stats.sdc_f1:.4f}")

    if hasattr(final, "feature_importances_"):
        print("\nImportances (final fit):")
        ranked = sorted(
            zip(ds.columns, final.feature_importances_), key=lambda t: -t[1]
        )
        for name, imp in ranked:
            if imp > 0.001:
                print(f"  {name:<28}{imp:.3f}")

    if args.model == "tree" and 0 < args.depth <= 6:
        print("\nRules:")
        print(export_text(final, feature_names=ds.columns, class_names=CLASS_NAMES))

    if args.save_model:
        import joblib

        bundle = {
            "format": 6,
            "model": final,
            "columns": ds.columns,
            "classification": True,
            "target": "severity_class",
            "classes": CLASS_NAMES,
            "class_to_id": {n: i for i, n in enumerate(CLASS_NAMES)},
            "thresholds": {
                "correct_max": args.correct_max,
                "corrupted_max": args.corrupted_max,
            },
            "sdc_rule": {
                "correct_class_id": 0,
                "is_sdc": "predicted_class_id != 0",
                "rel_error_threshold": args.correct_max,
            },
            "feature_policy": {
                "row_features": ROW_FEATURES,
                "campaign_features": ds.campaign_columns,
                "extra_features": EXTRA_FEATURES if args.extra_features else [],
            },
            "train_stages": sorted(set(ds.stage[allowed].tolist())),
            "train_sites": sorted(set(ds.site[allowed].tolist())),
            "cv": {
                "split": split_name,
                "folds": len(folds),
                "rows_scored": int(pooled.n),
                "confusion_matrix": pooled.cm.tolist(),
                "accuracy": pooled.accuracy,
                "macro_f1": pooled.macro_f1,
                "weighted_f1": pooled.weighted_f1,
                "sdc_accuracy": pooled.sdc_accuracy,
                "sdc_f1": pooled.sdc_f1,
                "baseline_accuracy": baseline,
            },
            "provenance": {
                "dataset": os.path.abspath(args.ml_dir),
                "rows_total": int(ds.n_rows),
                "rows_available": int(n_available),
                "rows_fitted": int(len(y_all)),
                "model_kind": args.model,
                "depth": int(args.depth),
                "trees": int(args.trees),
                "min_leaf": None if args.min_leaf is None else int(args.min_leaf),
                "class_weight": args.class_weight,
                "sample": int(args.sample),
                "sampling_seed_final": 424242,
            },
        }

        out = os.path.abspath(args.save_model)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        joblib.dump(bundle, out)

        print(
            f"\nmodel saved to {out} "
            f"({len(ds.columns)} features, 3-class severity classifier)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
