#!/usr/bin/env python3
"""
Memory-bounded HEAAN training for one target only: rel_error.

Input produced by prepare_heaan_updated.py:
  - heaan_rows.npz or heaan_rows.csv.gz with
      campaign_id, limb, coeff, bit, rel_error
  - heaan_campaigns.csv with campaign configuration/features

The model is always a regressor and rel_error is always the target.
By default it is fitted in log1p(rel_error) space and predictions are converted
back with expm1.

No slot counters, severity classes, correct/degraded/corrupted/failed labels,
is_sdc, n_wrong, or alternative targets are used.

Training sampling is uniform over eligible rows using a streaming priority
reservoir. The default cap is 1,000,000 rows per fold. Use --sample 0 to train
on every eligible row.

Examples:
  python3 train_heaan_large_updated.py ml
  python3 train_heaan_large_updated.py ml --sample 1000000
  python3 train_heaan_large_updated.py ml --model tree --sample 1000000 \
      --chunk-size 200000 --max-folds 5 --save-model heaan.joblib
  python3 train_heaan_large_updated.py ml --split site --sample 500000
  python3 train_heaan_large_updated.py ml --model forest --trees 100 --sample 500000
"""

import argparse
import gc
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor, export_text

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TREES = 200
DEFAULT_DEPTH = 8
DEFAULT_TOL = 2.5
DEFAULT_CHUNK = 200_000
DEFAULT_SAMPLE = 1_000_000
DEFAULT_ERROR_SAMPLE = 200_000
IN_DISTRIBUTION = {"random", "seed", "coeff", "bit"}

DEPTH_NOTE = (
    "  note: depth {d} costs several levels isolating the site before it can split\n"
    "        on bit. For in-distribution splits, consider --depth 16."
)

# Model inputs. rel_error is deliberately absent: it is the target.
NUMERIC = [
    "bit", "rel_bit", "bit_minus_logq", "bit_ge_logq",
    "coeff", "coeff_mod_gaps", "is_slot", "coeff_ge_half", "is_N2_coeff",
    "op_step", "op_depth", "limb",
    "n_add", "n_plainmul", "n_mul", "n_rot", "n_ops", "does_boot",
    "logN", "logQ", "logDelta", "logSlots", "n", "gaps",
    "dnum", "withNTT", "mult_depth", "isComplex", "bitPerCoeff",
]

# stage is an injection/pipeline descriptor, not an outcome severity category.
CATEGORICAL = ["stage"]

RAW_FEATURES = {
    "bit", "coeff", "op_step", "op_depth", "limb",
    "logN", "logQ", "logDelta", "logSlots",
    "dnum", "withNTT", "mult_depth", "isComplex", "bitPerCoeff",
    "doAdd", "doPlainMul", "doMul", "doRot", "doBoot", "stage",
}
RAW_TARGET = {"rel_error"}
RAW_GROUPING = {"seed", "seed_input"}
PROJECTED = RAW_FEATURES | RAW_TARGET | RAW_GROUPING


def to_log(y):
    return np.log1p(np.asarray(y, dtype=float))


def from_log(y):
    return np.clip(np.expm1(np.asarray(y, dtype=float)), 0.0, None)


def within_tol(actual, pred, tol: float) -> np.ndarray:
    """Percentage band; for an exact zero, use tol/100 as absolute tolerance."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(pred, dtype=float)
    band = np.abs(a) * (tol / 100.0)
    band = np.where(a == 0, tol / 100.0, band)
    return np.abs(p - a) <= band


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic engineered features from injection/campaign inputs."""
    df = df.copy()

    required = ["logN", "logDelta", "logQ", "logSlots", "bit", "coeff"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns needed to derive features: {missing}")

    df["n"] = np.left_shift(1, df.logN.astype(int))
    df["rel_bit"] = df.bit - df.logDelta
    df["bit_minus_logq"] = df.bit - df.logQ
    df["bit_ge_logq"] = (df.bit >= df.logQ).astype(np.int8)

    slots = np.left_shift(1, df.logSlots.astype(int))
    gaps = ((df.n // 2) // slots).clip(lower=1)
    df["gaps"] = gaps
    df["coeff_mod_gaps"] = df.coeff % gaps
    df["is_slot"] = (df.coeff_mod_gaps == 0).astype(np.int8)
    df["coeff_ge_half"] = (df.coeff >= df.n // 2).astype(np.int8)
    df["is_N2_coeff"] = (df.coeff == df.n // 2).astype(np.int8)

    df["n_add"] = df["doAdd"] if "doAdd" in df.columns else 0
    df["n_plainmul"] = df["doPlainMul"] if "doPlainMul" in df.columns else 0
    df["n_mul"] = df["doMul"] if "doMul" in df.columns else 0
    df["n_rot"] = df["doRot"] if "doRot" in df.columns else 0
    df["n_ops"] = df.n_add + df.n_plainmul + df.n_mul + df.n_rot
    df["does_boot"] = df["doBoot"].astype(np.int8) if "doBoot" in df.columns else 0
    return df


def make_target(df: pd.DataFrame) -> pd.Series:
    if "rel_error" not in df.columns:
        raise ValueError("prepared rows have no rel_error column")

    y = pd.to_numeric(df.rel_error, errors="coerce")
    if y.isna().any():
        raise ValueError(
            f"rel_error contains {int(y.isna().sum()):,} NaN/non-numeric values"
        )
    if (y < 0).any():
        raise ValueError(
            f"rel_error contains {int((y < 0).sum()):,} negative values"
        )
    return y.astype(float)


def build_features(
    df: pd.DataFrame,
    columns=None,
) -> tuple[pd.DataFrame, list[str]]:
    num = [c for c in NUMERIC if c in df.columns]
    cat = [c for c in CATEGORICAL if c in df.columns]

    dropped = []
    if columns is None:
        dropped = [c for c in num + cat if df[c].nunique(dropna=False) <= 1]
        num = [c for c in num if c not in dropped]
        cat = [c for c in cat if c not in dropped]

    X = df[num].apply(pd.to_numeric, errors="coerce").fillna(-1)
    if cat:
        X = pd.concat([X, pd.get_dummies(df[cat], columns=cat)], axis=1)

    X = X.astype(np.float32)

    if columns is not None:
        X = X.reindex(columns=columns, fill_value=np.float32(0))

    return X, dropped


def make_model(kind: str, depth: int, trees: int, min_leaf: int | None):
    min_leaf = 1 if min_leaf is None else min_leaf

    if kind == "forest":
        return RandomForestRegressor(
            n_estimators=trees,
            min_samples_leaf=min_leaf,
            random_state=0,
            n_jobs=-1,
        )

    if kind == "hgb":
        return HistGradientBoostingRegressor(random_state=0)

    return DecisionTreeRegressor(
        max_depth=depth,
        min_samples_leaf=min_leaf,
        random_state=0,
    )


def _safe_unlink(path: Path):
    try:
        path.unlink()
    except FileNotFoundError:
        pass


class RowSource:
    """Chunked access to prepared rows plus campaign metadata."""

    def __init__(
        self,
        ml_dir: str,
        chunk_size: int,
        stages: list[str] | None,
    ):
        self.ml_dir = Path(ml_dir)
        self.chunk_size = int(chunk_size)
        self.meta_path = self.ml_dir / "heaan_campaigns.csv"
        self.csv_path = self.ml_dir / "heaan_rows.csv.gz"
        self.npz_path = self.ml_dir / "heaan_rows.npz"
        self.cache_dir = self.ml_dir / ".heaan_rows_npy"

        if not self.meta_path.exists():
            sys.exit(f"no heaan_campaigns.csv under {self.ml_dir}")
        if not self.csv_path.exists() and not self.npz_path.exists():
            sys.exit(
                f"no heaan_rows.csv.gz or heaan_rows.npz under {self.ml_dir}"
            )

        self.meta_all = pd.read_csv(self.meta_path)
        self.meta = self.meta_all

        if "campaign_id" not in self.meta.columns:
            sys.exit("heaan_campaigns.csv has no campaign_id column")

        required_meta = {
            "campaign_id", "stage", "op_step", "op_depth",
            "logN", "logQ", "logDelta", "logSlots",
        }
        missing_meta = sorted(required_meta - set(self.meta.columns))
        if missing_meta:
            sys.exit(
                "heaan_campaigns.csv is missing required model metadata: "
                + ", ".join(missing_meta)
            )

        if stages:
            self.meta = self.meta[self.meta.stage.isin(stages)].copy()
            if self.meta.empty:
                sys.exit(f"no campaigns for stages={stages}")

        self.allowed_campaigns = set(self.meta.campaign_id.tolist())

        self.mode = "csv" if self.csv_path.exists() else "npz"
        if self.mode == "npz":
            self._ensure_npy_cache()
            self._open_memmaps()
            self.n_rows_total = (
                len(next(iter(self._maps.values()))) if self._maps else 0
            )
        else:
            self.n_rows_total = None

        self.n_rows_est = (
            self.n_rows_total
            if self.n_rows_total is not None and not stages
            else None
        )

    def _ensure_npy_cache(self):
        manifest = self.cache_dir / "manifest.json"
        stamp = {
            "npz_size": self.npz_path.stat().st_size,
            "npz_mtime_ns": self.npz_path.stat().st_mtime_ns,
        }

        if manifest.exists():
            try:
                old = json.loads(manifest.read_text())
                if old.get("source") == stamp:
                    return
            except Exception:
                pass

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        print(
            f"building one-time mmap cache from {self.npz_path.name} ...",
            flush=True,
        )

        with np.load(self.npz_path, allow_pickle=True) as z:
            for i, key in enumerate(z.files, 1):
                if key.startswith("_"):
                    continue

                arr = z[key]
                if arr.dtype == object:
                    ser = pd.Series(arr).infer_objects()
                    if ser.dtype == object:
                        arr = np.asarray(ser.fillna("").tolist(), dtype=str)
                    else:
                        arr = ser.to_numpy()

                np.save(
                    self.cache_dir / f"{key}.npy",
                    arr,
                    allow_pickle=False,
                )
                print(f"  cached {i:>2}/{len(z.files)}  {key}", flush=True)
                del arr
                gc.collect()

        manifest.write_text(json.dumps({"source": stamp}, indent=2))

    def _open_memmaps(self):
        self._maps = {}
        for path in sorted(self.cache_dir.glob("*.npy")):
            if path.name.startswith("_"):
                continue
            self._maps[path.stem] = np.load(
                path,
                mmap_mode="r",
                allow_pickle=False,
            )

        if not self._maps:
            sys.exit(f"empty npy cache at {self.cache_dir}")

        required = {"campaign_id", "limb", "coeff", "bit", "rel_error"}
        missing = sorted(required - set(self._maps))
        if missing:
            sys.exit(f"prepared npz is missing required columns: {missing}")

    def _join_meta(self, rows: pd.DataFrame) -> pd.DataFrame:
        rows = rows[rows.campaign_id.isin(self.allowed_campaigns)]
        if rows.empty:
            return rows

        df = rows.merge(
            self.meta,
            on="campaign_id",
            how="left",
            suffixes=("", "_meta"),
        )

        if "stage" not in df.columns or df.stage.isna().any():
            bad = (
                len(df)
                if "stage" not in df.columns
                else int(df.stage.isna().sum())
            )
            sys.exit(
                f"{bad:,} streamed rows have no campaign metadata — "
                "heaan_rows and heaan_campaigns are out of step"
            )

        return df

    def iter_chunks(self) -> Iterable[pd.DataFrame]:
        if self.mode == "csv":
            start = 0
            for rows in pd.read_csv(
                self.csv_path,
                chunksize=self.chunk_size,
            ):
                n = len(rows)
                rows["_rowid"] = np.arange(
                    start,
                    start + n,
                    dtype=np.int64,
                )
                start += n

                required = {"campaign_id", "limb", "coeff", "bit", "rel_error"}
                missing = sorted(required - set(rows.columns))
                if missing:
                    sys.exit(
                        f"prepared CSV is missing required columns: {missing}"
                    )

                df = self._join_meta(rows)
                if not df.empty:
                    yield df.reset_index(drop=True)

            self.n_rows_total = start
            return

        n = self.n_rows_total
        keys = list(self._maps)

        for start in range(0, n, self.chunk_size):
            stop = min(start + self.chunk_size, n)
            data = {
                k: np.asarray(self._maps[k][start:stop])
                for k in keys
            }
            rows = pd.DataFrame(data)
            rows["_rowid"] = np.arange(start, stop, dtype=np.int64)
            df = self._join_meta(rows)
            if not df.empty:
                yield df.reset_index(drop=True)


@dataclass(frozen=True)
class Fold:
    kind: str
    value: object
    name: str

    def test_mask(self, df: pd.DataFrame) -> np.ndarray:
        if self.kind == "site":
            return (site_series(df) == self.value).to_numpy()

        if self.kind == "stage":
            return (df.stage.astype(str) == str(self.value)).to_numpy()

        if self.kind == "seed":
            col, value = self.value
            return (df[col] == value).to_numpy()

        if self.kind in ("coeff", "bit"):
            return df[self.kind].isin(self.value).to_numpy()

        if self.kind == "random":
            x = df._rowid.to_numpy(dtype=np.uint64)
            x ^= x >> np.uint64(30)
            x *= np.uint64(0xBF58476D1CE4E5B9)
            x ^= x >> np.uint64(27)
            x *= np.uint64(0x94D049BB133111EB)
            x ^= x >> np.uint64(31)
            return (
                x % np.uint64(5) == np.uint64(self.value)
            ).astype(bool)

        raise ValueError(self.kind)


def site_series(df: pd.DataFrame) -> pd.Series:
    return (
        df.stage.astype(str)
        + "/" + df.op_step.astype(str)
        + "@" + df.op_depth.astype(str)
    )


def discover_group_values(source: RowSource, col: str) -> list:
    values = set()
    for chunk in source.iter_chunks():
        values.update(pd.unique(chunk[col]).tolist())
    return sorted(values)


def choose_folds(source: RowSource, how: str) -> tuple[str, list[Fold]]:
    meta = source.meta
    meta_sites = site_series(meta)

    if how == "auto":
        how = "site" if meta_sites.nunique() > 1 else "coeff"

    if how == "site":
        levels = sorted(meta_sites.unique())
        if len(levels) < 2:
            sys.exit(f"--split site needs >=2 sites; found {levels}")
        return (
            "leave-one-site-out",
            [Fold("site", x, str(x)) for x in levels],
        )

    if how == "stage":
        levels = sorted(meta.stage.astype(str).unique())
        if len(levels) < 2:
            sys.exit(f"--split stage needs >=2 stages; found {levels}")
        return (
            "leave-one-stage-out",
            [Fold("stage", x, str(x)) for x in levels],
        )

    if how == "seed":
        seed_col = next(
            (c for c in ("seed", "seed_input") if c in meta.columns),
            None,
        )
        if seed_col is None:
            sys.exit(
                "--split seed needs a seed or seed_input column "
                "in heaan_campaigns.csv"
            )

        levels = sorted(meta[seed_col].unique())
        if len(levels) < 2:
            sys.exit(f"--split seed needs >=2 levels; found {levels}")

        return (
            f"leave-one-{seed_col}-out",
            [
                Fold("seed", (seed_col, x), f"{seed_col} {x}")
                for x in levels
            ],
        )

    if how in ("coeff", "bit"):
        levels = discover_group_values(source, how)
        if len(levels) < 2:
            sys.exit(f"--split {how} needs >=2 values; found {levels}")

        rng = np.random.default_rng(0)
        folds = []
        n_test = max(1, int(np.ceil(0.25 * len(levels))))
        arr = np.asarray(levels)

        for i in range(5):
            chosen = set(
                rng.choice(
                    arr,
                    size=n_test,
                    replace=False,
                ).tolist()
            )
            folds.append(
                Fold(how, frozenset(chosen), f"split {i + 1}")
            )

        return f"leave-{how}s-out", folds

    if how == "random":
        return (
            "random 5-fold",
            [Fold("random", i, f"fold {i + 1}") for i in range(5)],
        )

    raise ValueError(how)


def evenly_limit_folds(folds: list[Fold], max_folds: int) -> list[Fold]:
    if not max_folds or len(folds) <= max_folds:
        return folds

    keep = np.linspace(
        0,
        len(folds) - 1,
        max_folds,
    ).round().astype(int)

    return [folds[i] for i in sorted(set(keep.tolist()))]


def project(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only explicitly approved model inputs/grouping variables plus target.

    This is a second safety boundary after prepare_heaan_updated.py. Even if an
    unexpected column appears in metadata, it cannot become a model feature
    unless it is explicitly listed in PROJECTED/NUMERIC/CATEGORICAL.
    """
    cols = [c for c in df.columns if c in PROJECTED]
    return df[cols]


class PriorityReservoir:
    """
    Exact uniform sample without replacement using random priorities.

    Every eligible training row receives one iid random priority. Keeping the N
    smallest priorities gives every row the same probability of inclusion,
    regardless of input ordering.
    """

    def __init__(
        self,
        capacity: int,
        rng: np.random.Generator,
    ):
        self.capacity = int(capacity)
        self.rng = rng
        self.df = None

    def add(self, df: pd.DataFrame):
        if df.empty:
            return

        part = project(df).copy()
        part["_priority"] = self.rng.random(len(part))

        if self.capacity and len(part) > self.capacity:
            idx = np.argpartition(
                part._priority.to_numpy(),
                self.capacity - 1,
            )[:self.capacity]
            part = part.iloc[idx]

        if self.df is None:
            self.df = part.reset_index(drop=True)
        else:
            self.df = pd.concat(
                [self.df, part],
                ignore_index=True,
            )

        if self.capacity and len(self.df) > self.capacity:
            p = self.df._priority.to_numpy()
            idx = np.argpartition(
                p,
                self.capacity - 1,
            )[:self.capacity]
            self.df = self.df.iloc[idx].reset_index(drop=True)

    def result(self) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()
        return self.df.drop(columns="_priority").reset_index(drop=True)


def collect_train(
    source: RowSource,
    fold: Fold | None,
    sample: int,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, int]:
    if sample > 0:
        res = PriorityReservoir(sample, rng)
        n_seen = 0

        for chunk in source.iter_chunks():
            mask = (
                np.zeros(len(chunk), dtype=bool)
                if fold is None
                else fold.test_mask(chunk)
            )
            train = chunk.loc[~mask]
            n_seen += len(train)
            res.add(train)

        return res.result(), n_seen

    # --sample 0 explicitly disables sampling and materialises every training row.
    frames = []
    n_seen = 0

    for chunk in source.iter_chunks():
        mask = (
            np.zeros(len(chunk), dtype=bool)
            if fold is None
            else fold.test_mask(chunk)
        )
        train = project(chunk.loc[~mask])
        n_seen += len(train)
        if not train.empty:
            frames.append(train)

    if not frames:
        return pd.DataFrame(), n_seen

    return pd.concat(frames, ignore_index=True), n_seen


class FloatReservoir:
    """Bounded uniform sample for approximate percentile reporting."""

    def __init__(self, capacity: int, seed: int):
        self.capacity = int(capacity)
        self.rng = np.random.default_rng(seed)
        self.values = np.empty(0, dtype=np.float64)
        self.keys = np.empty(0, dtype=np.float64)
        self.seen = 0

    def add(self, values):
        x = np.asarray(values, dtype=np.float64).ravel()
        if len(x) == 0:
            return

        original_n = len(x)
        keys = self.rng.random(len(x))

        if len(x) > self.capacity:
            idx = np.argpartition(
                keys,
                self.capacity - 1,
            )[:self.capacity]
            x, keys = x[idx], keys[idx]

        vals = np.concatenate([self.values, x])
        ks = np.concatenate([self.keys, keys])

        if len(vals) > self.capacity:
            idx = np.argpartition(
                ks,
                self.capacity - 1,
            )[:self.capacity]
            vals, ks = vals[idx], ks[idx]

        self.values, self.keys = vals, ks
        self.seen += original_n


class RegressionStats:
    def __init__(
        self,
        tol: float,
        error_sample: int,
        seed: int,
    ):
        self.tol = tol
        self.n = 0
        self.sum_y = 0.0
        self.sum_y2 = 0.0
        self.sse = 0.0
        self.sae = 0.0
        self.within_hits = 0
        self.max_err = 0.0
        self.errors = FloatReservoir(error_sample, seed)

        self.log_n = 0
        self.sum_la = 0.0
        self.sum_la2 = 0.0
        self.log_sse = 0.0
        self.log_sae = 0.0

    def add(self, actual, pred):
        a = np.asarray(actual, dtype=np.float64)
        p = np.asarray(pred, dtype=np.float64)

        err = p - a
        ae = np.abs(err)

        self.n += len(a)
        self.sum_y += float(a.sum())
        self.sum_y2 += float(np.dot(a, a))
        self.sse += float(np.dot(err, err))
        self.sae += float(ae.sum())
        self.within_hits += int(within_tol(a, p, self.tol).sum())

        if len(ae):
            self.max_err = max(self.max_err, float(ae.max()))

        self.errors.add(ae)

        la = np.log10(1 + a)
        lp = np.log10(1 + p)
        le = lp - la

        self.log_n += len(a)
        self.sum_la += float(la.sum())
        self.sum_la2 += float(np.dot(la, la))
        self.log_sse += float(np.dot(le, le))
        self.log_sae += float(np.abs(le).sum())

    @property
    def mae(self):
        return self.sae / self.n if self.n else float("nan")

    @property
    def within_rate(self):
        return (
            self.within_hits / self.n
            if self.n
            else float("nan")
        )

    @property
    def r2(self):
        if not self.n:
            return float("nan")

        sst = self.sum_y2 - self.sum_y * self.sum_y / self.n
        return 1.0 - self.sse / sst if sst > 0 else float("nan")

    @property
    def log_r2(self):
        if not self.log_n:
            return float("nan")

        sst = self.sum_la2 - self.sum_la * self.sum_la / self.log_n
        return 1.0 - self.log_sse / sst if sst > 0 else float("nan")

    @property
    def log_mae(self):
        return (
            self.log_sae / self.log_n
            if self.log_n
            else float("nan")
        )

    def merge(self, other: "RegressionStats"):
        self.n += other.n
        self.sum_y += other.sum_y
        self.sum_y2 += other.sum_y2
        self.sse += other.sse
        self.sae += other.sae
        self.within_hits += other.within_hits
        self.max_err = max(self.max_err, other.max_err)
        self.errors.add(other.errors.values)

        self.log_n += other.log_n
        self.sum_la += other.sum_la
        self.sum_la2 += other.sum_la2
        self.log_sse += other.log_sse
        self.log_sae += other.log_sae


def score_regression(
    source: RowSource,
    fold: Fold,
    model,
    columns,
    log_fit: bool,
    tol: float,
    train_median: float,
    seed: int,
):
    stats = RegressionStats(
        tol,
        DEFAULT_ERROR_SAMPLE,
        seed,
    )
    base_hits = 0
    base_n = 0

    for chunk in source.iter_chunks():
        te = fold.test_mask(chunk)
        if not te.any():
            continue

        test = derive(project(chunk.loc[te]))
        y = make_target(test).to_numpy(dtype=float)
        X, _ = build_features(test, columns=columns)

        p = model.predict(X)
        if log_fit:
            p = from_log(p)

        stats.add(y, p)

        base_hits += int(
            within_tol(
                y,
                np.full(len(y), train_median),
                tol,
            ).sum()
        )
        base_n += len(y)

    baseline = (
        base_hits / base_n
        if base_n
        else float("nan")
    )

    return stats, baseline


def describe_training_sample(df: pd.DataFrame):
    y = make_target(derive(df))
    print(
        f"        sampled train rel_error: min {y.min():.4g}  "
        f"median {y.median():.4g}  max {y.max():.4g}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "ml_dir",
        nargs="?",
        default=os.path.join(HERE, "ml"),
    )
    ap.add_argument(
        "--model",
        choices=["tree", "forest", "hgb"],
        default="tree",
    )
    ap.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    ap.add_argument("--trees", type=int, default=DEFAULT_TREES)
    ap.add_argument("--min-leaf", type=int, default=None, metavar="N")
    ap.add_argument(
        "--split",
        default="auto",
        choices=["auto", "site", "stage", "seed", "coeff", "bit", "random"],
    )
    ap.add_argument("--max-folds", type=int, default=0, metavar="N")
    ap.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE,
        metavar="N",
        help=(
            "fit on at most N TRAIN rows per fold using exact uniform "
            f"streaming sampling (default: {DEFAULT_SAMPLE:,}); "
            "use 0 to fit all rows"
        ),
    )
    ap.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK,
        metavar="N",
    )
    ap.add_argument("--stages", nargs="+", default=None, metavar="S")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL, metavar="T")
    ap.add_argument(
        "--log-target",
        dest="log_target",
        action="store_true",
        default=True,
        help="fit log1p(rel_error) (default)",
    )
    ap.add_argument(
        "--no-log-target",
        dest="log_target",
        action="store_false",
        help="fit rel_error directly",
    )
    ap.add_argument("--save-model", default=None, metavar="PATH")
    args = ap.parse_args()

    if args.sample < 0:
        ap.error("--sample must be >= 0")
    if args.chunk_size <= 0:
        ap.error("--chunk-size must be > 0")
    if args.depth <= 0:
        ap.error("--depth must be > 0")
    if args.trees <= 0:
        ap.error("--trees must be > 0")

    source = RowSource(
        os.path.abspath(args.ml_dir),
        args.chunk_size,
        args.stages,
    )
    log_fit = bool(args.log_target)

    print(
        f"source: {source.mode} · chunk {args.chunk_size:,} rows"
        + (
            f" · ~{source.n_rows_est:,} rows"
            if source.n_rows_est is not None
            else ""
        )
    )
    print(
        f"target: rel_error "
        f"({'regression, log1p fit' if log_fit else 'regression, direct fit'})"
    )

    if args.sample:
        print(
            f"training cap: {args.sample:,} rows per fold "
            "(uniform streaming sample without replacement)"
        )
    else:
        print(
            "training sampling disabled: every eligible training row will be used"
        )

    split_name, all_folds = choose_folds(source, args.split)
    folds = evenly_limit_folds(all_folds, args.max_folds)

    print(
        f"Split: {split_name} ({len(folds)} folds"
        + (
            f" of {len(all_folds)}"
            if len(folds) != len(all_folds)
            else ""
        )
        + ")"
    )

    if args.split == "random":
        print(
            "  warning: random split leaves sibling rows from the same "
            "injection site on both sides"
        )

    if (
        args.model == "tree"
        and args.depth < 12
        and args.split in IN_DISTRIBUTION
    ):
        print(DEPTH_NOTE.format(d=args.depth))

    pooled = RegressionStats(
        args.tol,
        DEFAULT_ERROR_SAMPLE,
        991,
    )
    pooled_base_hits = 0.0
    pooled_base_weight = 0

    print()
    print(
        f"  {'held out':<24}"
        f"{'train':>11}"
        f"{'test':>11}"
        f"{'base':>8}"
        f"{'within':>8}"
        f"{'MAE':>12}"
        f"{'secs':>8}",
        flush=True,
    )

    for fold_i, fold in enumerate(folds, 1):
        t0 = time.time()

        # Independent deterministic RNG per fold. This keeps each fold sample
        # uniform and makes it independent of which other folds were executed.
        fold_rng = np.random.default_rng(1000 + fold_i)

        train_raw, _n_train_available = collect_train(
            source,
            fold,
            args.sample,
            fold_rng,
        )

        if train_raw.empty:
            print(
                f"  {fold.name:<24}{0:>11}{0:>11}    "
                "(skipped: no train rows)"
            )
            continue

        train = derive(train_raw)
        y_train = make_target(train)

        if y_train.nunique() < 2:
            print(
                f"  {fold.name:<24}{len(train):>11,}{0:>11}    "
                "(skipped: constant rel_error)"
            )
            continue

        X_train, dropped = build_features(train)
        model = make_model(
            args.model,
            args.depth,
            args.trees,
            args.min_leaf,
        )
        model.fit(
            X_train,
            to_log(y_train) if log_fit else y_train,
        )

        columns = list(X_train.columns)
        n_fit = len(train)
        train_median = float(y_train.median())

        del train_raw, train, X_train
        gc.collect()

        stats, base = score_regression(
            source,
            fold,
            model,
            columns,
            log_fit,
            args.tol,
            train_median,
            10_000 + fold_i,
        )

        test_n = stats.n
        if test_n == 0:
            print(
                f"  {fold.name:<24}{n_fit:>11,}{0:>11}    "
                "(skipped: no test rows)"
            )
            continue

        pooled.merge(stats)
        pooled_base_hits += base * test_n
        pooled_base_weight += test_n

        print(
            f"  {fold.name:<24}"
            f"{n_fit:>11,}"
            f"{test_n:>11,}"
            f"{base:>8.3f}"
            f"{stats.within_rate:>8.3f}"
            f"{stats.mae:>12.4g}"
            f"{time.time() - t0:>8.1f}",
            flush=True,
        )

        if dropped:
            print(
                "    dropped constant train features: "
                + ", ".join(dropped)
            )

        del model, y_train
        gc.collect()

    if pooled.n == 0:
        sys.exit("every fold was skipped — nothing to report")

    baseline = (
        pooled_base_hits / pooled_base_weight
        if pooled_base_weight
        else float("nan")
    )

    print(
        f"\nPooled over folds: within_tol_rate {pooled.within_rate:.3f} "
        f"(±{args.tol}%)  MAE {pooled.mae:.4g}  R2 {pooled.r2:.3f}  "
        f"(median-baseline within_tol_rate {baseline:.3f})"
    )
    print(
        f"In log10(1+rel_error) space: "
        f"MAE {pooled.log_mae:.3f} decades  R2 {pooled.log_r2:.3f}"
    )

    if len(pooled.errors.values):
        qs = np.percentile(
            pooled.errors.values,
            [50, 90, 99],
        )
        approx = (
            "approx. "
            if pooled.errors.seen > len(pooled.errors.values)
            else ""
        )
        print(
            f"Absolute error: {approx}median {qs[0]:.4g}  "
            f"p90 {qs[1]:.4g}  p99 {qs[2]:.4g}  "
            f"max {pooled.max_err:.4g}"
        )

    print("\nFinal fit ...", flush=True)

    # Independent fixed RNG for the final fit. Therefore the final training
    # sample does not change when --split or --max-folds changes.
    final_rng = np.random.default_rng(424242)

    final_raw, n_final_available = collect_train(
        source,
        None,
        args.sample,
        final_rng,
    )

    if final_raw.empty:
        sys.exit("no rows available for final fit")

    describe_training_sample(final_raw)

    final_df = derive(final_raw)
    y_all = make_target(final_df)
    X_all, dropped = build_features(final_df)

    final = make_model(
        args.model,
        args.depth,
        args.trees,
        args.min_leaf,
    )
    final.fit(
        X_all,
        to_log(y_all) if log_fit else y_all,
    )

    if dropped:
        print(
            "dropped constant final-fit features: "
            + ", ".join(dropped)
        )

    if hasattr(final, "feature_importances_"):
        print("\nImportances (final fit):")
        for name, imp in sorted(
            zip(X_all.columns, final.feature_importances_),
            key=lambda t: -t[1],
        ):
            if imp > 0.001:
                print(f"  {name:24s} {imp:.3f}")

    if args.model == "tree" and args.depth <= 6:
        print("\nRules:")
        print(
            export_text(
                final,
                feature_names=list(X_all.columns),
            )
        )

    if args.save_model:
        import joblib

        bundle = {
            "format": 4,
            "model": final,
            "columns": list(X_all.columns),
            "regression": True,
            "target": "rel_error",
            "transform": "log1p" if log_fit else "identity",
            "train_stages": sorted(
                source.meta.stage.astype(str).unique().tolist()
            ),
            "train_sites": sorted(
                set(site_series(source.meta).tolist())
            ),
            "scoring": {
                "tol_percent": args.tol,
                "metric_name": "within_tol_rate",
            },
            "provenance": {
                "dataset": os.path.abspath(args.ml_dir),
                "rows_available": int(n_final_available),
                "rows_fitted": int(len(final_df)),
                "model_kind": args.model,
                "depth": args.depth,
                "trees": args.trees,
                "split": split_name,
                "streaming": True,
                "uniform_sampling": bool(args.sample > 0),
                "chunk_size": int(args.chunk_size),
                "sample": int(args.sample),
                "sampling_seed_final": 424242,
            },
        }

        out = os.path.abspath(args.save_model)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        joblib.dump(bundle, out)

        print(
            f"\nmodel saved to {out} "
            f"({len(bundle['columns'])} features, rel_error regression)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
