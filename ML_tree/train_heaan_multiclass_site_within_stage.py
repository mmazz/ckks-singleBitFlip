#!/usr/bin/env python3
"""
Clasificador de severidad HEAAN (3 clases derivadas de rel_error).

    correct    : rel_error <= 0.1
    corrupted  : 0.1 < rel_error <= 10.0
    failed     : rel_error > 10.0

Entrada, bajo ml_dir (la misma que produce prepare_heaan.py):
  - heaan_rows.npz  o  heaan_rows.csv.gz   con campaign_id, limb, coeff, bit,
    rel_error   (una fila por fault inyectado)
  - heaan_campaigns.csv                    con una fila por campaña

rel_error se usa SOLO para construir la etiqueta. Nunca es input del modelo.


QUE CAMBIO RESPECTO DE LA VERSION ANTERIOR
==========================================

1. --split config  (leave-one-config-out).
   Los splits por site/stage/random dejan campañas con el MISMO
   (logN, logQ, logDelta, logSlots, bitPerCoeff) de los dos lados, asi que
   estiman "otro site, misma escala". Si despues vas a predecir corridas con
   logQ nuevos, ese numero no aplica. --split config deja afuera una
   configuracion entera por fold y es el unico que estima lo que realmente
   te importa.

2. Chequeo de honestidad automatico.
   Sea cual sea el --split, el trainer verifica si cada fold dejo afuera
   configuraciones que igual seguian presentes en train, y avisa. Un CV que
   no separa configs ya no puede pasar por un CV que si lo hace.

3. Feature set 'relative' arreglado.
   - rel_bit y bit_minus_logq van RECORTADOS a una ventana (--clip). Sin
     recorte, un logQ/logDelta mas grande manda la feature a un rango que el
     modelo nunca vio: un arbol devuelve la ultima hoja y un logreg/mlp
     extrapola linealmente y se satura en la clase equivocada. Ese es el
     motivo de que 'relative' + logreg diera todavia peor.
   - coeff_mod_gaps ahora se normaliza por gaps (antes su rango dependia de
     logN/logSlots, o sea no era invariante a escala pese a estar en el set
     "invariante a escala").
   - limb_frac / limb_headroom se fueron: usaban n_limbs = logQ/bitPerCoeff,
     que esta al reves y da 1.0 constante. Sin RNS limb es siempre 0; cuando
     agregues RNS hay que definir n_limbs de verdad.
   - se agregan bit_over_q, bit_frac, q_minus_delta, delta_over_q y
     depth_left, todas acotadas y adimensionales.

4. Metricas: el titular es macro F1 y la DIFERENCIA contra el baseline
   trivial, no la accuracy sola. Con clases desbalanceadas la accuracy sube
   sola y no significa nada.

5. --class-weight ahora arranca en 'balanced'.

6. El bundle guarda las configuraciones de entrenamiento y el rango de cada
   feature, para que predict_heaan.py pueda avisar cuando la corrida nueva
   esta fuera de rango en vez de decir "54/54 sites vistos" y quedarse
   tranquilo.


Ejemplos
--------
  # el CV que corresponde si vas a predecir configs nuevas
  python3 train_heaan_multiclass_site_within_stage.py results/ml \
      --model hgb --feature-set relative --split config \
      --save-model heaan_rel.joblib

  # el de antes, para comparar (optimista si el test tiene configs nuevas)
  python3 train_heaan_multiclass_site_within_stage.py results/ml \
      --model tree --depth 16 --split site-within-stage
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
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.utils.class_weight import compute_sample_weight


HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_TREES = 200
DEFAULT_DEPTH = 8
DEFAULT_SAMPLE = 1_000_000
DEFAULT_BLOCK = 2_000_000
DEFAULT_CLIP = 32.0

CORRECT_MAX = 0.1
CORRUPTED_MAX = 10.0

CLASS_NAMES = ["correct", "corrupted", "failed"]
N_CLASSES = 3

BUNDLE_FORMAT = 8


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

ROW_FEATURES = ["bit", "coeff", "limb"]

CAMPAIGN_NUMERIC = [
    "op_step", "op_depth", "logN", "logQ", "logDelta", "logSlots", "dnum",
    "withNTT", "mult_depth", "isComplex", "bitPerCoeff", "doAdd", "doPlainMul",
    "doMul", "doRot", "doBoot",
]

CAMPAIGN_CATEGORICAL = ["stage"]

FEATURE_SETS = ("raw", "extra", "relative")

# Columnas que definen la ESCALA de una corrida: cambian lo que significa un
# valor dado de bit/coeff de campaña a campaña. Definen tambien la unidad de
# --split config.
CONFIG_KEYS = ["logN", "logQ", "logDelta", "logSlots", "bitPerCoeff"]
SCALE_CAMPAIGN_COLUMNS = list(CONFIG_KEYS)

EXTRA_FEATURES = [
    "rel_bit",         # bit - logDelta
    "bit_minus_logq",  # bit - logQ
    "coeff_mod_gaps",  # coeff % gaps
    "is_slot",
    "coeff_ge_half",
    "n_ops",
]

# Reemplazos invariantes a escala de bit/coeff/logN/logQ/logDelta/logSlots/
# bitPerCoeff. Todas acotadas: ninguna crece con logQ.
RELATIVE_FEATURES = [
    "rel_bit",             # clip(bit - logDelta)  <- la feature fisica principal
    "bit_minus_logq",      # clip(bit - logQ)
    "bit_over_q",          # bit >= logQ  (overflow del modulo, evento neto)
    "bit_frac",            # bit / (bitPerCoeff - 1)        en [0,1]
    "q_minus_delta",       # logQ - logDelta   (headroom de la config)
    "delta_over_q",        # logDelta / logQ                en [0,1]
    "coeff_mod_gaps_frac", # (coeff % gaps) / gaps          en [0,1)
    "is_slot",
    "coeff_ge_half",
    "coeff_frac",          # coeff / (N-1)                  en [0,1]
    "op_depth_frac",       # op_depth / mult_depth
    "depth_left",          # mult_depth - op_depth
    "n_ops",
]

CACHE_FORMAT = 2

CACHE_COLUMNS = {
    "cidx": np.int32,
    "limb": np.int32,
    "coeff": np.int32,
    "bit": np.int32,
    "rel_error": np.float32,
}

REQUIRED_ROW_COLUMNS = ["campaign_id", "limb", "coeff", "bit"]
TRUTH_COLUMN = "rel_error"

REQUIRED_META_COLUMNS = [
    "campaign_id", "stage", "op_step", "op_depth",
    "logN", "logQ", "logDelta", "logSlots",
]


def labels_from_rel_error(rel, correct_max: float, corrupted_max: float) -> np.ndarray:
    """0 = correct, 1 = corrupted, 2 = failed. NaN se filtra aguas arriba."""
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
    """Tabla de campañas + copia compacta memmapeada de las filas preparadas."""

    def __init__(
        self,
        ml_dir: str,
        feature_set: str = "raw",
        rebuild: bool = False,
        clip: float = DEFAULT_CLIP,
        drop: list[str] | None = None,
    ):
        if feature_set not in FEATURE_SETS:
            sys.exit(f"feature_set debe ser uno de {FEATURE_SETS}, no {feature_set!r}")

        self.dir = Path(ml_dir)
        self.feature_set = feature_set
        self.clip = float(clip)
        self.drop = list(drop or [])

        self.meta_path = self.dir / "heaan_campaigns.csv"
        self.csv_path = self.dir / "heaan_rows.csv.gz"
        self.npz_path = self.dir / "heaan_rows.npz"
        self.cache_dir = self.dir / ".heaan_cache"

        if not self.meta_path.exists():
            sys.exit(f"no hay heaan_campaigns.csv en {self.dir}")

        if self.npz_path.exists():
            self.source = self.npz_path
        elif self.csv_path.exists():
            self.source = self.csv_path
        else:
            sys.exit(f"no hay heaan_rows.npz ni heaan_rows.csv.gz en {self.dir}")

        self._load_meta()
        self._build_campaign_matrix()

        if rebuild and self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        self._ensure_cache()
        self._open_cache()

    # -- tabla de campañas -------------------------------------------------

    def _load_meta(self):
        meta = pd.read_csv(self.meta_path)

        missing = [c for c in REQUIRED_META_COLUMNS if c not in meta.columns]
        if missing:
            sys.exit(
                "heaan_campaigns.csv no tiene columnas obligatorias: "
                + ", ".join(missing)
            )

        if meta.campaign_id.duplicated().any():
            dup = int(meta.campaign_id.duplicated().sum())
            sys.exit(f"heaan_campaigns.csv tiene {dup:,} campaign_id duplicados")

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

        # identidad de configuracion (la escala de la corrida)
        self.config_keys = [c for c in CONFIG_KEYS if c in self.meta.columns]
        if self.config_keys:
            self.config = (
                self.meta[self.config_keys]
                .astype(str)
                .agg("|".join, axis=1)
                .to_numpy()
            )
        else:
            self.config = np.full(self.n_campaigns, "unknown", dtype=object)

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

    def config_table(self) -> pd.DataFrame:
        if not self.config_keys:
            return pd.DataFrame()
        g = self.meta.groupby(self.config_keys, dropna=False).size()
        return g.rename("campaigns").reset_index()

    def _map_campaign_ids(self, values) -> np.ndarray:
        v = np.asarray(values)

        if self._cid_sorted is not None and v.dtype.kind in "iu":
            pos = np.searchsorted(self._cid_sorted, v.astype(np.int64))
            pos = np.clip(pos, 0, len(self._cid_sorted) - 1)
            bad = self._cid_sorted[pos] != v
            if bad.any():
                sys.exit(
                    f"{int(bad.sum()):,} filas apuntan a un campaign_id que no esta "
                    "en heaan_campaigns.csv"
                )
            return self._cid_order[pos]

        s = pd.Series(np.asarray(values).astype(str)).map(self._cid_map)
        if s.isna().any():
            sys.exit(
                f"{int(s.isna().sum()):,} filas apuntan a un campaign_id que no esta "
                "en heaan_campaigns.csv"
            )
        return s.to_numpy(dtype=np.int32)

    def _build_campaign_matrix(self):
        present = [c for c in CAMPAIGN_NUMERIC if c in self.meta.columns]
        self.missing_campaign_columns = [
            c for c in CAMPAIGN_NUMERIC if c not in self.meta.columns
        ]

        num = self.meta[present].apply(pd.to_numeric, errors="coerce").fillna(-1)
        stage_dummies = pd.get_dummies(
            self.meta[CAMPAIGN_CATEGORICAL], columns=CAMPAIGN_CATEGORICAL
        )
        camp = pd.concat([num, stage_dummies], axis=1).astype(np.float32)

        self.campaign_columns = list(camp.columns)
        self.campaign_matrix = np.ascontiguousarray(camp.to_numpy(dtype=np.float32))
        self._cpos = {name: i for i, name in enumerate(self.campaign_columns)}

        if self.feature_set == "relative":
            self.exposed_campaign_columns = [
                c for c in self.campaign_columns if c not in SCALE_CAMPAIGN_COLUMNS
            ]
        else:
            self.exposed_campaign_columns = self.campaign_columns

        self._exposed_idx = np.array(
            [self._cpos[c] for c in self.exposed_campaign_columns], dtype=np.int64
        )

        row_features = [] if self.feature_set == "relative" else ROW_FEATURES
        derived = {
            "raw": [],
            "extra": EXTRA_FEATURES,
            "relative": RELATIVE_FEATURES,
        }[self.feature_set]

        all_columns = row_features + self.exposed_campaign_columns + derived

        unknown = [c for c in self.drop if c not in all_columns]
        if unknown:
            sys.exit(
                "--drop-features nombra columnas que no existen en el set "
                f"'{self.feature_set}': {', '.join(unknown)}\n"
                "disponibles: " + ", ".join(all_columns)
            )
        self.columns = [c for c in all_columns if c not in set(self.drop)]
        if not self.columns:
            sys.exit("--drop-features dejo el modelo sin ninguna feature")

        if self.feature_set in ("extra", "relative"):
            need = ["logDelta", "logQ", "logN", "logSlots"]
            miss = [c for c in need if c not in self._cpos]
            if miss:
                sys.exit(
                    f"--feature-set {self.feature_set} necesita estas columnas de "
                    "campaña: " + ", ".join(miss)
                )
        if self.feature_set == "relative":
            need = ["bitPerCoeff", "mult_depth", "op_depth"]
            miss = [c for c in need if c not in self._cpos]
            if miss:
                sys.exit(
                    "--feature-set relative necesita estas columnas de campaña: "
                    + ", ".join(miss)
                )

    # -- cache de filas ----------------------------------------------------

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

        print(f"construyendo cache de filas desde {self.source.name} (una vez) ...",
              flush=True)
        t0 = time.time()
        self._has_truth = True

        if self.source is self.npz_path:
            n_rows, n_bad = self._fill_cache_from_npz(tmp)
        else:
            n_rows, n_bad = self._fill_cache_from_csv(tmp)

        if n_rows == 0:
            sys.exit("las filas preparadas quedaron vacias despues de filtrar")

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
            f"  {n_rows:,} filas cacheadas en {time.time() - t0:.1f}s"
            + (f" ({n_bad:,} descartadas: rel_error NaN o negativo)" if n_bad else ""),
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
                        "las filas preparadas no tienen columnas obligatorias: "
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
        with np.load(self.npz_path, allow_pickle=True) as z:
            missing = [c for c in REQUIRED_ROW_COLUMNS if c not in z.files]
            if missing:
                sys.exit(
                    "el npz preparado no tiene columnas obligatorias: "
                    + ", ".join(missing)
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

    # -- acceso ------------------------------------------------------------

    def labels(self, start: int, stop: int, correct_max, corrupted_max) -> np.ndarray:
        return labels_from_rel_error(
            self.col["rel_error"][start:stop], correct_max, corrupted_max
        )

    def _clip(self, a: np.ndarray) -> np.ndarray:
        if self.clip and self.clip > 0:
            return np.clip(a, -self.clip, self.clip)
        return a

    def features(self, idx: np.ndarray) -> np.ndarray:
        """Matriz de features para indices arbitrarios de fila.

        Se arma como un diccionario nombre -> columna y despues se apila en el
        orden de self.columns. Es un poco mas lento que escribir por indice,
        pero hace imposible el bug de desalinear una columna con su nombre.
        """
        bit = self.col["bit"][idx].astype(np.float32)
        coeff = self.col["coeff"][idx].astype(np.float32)
        limb = self.col["limb"][idx].astype(np.float32)

        camp_full = self.campaign_matrix[self.col["cidx"][idx]]

        parts: dict[str, np.ndarray] = {}

        if self.feature_set != "relative":
            parts["bit"] = bit
            parts["coeff"] = coeff
            parts["limb"] = limb

        for name in self.exposed_campaign_columns:
            parts[name] = camp_full[:, self._cpos[name]]

        if self.feature_set in ("extra", "relative"):
            log_delta = camp_full[:, self._cpos["logDelta"]]
            log_q = camp_full[:, self._cpos["logQ"]]
            log_n = camp_full[:, self._cpos["logN"]]
            log_slots = camp_full[:, self._cpos["logSlots"]]

            half = np.exp2(np.maximum(log_n - 1.0, 0.0))
            gaps = np.maximum(half / np.exp2(log_slots), 1.0)
            coeff_mod_gaps = np.mod(coeff, gaps)

            n_ops = np.zeros(len(bit), dtype=np.float32)
            for c in ("doAdd", "doPlainMul", "doMul", "doRot"):
                if c in self._cpos:
                    n_ops += camp_full[:, self._cpos[c]]

            if self.feature_set == "extra":
                parts["rel_bit"] = bit - log_delta
                parts["bit_minus_logq"] = bit - log_q
                parts["coeff_mod_gaps"] = coeff_mod_gaps
                parts["is_slot"] = (coeff_mod_gaps == 0).astype(np.float32)
                parts["coeff_ge_half"] = (coeff >= half).astype(np.float32)
                parts["n_ops"] = n_ops
            else:
                bit_per_coeff = camp_full[:, self._cpos["bitPerCoeff"]]
                mult_depth = camp_full[:, self._cpos["mult_depth"]]
                op_depth = camp_full[:, self._cpos["op_depth"]]

                parts["rel_bit"] = self._clip(bit - log_delta)
                parts["bit_minus_logq"] = self._clip(bit - log_q)
                parts["bit_over_q"] = (bit >= log_q).astype(np.float32)
                parts["bit_frac"] = bit / np.maximum(bit_per_coeff - 1.0, 1.0)
                parts["q_minus_delta"] = log_q - log_delta
                parts["delta_over_q"] = log_delta / np.maximum(log_q, 1.0)
                parts["coeff_mod_gaps_frac"] = coeff_mod_gaps / gaps
                parts["is_slot"] = (coeff_mod_gaps == 0).astype(np.float32)
                parts["coeff_ge_half"] = (coeff >= half).astype(np.float32)
                parts["coeff_frac"] = coeff / np.maximum(2.0 * half - 1.0, 1.0)
                parts["op_depth_frac"] = op_depth / np.maximum(mult_depth, 1.0)
                parts["depth_left"] = mult_depth - op_depth
                parts["n_ops"] = n_ops

        missing = [c for c in self.columns if c not in parts]
        if missing:
            sys.exit(f"bug interno: faltan features {missing}")

        X = np.empty((len(bit), len(self.columns)), dtype=np.float32)
        for i, name in enumerate(self.columns):
            X[:, i] = parts[name]
        return X

    def feature_ranges(self, idx: np.ndarray) -> dict:
        X = self.features(idx)
        return {
            name: [float(X[:, i].min()), float(X[:, i].max())]
            for i, name in enumerate(self.columns)
        }


# ---------------------------------------------------------------------------
# Folds
# ---------------------------------------------------------------------------

@dataclass
class Fold:
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
    """Devuelve (nombre_del_split, mascara_de_campañas_permitidas, folds)."""
    allowed = np.ones(ds.n_campaigns, dtype=bool)

    if stages:
        allowed &= np.isin(ds.stage, np.asarray(stages, dtype=object).astype(str))
        if not allowed.any():
            sys.exit(f"no hay campañas para stages={stages}")

    if how == "random":
        return (
            "random 5-fold (in-distribution)",
            allowed,
            [Fold(f"fold {i + 1}", random_part=i) for i in range(5)],
        )

    if how == "config":
        levels = sorted(set(ds.config[allowed].tolist()))
        if len(levels) < 2:
            sys.exit(
                "--split config necesita >=2 configuraciones distintas de "
                f"{ds.config_keys}; en este dataset hay {len(levels)}. "
                "Con una sola config no hay forma de estimar generalizacion a "
                "configs nuevas: hace falta entrenar con varios logQ/logDelta."
            )
        print(f"  config: {len(levels)} configuraciones de {ds.config_keys}")
        return (
            "leave-one-config-out",
            allowed,
            [Fold(c, test_campaigns=allowed & (ds.config == c)) for c in levels],
        )

    if how == "stage":
        levels = sorted(set(ds.stage[allowed].tolist()))
        if len(levels) < 2:
            sys.exit(f"--split stage necesita >=2 stages; hay {levels}")
        return (
            "leave-one-stage-out",
            allowed,
            [Fold(s, test_campaigns=allowed & (ds.stage == s)) for s in levels],
        )

    sites = sorted(set(ds.site[allowed].tolist()))

    if how == "site-within-stage":
        by_stage: dict[str, set] = {}
        for st, si in zip(ds.stage[allowed], ds.site[allowed]):
            by_stage.setdefault(st, set()).add(si)

        keep_stages = {s for s, v in by_stage.items() if len(v) >= 2}
        singletons = sorted(s for s, v in by_stage.items() if len(v) < 2)

        sites = sorted(s for s in sites if s.split("/", 1)[0] in keep_stages)

        if not sites:
            sys.exit(
                "--split site-within-stage no encontro ningun stage con >=2 sites "
                "distintos; usa --split site o --split random"
            )

        print(
            f"  site-within-stage: {len(sites)} sites elegibles "
            f"de {len(keep_stages)} stages"
        )
        if singletons:
            print(
                "  stages con un solo site: quedan en train y nunca se dejan "
                "afuera: " + ", ".join(singletons)
            )

        name = "leave-one-site-out-within-known-stage"
    else:
        if len(sites) < 2:
            sys.exit(f"--split site necesita >=2 sites; hay {sites}")
        name = "leave-one-site-out"

    return (
        name,
        allowed,
        [Fold(s, test_campaigns=allowed & (ds.site == s)) for s in sites],
    )


def audit_folds(ds: Dataset, allowed: np.ndarray, folds: list[Fold]) -> dict:
    """Cuantos folds dejaron afuera configuraciones que igual seguian en train.

    Este es el chequeo que hace que un CV no pueda hacerse pasar por otro.
    """
    leaky = 0
    checked = 0

    for fold in folds:
        if fold.test_campaigns is None:
            # el split random no separa nada a nivel campaña
            leaky += 1
            checked += 1
            continue
        test_mask = fold.test_campaigns & allowed
        train_mask = allowed & ~fold.test_campaigns
        if not test_mask.any() or not train_mask.any():
            continue
        checked += 1
        if set(ds.config[test_mask].tolist()) & set(ds.config[train_mask].tolist()):
            leaky += 1

    return {"folds_checked": checked, "folds_with_config_in_train": leaky}


def limit_folds(folds: list[Fold], max_folds: int) -> list[Fold]:
    if not max_folds or len(folds) <= max_folds:
        return folds
    keep = np.linspace(0, len(folds) - 1, max_folds).round().astype(int)
    return [folds[i] for i in sorted(set(keep.tolist()))]


# ---------------------------------------------------------------------------
# Muestreo
# ---------------------------------------------------------------------------

def sample_train_indices(ds, allowed, fold, cap, rng, block):
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
        return None, None, None, available
    X = ds.features(idx)
    y = labels_from_rel_error(ds.col["rel_error"][idx], correct_max, corrupted_max)
    return X, y, idx, available


# ---------------------------------------------------------------------------
# Metricas
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
    def balanced_accuracy(self) -> float:
        if not self.n:
            return float("nan")
        _, recall, _, support = self.per_class()
        seen = support > 0
        return float(recall[seen].mean()) if seen.any() else float("nan")

    @property
    def weighted_f1(self) -> float:
        if not self.n:
            return float("nan")
        _, _, f1, support = self.per_class()
        return float(np.average(f1, weights=support)) if support.sum() else 0.0

    def _sdc_counts(self):
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
# Modelo
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

    if kind == "logreg":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=2000,
                class_weight=class_weight,
                random_state=0,
            )),
        ])

    if kind == "mlp":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=300,
                early_stopping=True,
                n_iter_no_change=10,
                random_state=0,
            )),
        ])

    return DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=min_leaf,
        class_weight=class_weight,
        random_state=0,
    )


def fit_model(model, X, y, kind: str, class_weight):
    """MLPClassifier no toma class_weight al construirse.

    En scikit-learn nuevo acepta sample_weight en fit; en versiones viejas no.
    Si no lo acepta, se hace fallback a fit sin pesos y se avisa, en vez de
    romper la corrida entera.
    """
    if kind == "mlp" and class_weight == "balanced":
        sw = compute_sample_weight("balanced", y)
        try:
            model.fit(X, y, clf__sample_weight=sw)
            return
        except TypeError:
            print(
                "  aviso: este scikit-learn no acepta sample_weight en "
                "MLPClassifier; se entrena sin balancear las clases"
            )
    model.fit(X, y)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    ap.add_argument("ml_dir", nargs="?", default=os.path.join(HERE, "ml"))

    ap.add_argument(
        "--model",
        choices=["tree", "forest", "hgb", "logreg", "mlp"],
        default="tree",
        help=(
            "tree/forest/hgb: cortes axis-aligned, solo pueden umbralar una "
            "feature. logreg/mlp: lineal / red chica estandarizada, pueden usar "
            "un ratio como ratio. Con --feature-set relative, hgb y logreg son "
            "las apuestas razonables"
        ),
    )
    ap.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    ap.add_argument("--trees", type=int, default=DEFAULT_TREES)
    ap.add_argument("--min-leaf", type=int, default=None, metavar="N")
    ap.add_argument(
        "--class-weight",
        choices=["none", "balanced"],
        default="balanced",
        help="default: balanced (antes era none, y con clases desbalanceadas "
             "eso infla la accuracy sin mejorar nada)",
    )
    ap.add_argument("--n-jobs", type=int, default=-1)

    ap.add_argument(
        "--split",
        default="site-within-stage",
        choices=["config", "site-within-stage", "site", "stage", "random"],
        help=(
            "config: leave-one-config-out sobre (logN, logQ, logDelta, "
            "logSlots, bitPerCoeff). Es el unico que estima que va a pasar con "
            "una corrida de configuracion nueva. Los demas dejan la misma "
            "escala de los dos lados"
        ),
    )
    ap.add_argument("--max-folds", type=int, default=0, metavar="N")
    ap.add_argument("--stages", nargs="+", default=None, metavar="S")

    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, metavar="N")
    ap.add_argument("--block", type=int, default=DEFAULT_BLOCK, metavar="N")

    ap.add_argument(
        "--feature-set",
        choices=list(FEATURE_SETS),
        default="raw",
        help=(
            "raw: bit/coeff/limb + columnas de campaña tal cual. extra: raw + "
            + ", ".join(EXTRA_FEATURES) + ". relative: saca las columnas de "
            "escala absoluta y las reemplaza por (" + ", ".join(RELATIVE_FEATURES)
            + "). Usa relative si vas a predecir configs nuevas"
        ),
    )
    ap.add_argument(
        "--clip",
        type=float,
        default=DEFAULT_CLIP,
        metavar="B",
        help=(
            f"recorta rel_bit y bit_minus_logq a +-B bits (default {DEFAULT_CLIP:g}; "
            "0 = sin recorte). Es lo que impide que un logQ mas grande mande la "
            "feature a un rango nunca visto. Solo aplica a --feature-set relative"
        ),
    )
    ap.add_argument(
        "--drop-features",
        nargs="+",
        default=None,
        metavar="NAME",
        help=(
            "saca features por nombre. Util cuando predict_heaan.py reporta que "
            "una feature cae 100%% fuera del rango de entrenamiento: p.ej. "
            "--drop-features q_minus_delta delta_over_q op_step"
        ),
    )
    ap.add_argument("--correct-max", type=float, default=CORRECT_MAX, metavar="X")
    ap.add_argument("--corrupted-max", type=float, default=CORRUPTED_MAX, metavar="X")

    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--save-model", default=None, metavar="PATH")

    args = ap.parse_args()

    if args.sample < 0:
        ap.error("--sample debe ser >= 0")
    if args.block <= 0:
        ap.error("--block debe ser > 0")
    if args.depth < 0:
        ap.error("--depth debe ser >= 0")
    if args.trees <= 0:
        ap.error("--trees debe ser > 0")
    if not (0 < args.correct_max < args.corrupted_max):
        ap.error("hace falta 0 < --correct-max < --corrupted-max")

    class_weight = None if args.class_weight == "none" else "balanced"

    ds = Dataset(
        os.path.abspath(args.ml_dir),
        feature_set=args.feature_set,
        rebuild=args.rebuild_cache,
        clip=args.clip,
        drop=args.drop_features,
    )

    if not ds.has_truth:
        sys.exit(
            "las filas preparadas no tienen rel_error, asi que no hay nada que "
            "aprender — este dataset solo puede puntuarse con un modelo ya "
            "entrenado (ver predict_heaan.py)"
        )

    print(
        f"dataset: {ds.n_rows:,} filas · {ds.n_campaigns:,} campañas · "
        f"{len(ds.columns)} features"
    )

    cfg = ds.config_table()
    if len(cfg):
        print(f"configuraciones ({len(cfg)}):")
        print("  " + cfg.to_string(index=False).replace("\n", "\n  "))
        if len(cfg) == 1:
            print(
                "  >> Hay UNA sola configuracion. Con un solo (logQ, logDelta, ...)\n"
                "     ningun CV puede decirte si el modelo generaliza a otra: la\n"
                "     unica forma es entrenar con varias."
            )

    if ds.missing_campaign_columns:
        print(
            "  columnas de campaña ausentes en heaan_campaigns.csv (descartadas): "
            + ", ".join(ds.missing_campaign_columns)
        )

    dropped_bad = int(ds.cache_info.get("n_dropped_bad_rel_error", 0))
    if dropped_bad:
        print(f"  {dropped_bad:,} filas descartadas: rel_error NaN o negativo")

    print(
        "target: severidad 3 clases  "
        f"correct <= {args.correct_max:g} < corrupted <= {args.corrupted_max:g} < failed"
    )
    print(f"features: set '{args.feature_set}' ({len(ds.columns)} columnas)"
          + (f", clip +-{args.clip:g}" if args.feature_set == "relative" and args.clip
             else ""))
    print(f"model: {args.model} · class-weight {args.class_weight}")

    split_name, allowed, all_folds = build_folds(ds, args.split, args.stages)
    folds = limit_folds(all_folds, args.max_folds)

    print(
        f"split: {split_name} ({len(folds)} folds"
        + (f" de {len(all_folds)}" if len(folds) != len(all_folds) else "")
        + ")"
    )

    audit = audit_folds(ds, allowed, folds)
    if audit["folds_with_config_in_train"]:
        print()
        print("  " + "!" * 70)
        print(
            f"  AVISO: {audit['folds_with_config_in_train']} de "
            f"{audit['folds_checked']} folds dejaron afuera datos cuya"
        )
        print("  configuracion (logN/logQ/logDelta/logSlots/bitPerCoeff) SEGUIA")
        print("  presente en el conjunto de entrenamiento. El numero de CV que")
        print("  sale abajo estima 'otro site, misma escala', NO 'otra escala'.")
        print("  Si vas a predecir corridas con logQ nuevos, corre --split config.")
        print("  " + "!" * 70)

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

        X, y, _, _ = training_set(
            ds, allowed, fold, args.sample, rng, args.block,
            args.correct_max, args.corrupted_max,
        )

        if X is None:
            print(f"  {fold.name:<28}{0:>11}{0:>12}    (salteado: sin filas de train)")
            continue

        if len(np.unique(y)) < 2:
            only = CLASS_NAMES[int(y[0])]
            print(
                f"  {fold.name:<28}{len(y):>11,}{0:>12}    "
                f"(salteado: train tiene solo la clase {only})"
            )
            continue

        model = make_model(
            args.model, args.depth, args.trees, args.min_leaf, class_weight, args.n_jobs
        )
        fit_model(model, X, y, args.model, class_weight)

        majority = int(np.argmax(np.bincount(y, minlength=N_CLASSES)))
        n_fit = len(y)
        del X, y

        stats, base = score_fold(
            ds, allowed, fold, model, args.block, majority,
            args.correct_max, args.corrupted_max,
        )

        if stats.n == 0:
            print(f"  {fold.name:<28}{n_fit:>11,}{0:>12}    (salteado: sin filas de test)")
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
        sys.exit("todos los folds se saltearon — no hay nada que reportar")

    baseline = pooled_base_hits / pooled_base_n if pooled_base_n else float("nan")
    lift = pooled.accuracy - baseline

    print("\nPooled sobre folds")
    print(f"  filas        {pooled.n:,}")
    print(f"  macro F1     {pooled.macro_f1:.4f}   <- el numero que importa")
    print(f"  bal accuracy {pooled.balanced_accuracy:.4f}")
    print(f"  accuracy     {pooled.accuracy:.4f}")
    print(f"  base acc     {baseline:.4f}   (predecir siempre la clase mayoritaria)")
    print(f"  lift         {lift:+.4f}   (accuracy - base)")
    print(f"  weighted F1  {pooled.weighted_f1:.4f}")
    print(f"  SDC accuracy {pooled.sdc_accuracy:.4f}")
    print(f"  SDC F1       {pooled.sdc_f1:.4f}")

    if lift < 0.05:
        print()
        print("  >> El modelo casi no le gana a predecir siempre la clase")
        print("     mayoritaria. Una accuracy alta aca no significa nada.")

    print("\nPooled por clase")
    print(pooled.report())

    print("\nMatriz de confusion pooled (filas=real, columnas=predicho)")
    print(pooled.confusion())

    # -- fit final ---------------------------------------------------------

    print("\nFit final ...", flush=True)

    X_all, y_all, idx_all, n_available = training_set(
        ds, allowed, None, args.sample, np.random.default_rng(424242), args.block,
        args.correct_max, args.corrupted_max,
    )

    if X_all is None:
        sys.exit("no hay filas para el fit final")

    print("\nDistribucion de clases de la muestra final")
    print_distribution(y_all)

    final = make_model(
        args.model, args.depth, args.trees, args.min_leaf, class_weight, args.n_jobs
    )
    fit_model(final, X_all, y_all, args.model, class_weight)

    train_stats = Stats()
    train_stats.add(y_all, final.predict(X_all).astype(np.int8))

    print("\nScore del fit final sobre sus propias filas (optimista — usa el CV)")
    print(f"  accuracy     {train_stats.accuracy:.4f}")
    print(f"  macro F1     {train_stats.macro_f1:.4f}")
    print(f"  SDC F1       {train_stats.sdc_f1:.4f}")

    ranges = {
        name: [float(X_all[:, i].min()), float(X_all[:, i].max())]
        for i, name in enumerate(ds.columns)
    }

    if hasattr(final, "feature_importances_"):
        print("\nImportancias (fit final):")
        ranked = sorted(zip(ds.columns, final.feature_importances_), key=lambda t: -t[1])
        for name, imp in ranked:
            if imp > 0.001:
                print(f"  {name:<28}{imp:.3f}")
    elif isinstance(final, Pipeline) and hasattr(final.named_steps.get("clf"), "coef_"):
        coefs = np.abs(final.named_steps["clf"].coef_).sum(axis=0)
        print("\n|coeficiente| sumado sobre clases, features estandarizadas:")
        ranked = sorted(zip(ds.columns, coefs), key=lambda t: -t[1])
        for name, c in ranked:
            if c > 0.01:
                print(f"  {name:<28}{c:.3f}")

    if args.model == "tree" and 0 < args.depth <= 6:
        print("\nReglas:")
        print(export_text(final, feature_names=ds.columns, class_names=CLASS_NAMES))

    if args.save_model:
        import joblib

        bundle = {
            "format": BUNDLE_FORMAT,
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
                "feature_set": args.feature_set,
                "clip": float(args.clip),
                "dropped": list(ds.drop),
                "row_features": [] if args.feature_set == "relative" else ROW_FEATURES,
                "campaign_features": ds.exposed_campaign_columns,
                "derived_features": {
                    "raw": [],
                    "extra": EXTRA_FEATURES,
                    "relative": RELATIVE_FEATURES,
                }[args.feature_set],
            },
            "feature_ranges": ranges,
            "train_stages": sorted(set(ds.stage[allowed].tolist())),
            "train_sites": sorted(set(ds.site[allowed].tolist())),
            "train_config_keys": ds.config_keys,
            "train_configs": sorted(set(ds.config[allowed].tolist())),
            "cv": {
                "split": split_name,
                "folds": len(folds),
                "rows_scored": int(pooled.n),
                "confusion_matrix": pooled.cm.tolist(),
                "accuracy": pooled.accuracy,
                "macro_f1": pooled.macro_f1,
                "balanced_accuracy": pooled.balanced_accuracy,
                "weighted_f1": pooled.weighted_f1,
                "sdc_accuracy": pooled.sdc_accuracy,
                "sdc_f1": pooled.sdc_f1,
                "baseline_accuracy": baseline,
                "lift": lift,
                "folds_checked": audit["folds_checked"],
                "folds_with_config_in_train": audit["folds_with_config_in_train"],
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

        print(f"\nmodelo guardado en {out} ({len(ds.columns)} features)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
