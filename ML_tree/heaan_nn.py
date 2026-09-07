#!/usr/bin/env python3
"""
heaan_nn.py -- Predecir el resultado de inyeccion de errores en pipelines CKKS/HEAAN
               que el modelo nunca vio, entrenando con pipelines simples.

Diseno:
  1. Todas las features son RELATIVAS AL PUNTO DE INYECCION y ACOTADAS.
     Nada de conteos globales sin clipear: eso es lo que rompe la extrapolacion
     a pipelines mas largos (p.ej. una red neuronal).
  2. El nivel del modulo se trackea op por op (logQ baja logDelta por cada
     multiplicacion; boot lo restaura), asi que `bit >= logQ_at_inject` es el
     evento fisico real de overflow, no `bit >= logQ` inicial.
  3. Hay un BASELINE DE REGLA explicito con la fisica ya conocida. Si el modelo
     no le gana, el modelo no aprendio nada.
  4. La validacion agrupa por PIPELINE (leave-one-pipeline-out), que es la
     pregunta que importa. Tambien hay split por profundidad: entrenar corto,
     testear largo.

Uso:
    python3 heaan_nn.py selftest                     # verifica el codigo con datos sinteticos
    python3 heaan_nn.py inspect  datos.csv           # muestra como resuelve las columnas
    python3 heaan_nn.py train    datos.csv --split pipeline
    python3 heaan_nn.py train    datos.csv --split depth --save modelo.joblib
"""

from __future__ import annotations

import argparse
import json
import os
import time
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Resolucion tolerante de columnas
# ---------------------------------------------------------------------------
# No conozco tu esquema exacto, asi que cada campo canonico tiene una lista de
# candidatos. `inspect` te muestra que resolvio. Podes forzar cualquiera con
# --col canonico=nombre_real.

CANDIDATES: dict[str, list[str]] = {
    # parametros de escala
    "logN":      ["logn", "log_n", "logdegree", "log_degree"],
    "logDelta":  ["logdelta", "log_delta", "logscale", "log_scale", "logp", "log_p"],
    "logQ":      ["logq", "log_q", "logqbits", "log_q_bits"],
    "logSlots":  ["logslots", "log_slots", "lognslots"],
    # punto de inyeccion dentro del ciphertext
    "bit":       ["bit", "bitpos", "bit_pos", "bitindex", "bit_index", "flip_bit"],
    "coeff":     ["coeff", "coefficient", "coeff_idx", "coeff_index", "coefindex"],
    "limb":      ["limb", "limb_idx", "limb_index", "rns_limb"],
    # posicion de la inyeccion dentro del pipeline
    "op_step":   ["op_step", "opstep", "step", "inject_step", "op_index", "opidx"],
    "op_depth":  ["op_depth", "opdepth", "depth", "mul_depth", "muldepth", "level"],
    # el pipeline
    "pipeline":  ["pipeline", "ops", "op_seq", "opseq", "circuit", "sequence"],
    "doAdd":     ["doadd", "do_add", "n_add", "nadd", "num_add", "adds"],
    "doMul":     ["domul", "do_mul", "n_mul", "nmul", "num_mul", "muls"],
    "doPlainMul":["doplainmul", "do_plainmul", "n_plainmul", "nplainmul", "pmul",
                  "do_pmul", "plainmuls", "do_cmul", "n_cmul"],
    "doScalarMul": ["doscalarmul", "do_scalarmul", "n_scalarmul", "scalarmul",
                    "do_smul", "n_smul"],
    "doRot":     ["dorot", "do_rot", "n_rot", "nrot", "num_rot", "rots", "rotations"],
    "doBoot":    ["doboot", "do_boot", "n_boot", "nboot", "boot", "bootstrap",
                  "do_bootstrap"],
    # target
    "label":     ["label", "outcome", "result", "class", "verdict", "status",
                  "y", "target"],
    "rel_error": ["rel_error", "relerror", "relative_error", "err", "error",
                  "log2_rel_error", "log2relerror"],
    "l2_norm":   ["l2_norm", "l2norm", "l2"],
    "is_sdc":    ["is_sdc", "issdc", "sdc"],
    "hidden_layer": ["hidden_layer", "hiddenlayer"],
    "reduceSum_layer": ["reducesum_layer", "reducesumlayer"],
    # estructurales del esquema real
    "campaign_id": ["campaign_id", "campaignid", "campaign"],
    "mult_depth": ["mult_depth", "multdepth", "depth_total", "total_depth"],
    "withNTT":   ["withntt", "with_ntt", "ntt", "is_ntt", "ntt_domain"],
    "isComplex": ["iscomplex", "is_complex", "complex"],
    "scaleTech": ["scaletech", "scale_tech", "rescale_tech", "scaling_technique"],
    "dnum":      ["dnum", "d_num", "num_digits"],
    "library":   ["library", "lib", "backend"],
    "amountBits": ["amountbits", "amount_bits", "n_bits_flipped", "nbits"],
    # opcionales
    "seed":      ["seed", "rng_seed", "run_seed"],
    "stage":     ["stage", "phase", "site"],
    "bitPerCoeff": ["bitpercoeff", "bits_per_coeff", "coeff_bits", "bitwidth"],
}

REQUIRED = ["logN", "logDelta", "logQ", "logSlots", "bit", "coeff"]


def _norm(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum() or ch == "_")


def resolve_columns(df: pd.DataFrame, overrides: dict[str, str] | None = None
                    ) -> dict[str, str | None]:
    """Mapea nombre canonico -> nombre real en el CSV (o None si no esta)."""
    overrides = overrides or {}
    lookup = {_norm(c): c for c in df.columns}
    resolved: dict[str, str | None] = {}
    for canon, cands in CANDIDATES.items():
        if canon in overrides:
            actual = overrides[canon]
            if actual not in df.columns:
                raise SystemExit(f"--col {canon}={actual}: esa columna no existe. "
                                 f"Columnas disponibles: {list(df.columns)}")
            resolved[canon] = actual
            continue
        hit = None
        for cand in [_norm(canon)] + cands:
            if cand in lookup:
                hit = lookup[cand]
                break
        resolved[canon] = hit
    return resolved


def print_resolution(resolved: dict[str, str | None], df: pd.DataFrame) -> None:
    print("\n=== Resolucion de columnas ===")
    for canon, actual in resolved.items():
        if actual is None:
            mark = "FALTA" if canon in REQUIRED else "-"
            print(f"  {canon:<14} {mark}")
        else:
            sample = df[actual].dropna()
            uniq = sample.nunique()
            head = list(sample.unique()[:5])
            print(f"  {canon:<14} <- {actual!r:<22} ({uniq} valores unicos, ej: {head})")
    unused = [c for c in df.columns if c not in set(v for v in resolved.values() if v)]
    if unused:
        print(f"\n  Columnas del CSV sin mapear: {unused}")
    missing = [c for c in REQUIRED if resolved.get(c) is None]
    if missing:
        print(f"\n  !! Faltan columnas obligatorias: {missing}")
        print(f"     Forzalas con --col {missing[0]}=nombre_real")




# ---------------------------------------------------------------------------
# 1b. Carga del layout real de dos niveles
# ---------------------------------------------------------------------------
# results/
#   campaigns_start.csv          <- una fila por campana: config + pipeline + sitio
#   data/campaign_XXXXXX.csv.gz  <- una fila por inyeccion: bit, coeff, limb, resultado
#
# Los parametros de campana se repiten identicos en miles de filas. Eso tiene
# una consecuencia que hay que respetar si o si: un CV que parte filas al azar
# pone filas de la MISMA campana en train y en test, que comparten todo salvo
# (bit, coeff, limb). Eso no mide generalizacion, mide memoria. El agrupamiento
# minimo valido es por campaign_id; el que te interesa es por firma de pipeline.

def _read_one(task):
    """Lee un csv.gz, lo muestrea y lo achica. Corre en un proceso aparte:
    descomprimir gzip es CPU-bound y con miles de archivos es EL cuello de
    botella (6379 archivos en serie son decenas de minutos)."""
    path, per, seed, meta_cols, meta_vals = task
    try:
        sub = pd.read_csv(path, compression="gzip")
    except Exception as e:
        return None, 0, 0, f"{path}: {type(e).__name__}"
    total = len(sub)
    sampled = 0
    if per and total > per:
        sub = sub.sample(n=per, random_state=seed)
        sampled = 1
    for c, v in zip(meta_cols, meta_vals):
        if c not in sub.columns:
            sub[c] = v
    return shrink_numeric(sub), total, sampled, None


def shrink_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast de columnas numericas. SEGURO para devolver desde un worker.

    Nada de dtype `category` aca: un Categorical no se puede despicklear entre
    procesos en pandas + Python 3.14 (NotImplementedError en
    NDArrayBacked.__setstate__), y eso rompe el pool entero. Las categorias se
    arman en el proceso padre, despues del concat.
    """
    for c in df.columns:
        col = df[c]
        if pd.api.types.is_integer_dtype(col):
            df[c] = pd.to_numeric(col, downcast="integer")
        elif pd.api.types.is_float_dtype(col):
            df[c] = pd.to_numeric(col, downcast="float")
    return df


def shrink(df: pd.DataFrame) -> pd.DataFrame:
    """shrink_numeric + categorias. Solo en el proceso padre.

    Los parametros de campana se replican identicos en cada fila de inyeccion.
    Un `scaleTech` = "FLEXIBLEAUTO" como string de Python cuesta ~60 bytes por
    fila; como categoria, 1.
    """
    df = shrink_numeric(df)
    for c in df.columns:
        col = df[c]
        if col.dtype == object and col.nunique(dropna=False) <= max(64, len(col) // 100):
            df[c] = col.astype("category")
    return df


def find_campaign_file(data_dir: Path, cid: int) -> Path | None:
    for pat in (f"campaign_{cid:06d}.csv.gz",
                f"campaign_campaign_{cid:06d}.csv.gz",
                f"*{cid:06d}*.csv.gz"):
        hits = sorted(data_dir.glob(pat))
        if hits:
            return hits[0]
    return None


def load_campaigns(root: str, limit: int | None = None,
                   cache: bool = True, quiet: bool = False,
                   sample_per_campaign: int | None = None,
                   max_rows: int | None = 2_000_000,
                   n_jobs: int | None = None,
                   seed: int = 0) -> pd.DataFrame:
    """Junta campaigns_start.csv con los csv.gz por campana en una tabla plana.

    El presupuesto es GLOBAL: `max_rows` se reparte entre las campanas y el
    muestreo se aplica MIENTRAS se lee, no despues. Un tope solo por campana no
    alcanza: con 6379 campanas, 20.000 por campana son 127 millones de filas y
    17 GB antes de que empiece a featurizar.

    sample_per_campaign acota cuantas inyecciones se toman de cada campana.
    No es solo por memoria (un barrido exhaustivo con logN=16 son 2^15 x 64 =
    2.1M filas por campana): tambien corrige un SESGO. Sin tope, una campana con
    logN=16 aporta 4 veces mas filas que una con logN=14 solo por ser mas
    grande, y el modelo termina optimizando para las configs grandes. Con tope,
    cada campana pesa lo mismo, que es lo que corresponde cuando la unidad
    experimental es la campana.

    El muestreo es uniforme dentro de la campana, asi que las proporciones de
    clase de esa campana se conservan.
    """
    root = Path(root)
    start = root / "campaigns_start.csv"
    if not start.exists():
        hits = list(root.glob("campaigns_start.csv")) + list(root.glob("*/campaigns_start.csv"))
        if not hits:
            raise SystemExit(f"No encuentro campaigns_start.csv bajo {root}")
        start = hits[0]
    data_dir = start.parent / "data"
    if not data_dir.exists():
        raise SystemExit(f"No encuentro el directorio {data_dir}")

    tag = (f"spc{sample_per_campaign}" if sample_per_campaign
           else (f"mr{max_rows}" if max_rows else "all"))
    cache_path = start.parent / f".heaan_flat_{tag}.parquet"
    # Un cache corrupto (run anterior interrumpido o sin memoria) no puede
    # bloquear todo: se borra y se regenera.
    pkl_path = cache_path.with_suffix(".pkl")
    for cp, reader in ((pkl_path, pd.read_pickle), (cache_path, pd.read_parquet)):
        if not (cache and cp.exists()):
            continue
        if cp.stat().st_mtime <= start.stat().st_mtime:
            continue
        if cp.stat().st_size == 0:
            print(f"  cache {cp.name} esta vacio (run anterior interrumpido); "
                  f"lo borro y regenero")
            cp.unlink(missing_ok=True)
            continue
        try:
            if not quiet:
                print(f"  usando cache {cp} (borrala para regenerar)")
            df = reader(cp)
            return df.head(limit) if limit else df
        except Exception as e:
            print(f"  cache {cp.name} ilegible ({type(e).__name__}: {e}); "
                  f"lo borro y regenero")
            cp.unlink(missing_ok=True)

    camp = pd.read_csv(start)
    if not quiet:
        print(f"  campaigns_start.csv: {len(camp)} campanas, "
              f"{len(camp.columns)} columnas")
    cid_col = next((c for c in camp.columns if _norm(c) in
                    ("campaign_id", "campaignid", "campaign")), None)
    if cid_col is None:
        raise SystemExit(f"campaigns_start.csv no tiene campaign_id. "
                         f"Columnas: {list(camp.columns)}")

    frames, missing = [], []
    total_rows, n_sampled, kept = 0, 0, 0
    ids = camp[cid_col].tolist()[: (limit or len(camp))]

    per = sample_per_campaign
    if per is None:
        per = max(1, int(max_rows // max(len(ids), 1))) if max_rows else None
        if not quiet and per is not None:
            print(f"  presupuesto global {max_rows:,} filas / {len(ids):,} "
                  f"campanas = {per:,} inyecciones por campana")
            if per < 200:
                print(f"  (son pocas por campana, pero al ser muestreo uniforme")
                print(f"   las proporciones de clase de cada una se conservan;")
                print(f"   subi --max-rows si necesitas mas resolucion)")
    tasks = []
    for cid in ids:
        path = find_campaign_file(data_dir, int(cid))
        if path is None:
            missing.append(int(cid))
            continue
        meta = camp[camp[cid_col] == cid].iloc[0]
        tasks.append((str(path), per, seed, list(camp.columns),
                      [meta[c] for c in camp.columns]))

    jobs = max(1, int(n_jobs)) if n_jobs else max(1, (os.cpu_count() or 2) - 1)
    t0 = time.time()
    parallel_ok = True
    if jobs > 1 and len(tasks) > 8:
        if not quiet:
            print(f"  leyendo {len(tasks):,} archivos con {jobs} procesos...")
        from concurrent.futures import ProcessPoolExecutor, BrokenExecutor
        try:
            with ProcessPoolExecutor(max_workers=jobs) as ex:
                for i, (sub, total, sm, errmsg) in enumerate(
                        ex.map(_read_one, tasks, chunksize=8)):
                    if errmsg:
                        missing.append(errmsg)
                        continue
                    total_rows += total; n_sampled += sm; kept += len(sub)
                    frames.append(sub)
                    if not quiet and (i + 1) % 500 == 0:
                        el = time.time() - t0
                        eta = el / (i + 1) * (len(tasks) - i - 1)
                        print(f"    {i+1:,}/{len(tasks):,} campanas, {kept:,} filas, "
                              f"{el:.0f}s (faltan ~{eta:.0f}s)")
        except (BrokenExecutor, OSError, NotImplementedError) as e:
            print(f"  !! el pool de procesos se rompio ({type(e).__name__}). "
                  f"Sigo en serie, que es mas lento pero funciona.")
            print(f"     Podes forzarlo desde el principio con --jobs 1.")
            frames.clear(); total_rows = n_sampled = kept = 0
            parallel_ok = False
    if not parallel_ok or not (jobs > 1 and len(tasks) > 8):
        for i, task in enumerate(tasks):
            sub, total, sm, errmsg = _read_one(task)
            if errmsg:
                missing.append(errmsg)
                continue
            total_rows += total; n_sampled += sm; kept += len(sub)
            frames.append(sub)
            if max_rows and kept > max_rows * 1.5:
                print(f"  !! corte en {kept:,} filas ({i+1}/{len(tasks)} campanas)")
                break
            if not quiet and (i + 1) % 500 == 0:
                print(f"    {i+1:,}/{len(tasks):,} campanas, {kept:,} filas...")
    if not quiet:
        print(f"  lectura: {time.time()-t0:.0f}s")

    if missing:
        print(f"  aviso: {len(missing)} campanas sin archivo en data/ "
              f"(ej: {missing[:5]})")
    if not frames:
        raise SystemExit("No se pudo leer ninguna campana.")

    frames = [f for f in frames if len(f)]        # evita la FutureWarning de concat
    n_frames = len(frames)
    df = pd.concat(frames, ignore_index=True)
    del frames
    # Recien aca las columnas de texto pasan a `category`: en el padre, donde no
    # hay que picklear nada entre procesos.
    df = shrink(df)
    if not quiet:
        mem = df.memory_usage(deep=True).sum() / 1e9
        print(f"  total: {len(df):,} filas de inyeccion, {len(df.columns)} "
              f"columnas, {mem:.2f} GB en memoria")
        if n_sampled:
            print(f"  {n_sampled}/{n_frames} campanas muestreadas a {per:,} filas "
                  f"(de {total_rows:,} disponibles en total)")
    if cache and df.memory_usage(deep=True).sum() > 4e9:
        print("  (mas de 4 GB: no lo cacheo, el pickle seria inmanejable)")
        cache = False
    if cache:
        # Escritura ATOMICA: primero a un temporal en el mismo directorio, y
        # recien cuando termino bien, un rename. Si el proceso muere a mitad,
        # queda el temporal y el cache viejo intacto -- nunca un cache truncado.
        def _atomic(target: Path, writer) -> bool:
            fd, tmp = tempfile.mkstemp(dir=str(target.parent),
                                       prefix=".heaan_tmp_", suffix=target.suffix)
            os.close(fd)
            try:
                writer(tmp)
                os.replace(tmp, target)
                return True
            except Exception:
                Path(tmp).unlink(missing_ok=True)
                raise

        try:
            _atomic(cache_path, lambda t: df.to_parquet(t, index=False))
            if not quiet:
                print(f"  cache escrito en {cache_path}")
        except Exception:
            pkl = cache_path.with_suffix(".pkl")
            try:
                _atomic(pkl, lambda t: df.to_pickle(t))
                if not quiet:
                    print(f"  cache escrito en {pkl} (sin pyarrow, use pickle)")
            except Exception as e:
                print(f"  (no pude cachear: {type(e).__name__}: {e})")
                print(f"   seguimos igual, solo que la proxima corrida vuelve a leer todo")
    return df


def read_any(path: str, limit: int | None = None,
             sample_per_campaign: int | None = None,
             max_rows: int | None = 2_000_000,
             n_jobs: int | None = None) -> pd.DataFrame:
    """Acepta un CSV plano o un directorio results/ con el layout de dos niveles."""
    pth = Path(path)
    # Apuntar al directorio results/ o directamente al campaigns_start.csv:
    # las dos formas valen. Si lo que se pasa es el CSV de campanas y al lado
    # hay un data/, es el layout de dos niveles y hay que juntarlo.
    if pth.is_file() and (pth.parent / "data").is_dir() and \
            _norm(pth.stem).startswith("campaigns"):
        print(f"=== {pth.name} con {pth.parent/'data'} al lado: "
              f"layout de dos niveles ===")
        return load_campaigns(str(pth.parent), limit=limit,
                              sample_per_campaign=sample_per_campaign or None,
                              max_rows=max_rows or None, n_jobs=n_jobs)
    if pth.is_dir():
        print(f"=== Cargando layout de campanas desde {pth} ===")
        return load_campaigns(str(pth), limit=limit,
                              sample_per_campaign=sample_per_campaign or None,
                              max_rows=max_rows or None, n_jobs=n_jobs)
    if pth.is_file() and _norm(pth.stem).startswith("campaigns"):
        print(f"  aviso: {pth.name} tiene los parametros por campana pero NO las")
        print(f"         inyecciones (bit, coeff). Esas estan en data/*.csv.gz y")
        print(f"         no encuentro ese directorio al lado de {pth.parent}.")
    return pd.read_csv(path)


def layout(args) -> None:
    """Muestra el esquema real de los dos niveles. Corre esto primero."""
    root = Path(args.root)
    start = root / "campaigns_start.csv"
    if not start.exists():
        raise SystemExit(f"No encuentro {start}")
    camp = pd.read_csv(start)
    print(f"=== {start} ===")
    print(f"  {len(camp)} campanas")
    print("  columnas y cardinalidad:")
    for c in camp.columns:
        u = camp[c].nunique()
        vals = list(camp[c].unique()[:6])
        const = "  <- CONSTANTE, no aporta nada al modelo" if u == 1 else ""
        print(f"    {c:<16} {u:>6} unicos  {vals}{const}")

    data_dir = start.parent / "data"
    gz = sorted(data_dir.glob("*.csv.gz"))
    print(f"\n=== {data_dir} ===")
    print(f"  {len(gz)} archivos .csv.gz")
    if not gz:
        return
    total_bytes = sum(f.stat().st_size for f in gz)
    print(f"  {total_bytes/1e9:.2f} GB comprimidos en total")

    sample = gz[0]
    sub = pd.read_csv(sample, compression="gzip")
    print(f"\n=== esquema de {sample.name} ===")
    print(f"  {len(sub):,} filas  ({sample.stat().st_size/1e6:.1f} MB comprimido)")
    est = len(sub) * len(gz)
    print(f"  => estimado del dataset completo: ~{est:,} filas")
    if est > 20_000_000:
        print(f"  !! Eso no entra en memoria de una. El loader muestrea a")
        print(f"     20.000 filas por campana por defecto "
              f"(~{20000*len(gz):,} filas en total).")
        print(f"     Ajustalo con --sample-per-campaign, o 0 para traer todo.")
    for c in sub.columns:
        u = sub[c].nunique()
        vals = list(sub[c].unique()[:6])
        print(f"    {c:<16} {u:>6} unicos  {vals}")
    print("\n  primeras filas:")
    print(sub.head(5).to_string(max_colwidth=18))

    dup = set(camp.columns) & set(sub.columns)
    if dup:
        print(f"\n  columnas presentes en LOS DOS niveles: {sorted(dup)}")
        print("  (al juntar se conserva la del archivo por campana)")

    print("\n=== Grupos disponibles para el CV ===")
    pipe_cols = [c for c in camp.columns if _norm(c).startswith("do")]
    cfg_cols = [c for c in ["logN", "logQ", "logDelta", "logSlots"] if c in camp.columns]
    if pipe_cols:
        sig = camp[pipe_cols].astype(str).agg("|".join, axis=1)
        print(f"  pipelines distintos (por {pipe_cols}): {sig.nunique()}")
    if cfg_cols:
        cfg = camp[cfg_cols].astype(str).agg("|".join, axis=1)
        print(f"  configuraciones distintas (por {cfg_cols}): {cfg.nunique()}")
    if pipe_cols and sig.nunique() < 3:
        print("  !! Con menos de 3 pipelines distintos no se puede estimar")
        print("     generalizacion a un pipeline nuevo. Hacen falta mas.")



# ---------------------------------------------------------------------------
# 1c. Targets
# ---------------------------------------------------------------------------
# Los csv.gz NO traen una etiqueta: traen CUATRO CONTADORES DE SLOTS.
#   correct + degraded + corrupted + failed == 2^logSlots   (verificado)
# O sea, por cada inyeccion sabemos cuantos de los slots quedaron en cada
# estado. Eso es mas rico que una etiqueta, y ademas mide directamente el
# ESPARCIMIENTO: cuantos slots alcanzo un error inyectado en un solo
# coeficiente. Colapsarlo a una sola clase tira informacion, asi que aca se
# arman varios targets y se elige con --target.

CLASS_COLS = ["correct", "degraded", "corrupted", "failed"]
SEVERITY = {"correct": 0, "degraded": 1, "corrupted": 2, "failed": 3}

# MEDIDO sobre 179.200 inyecciones reales: `class_worst` es EXACTAMENTE
# rel_error umbralado en 0.01 / 0.1 / 10. Reproduce la clase en el 100.000%
# de las filas, sin un solo desacuerdo.
#   correct  : rel_error <  0.01
#   degraded : 0.01 <= rel_error < 0.1
#   corrupted: 0.1  <= rel_error < 10
#   failed   : rel_error >= 10
# Consecuencia: las 4 clases NO son un problema de clasificacion aparte. Son la
# regresion sobre la magnitud, con umbrales conocidos. Entrenar un clasificador
# de 4 clases tira la estructura ordinal Y los umbrales, que ya sabemos.
CLASS_THRESHOLDS = [0.01, 0.1, 10.0]
LOG2_THRESHOLDS = [float(np.log2(t)) for t in CLASS_THRESHOLDS]


def classes_from_log2(l2: np.ndarray) -> np.ndarray:
    """log2(rel_error) -> clase, con los umbrales medidos."""
    a, b, c = LOG2_THRESHOLDS
    return np.select([l2 < a, l2 < b, l2 < c],
                     ["correct", "degraded", "corrupted"],
                     default="failed").astype(object)


def detect_class_columns(df: pd.DataFrame) -> list[str] | None:
    lookup = {_norm(c): c for c in df.columns}
    hit = [lookup[c] for c in CLASS_COLS if c in lookup]
    return hit if len(hit) == len(CLASS_COLS) else None


def build_targets(df: pd.DataFrame, cols: dict, quiet: bool = False) -> pd.DataFrame:
    """Arma todos los targets posibles a partir de lo que haya en el CSV."""
    out = pd.DataFrame(index=df.index)
    ccols = detect_class_columns(df)

    if ccols:
        counts = df[ccols].to_numpy(dtype=float)
        total = counts.sum(axis=1)
        if cols.get("logSlots"):
            slots = np.power(2.0, pd.to_numeric(df[cols["logSlots"]],
                                                errors="coerce").fillna(0).to_numpy())
            bad = np.abs(total - slots) > 1e-6
            if bad.any() and not quiet:
                print(f"  aviso: en {bad.mean():.1%} de las filas los 4 contadores "
                      f"no suman 2^logSlots. Reviso esa suposicion.")
        with np.errstate(divide="ignore", invalid="ignore"):
            frac = counts / np.maximum(total[:, None], 1)

        # clase de la fila = el PEOR estado que alcanzo algun slot.
        # Es la definicion conservadora: "algo salio mal en esta inyeccion".
        worst = np.zeros(len(df), dtype=int)
        for i, name in enumerate(CLASS_COLS):
            worst = np.where(counts[:, i] > 0, np.maximum(worst, SEVERITY[name]), worst)
        inv = {v: k for k, v in SEVERITY.items()}
        out["class_worst"] = [inv[w] for w in worst]

        # clase dominante = la que se llevo mas slots
        out["class_major"] = [CLASS_COLS[i] for i in counts.argmax(axis=1)]

        # esparcimiento: cuantos slots dejaron de estar correctos
        out["n_affected"] = total - counts[:, CLASS_COLS.index("correct")]
        out["frac_affected"] = 1.0 - frac[:, CLASS_COLS.index("correct")]
        out["is_any_error"] = (out["n_affected"] > 0).astype(int)
        # 0 = ningun slot, 1 = exactamente uno (error localizado),
        # 2 = varios pero no todos, 3 = todos (esparcimiento total)
        out["spread"] = np.select(
            [out.n_affected == 0, out.n_affected == 1, out.n_affected >= total],
            ["ninguno", "un_slot", "todos"], default="parcial")
        for i, name in enumerate(CLASS_COLS):
            out[f"frac_{name}"] = frac[:, i]

    if cols.get("label"):          # esquema simple: una columna de etiqueta
        out["label"] = df[cols["label"]].astype(str).to_numpy()
        if "class_worst" not in out.columns:
            out["class_worst"] = out["label"]

    if cols.get("rel_error"):
        re_ = pd.to_numeric(df[cols["rel_error"]], errors="coerce").fillna(0.0)
        out["rel_error"] = re_.to_numpy()
        # log2 con piso: rel_error == 0 es "no paso nada", no -infinito
        with np.errstate(divide="ignore"):
            l = np.log2(np.maximum(re_.to_numpy(), 1e-12))
        out["log2_rel_error"] = np.clip(l, -40, 80)

    if not quiet:
        print("  targets disponibles: " + ", ".join(out.columns))
    return out


def resolve_target(targets: pd.DataFrame, name: str) -> tuple[np.ndarray, bool]:
    """Devuelve (y, es_regresion)."""
    alias = {"class": "class_worst", "clase": "class_worst",
             "rel_error": "log2_rel_error", "error": "log2_rel_error"}
    col = alias.get(name, name)
    if col not in targets.columns:
        raise SystemExit(
            f"target '{name}' no disponible. Hay: {list(targets.columns)}")
    y = targets[col].to_numpy()
    return y, col in ("log2_rel_error", "rel_error", "n_affected", "frac_affected")


# ---------------------------------------------------------------------------
# 2. Parseo del pipeline
# ---------------------------------------------------------------------------

OP_ALIASES = {
    "add": "add", "doadd": "add", "cadd": "add", "addconst": "add",
    "mul": "mul", "domul": "mul", "cmul": "mul", "multiply": "mul",
    "plainmul": "pmul", "doplainmul": "pmul", "pmul": "pmul", "pmult": "pmul",
    "multbyconst": "pmul", "multplain": "pmul",
    "scalarmul": "smul", "doscalarmul": "smul", "smul": "smul",
    "multbyscalar": "smul", "multconst": "smul",
    "rot": "rot", "dorot": "rot", "rotate": "rot", "leftrot": "rot",
    "boot": "boot", "doboot": "boot", "bootstrap": "boot", "dobootstrap": "boot",
}

# Ops que hacen una multiplicacion POLINOMIAL y por lo tanto esparcen un error
# de UN coeficiente a TODOS los demas (convolucion negaciclica):
#   mul   -> multiplicacion + relinearizacion (key switching)
#   pmul  -> multiplicacion por un POLINOMIO plaintext
#   rot   -> key switching, que internamente es una mult por la evk
#   boot  -> muchas de las anteriores
#
# Las que NO esparcen (actuan coeficiente a coeficiente):
#   add   -> suma
#   smul  -> multiplicacion por un ESCALAR. Esta es la distincion que importa:
#            `doScalarMul` multiplica cada coeficiente por una constante, asi
#            que un error en el coeficiente i se queda en el coeficiente i.
#            `doPlainMul` multiplica por un polinomio y si esparce. Meterlas
#            en la misma bolsa seria un error.
#
# OJO: que `rot` cuente como "spreader" es una HIPOTESIS a testear contra los
# datos. Con --polymul-set narrow se cuentan solo mul/pmul/boot.
POLYMUL_WIDE = {"mul", "pmul", "rot", "boot"}
POLYMUL_NARROW = {"mul", "pmul", "boot"}

# Ops que consumen un nivel (bajan logQ en logDelta) al rescalar.
# scalarMul tambien rescala aunque no esparza.
LEVEL_CONSUMING = {"mul", "pmul", "smul"}


def parse_pipeline(value) -> list[str] | None:
    """'doMul,doRot,doAdd' -> ['mul','rot','add']. None si no se puede parsear."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    for sep in [",", ";", "|", ">", "->", " "]:
        if sep in s:
            parts = [p for p in s.replace("->", ",").replace(">", ",")
                     .replace(";", ",").replace("|", ",").replace(" ", ",").split(",")
                     if p]
            break
    else:
        parts = [s]
    ops = []
    for p in parts:
        key = _norm(p).replace("_", "")
        if key in OP_ALIASES:
            ops.append(OP_ALIASES[key])
        else:
            return None
    return ops or None


def pipeline_from_counts(row: pd.Series, cols: dict[str, str | None]) -> list[str]:
    """Sin orden explicito, reconstruye un pipeline canonico desde los conteos.

    Orden canonico: pmul, mul, rot, add, boot. Es una APROXIMACION -- si tu CSV
    no guarda el orden real, las features de 'que viene despues' son aproximadas
    y el modelo va a rendir peor de lo que podria. Guardar la secuencia ordenada
    es la mejora individual mas grande que le podes hacer al dataset.
    """
    ops: list[str] = []
    for canon, op in [("doPlainMul", "pmul"), ("doMul", "mul"),
                      ("doScalarMul", "smul"), ("doRot", "rot"),
                      ("doAdd", "add"), ("doBoot", "boot")]:
        col = cols.get(canon)
        if col is None:
            continue
        try:
            n = int(float(row[col]))
        except (TypeError, ValueError):
            n = 0
        ops.extend([op] * max(0, n))
    return ops


# ---------------------------------------------------------------------------
# 3. Featurizer
# ---------------------------------------------------------------------------

@dataclass
class FeatConfig:
    clip: float = 32.0          # recorte de las features en bits
    count_clip: int = 3         # recorte de los conteos de ops
    gap_formula: str = "pow2"   # 'pow2' -> 2^(logN-1-logSlots) | 'ratio' -> (logN-1)/logSlots
    polymul_set: str = "wide"   # 'wide' incluye rot | 'narrow' solo mul/pmul
    boot_restores_to: float | None = None  # None -> restaura a logQ inicial
    include_raw_scale: bool = False        # incluir logQ/logDelta crudos (rompe transfer)
    # Etapas que trabajan sobre el PLAINTEXT y no sobre el ciphertext. Ahi el
    # modulo de trabajo no es q: en HEAAN el encode vive en un modulo mas grande,
    # asi que `bit - logQ` mide contra la referencia equivocada y todo el eje bit
    # queda corrido. `--encode-ref` elige contra que medir.
    plaintext_stages: tuple = ("encode", "decode", "encodesingle")
    encode_ref: str = "q"                  # 'q' | '2q' | 'bpc'
    stage_vocab: tuple = ()                # se fija en train, se reusa en predict
    feature_names: list[str] = field(default_factory=list)


def slot_gap(logN: float, logSlots: float, formula: str) -> float:
    """Distancia entre coeficientes que caen en el mismo slot.

    'pow2'  : N/(2*slots) = 2^(logN-1-logSlots)  <- lo estandar en CKKS
    'ratio' : (logN-1)/logSlots                  <- literal de como lo escribiste

    Los dos estan implementados porque tu nota decia `coeff % ((logN-1)/logSlots)`
    y no me queda claro si era la formula o la taquigrafia. Corre las dos y
    quedate con la que separa mejor las clases -- `inspect` te lo dice.
    """
    if formula == "ratio":
        denom = max(1.0, float(logSlots))
        return max(1.0, (float(logN) - 1.0) / denom)
    return float(2.0 ** max(0.0, float(logN) - 1.0 - float(logSlots)))


def featurize(df: pd.DataFrame, cols: dict[str, str | None],
              cfg: FeatConfig) -> tuple[pd.DataFrame, pd.Series]:
    """Devuelve (X, pipeline_signature)."""
    C, KC = cfg.clip, cfg.count_clip
    poly = POLYMUL_WIDE if cfg.polymul_set == "wide" else POLYMUL_NARROW

    g = lambda canon, default=0.0: (
        pd.to_numeric(df[cols[canon]], errors="coerce").fillna(default)
        if cols.get(canon) else pd.Series(default, index=df.index, dtype=float))

    logN, logDelta = g("logN"), g("logDelta")
    logQ, logSlots = g("logQ"), g("logSlots")
    bit, coeff = g("bit"), g("coeff")

    n = len(df)
    est_gb = n * 45 * 4 / 1e9
    if est_gb > 1.0:
        print(f"  atencion: {n:,} filas x ~45 features en float32 ~= "
              f"{est_gb:.1f} GB solo para la matriz,")
        print(f"            y el entrenamiento necesita mas encima. Si la maquina")
        print(f"            tiene menos de {est_gb*3:.0f} GB libres, baja "
              f"--sample-per-campaign\n            o usa --max-rows.")
    feats: dict[str, np.ndarray] = {}

    # --- reconstruir el pipeline y la posicion de la inyeccion ----------------
    # VECTORIZADO. La version anterior iteraba fila por fila y construia listas
    # de Python de largo n: 1.2 GB de pico para 750k filas y 8.3 GB para 5M,
    # que es lo que cuelga una maquina.
    #
    # La observacion que lo arregla: todo lo que depende del circuito depende
    # SOLO de (flags do*, op_step, logQ, logDelta) -- o sea, de la campana, no
    # de la inyeccion. En datos reales eso son unas pocas decenas de
    # combinaciones para millones de filas. Asi que se calcula una vez por
    # combinacion unica y se reparte con indexado numpy.
    pipe_col = cols.get("pipeline")
    step_col = cols.get("op_step")

    flag_cols = {op: cols.get(canon) for canon, op in
                 [("doPlainMul", "pmul"), ("doMul", "mul"), ("doScalarMul", "smul"),
                  ("doRot", "rot"), ("doAdd", "add"), ("doBoot", "boot")]}
    flag_cols = {op: c for op, c in flag_cols.items() if c is not None}

    key_df = pd.DataFrame(index=df.index)
    if pipe_col is not None:
        key_df["_pipe"] = pd.factorize(df[pipe_col].astype(str))[0]
    for op, c in flag_cols.items():
        key_df[f"_f_{op}"] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int32")
    key_df["_step"] = (pd.to_numeric(df[step_col], errors="coerce").fillna(0).astype("int32")
                       if step_col is not None else np.int32(0))
    key_df["_q"] = logQ.to_numpy()
    key_df["_d"] = logDelta.to_numpy()
    if key_df.shape[1] == 0:
        raise SystemExit("No hay ni columna de pipeline ni flags do*; no puedo "
                         "reconstruir el circuito.")

    kcols = list(key_df.columns)
    uniq = key_df.drop_duplicates().reset_index(drop=True)
    uniq["_code"] = np.arange(len(uniq), dtype=np.int32)
    codes = key_df.merge(uniq, on=kcols, how="left")["_code"].to_numpy()
    del key_df

    print(f"  {len(uniq)} combinaciones unicas de (pipeline, punto de "
          f"inyeccion, escala) para {len(df):,} filas")
    if pipe_col is None:
        print("  aviso: no hay columna con la SECUENCIA ORDENADA de ops. Se "
              "reconstruye\n         desde los flags do* con un orden canonico. "
              "Guardar el orden real\n         es la mejora mas grande posible "
              "al dataset.")

    # --- una vuelta por combinacion unica (decenas, no millones) -------------
    U = len(uniq)
    u_mul_b = np.zeros(U); u_poly_b = np.zeros(U)
    u_mul_a = np.zeros(U); u_pmul_a = np.zeros(U); u_rot_a = np.zeros(U)
    u_add_a = np.zeros(U); u_boot_a = np.zeros(U); u_poly_a = np.zeros(U)
    u_opsa = np.zeros(U); u_len = np.zeros(U); u_lvl = np.zeros(U)
    u_sig = np.empty(U, dtype=object)
    pipe_vals = (pd.factorize(df[pipe_col].astype(str))[1]
                 if pipe_col is not None else None)

    for u in range(U):
        row = uniq.iloc[u]
        ops = None
        if pipe_vals is not None:
            ops = parse_pipeline(pipe_vals[int(row["_pipe"])])
        if ops is None:
            ops = []
            for op in flag_cols:
                ops.extend([op] * max(0, int(row[f"_f_{op}"])))
        step = int(np.clip(int(row["_step"]), 0, max(0, len(ops))))
        before, after = ops[:step], ops[step:]

        u_mul_b[u] = sum(1 for o in before if o == "mul")
        u_poly_b[u] = sum(1 for o in before if o in poly)
        u_mul_a[u] = sum(1 for o in after if o == "mul")
        u_pmul_a[u] = sum(1 for o in after if o == "pmul")
        u_rot_a[u] = sum(1 for o in after if o == "rot")
        u_add_a[u] = sum(1 for o in after if o == "add")
        u_boot_a[u] = sum(1 for o in after if o == "boot")
        u_poly_a[u] = sum(1 for o in after if o in poly)
        u_opsa[u] = len(after); u_len[u] = len(ops)
        u_sig[u] = "+".join(ops) if ops else "empty"

        q = float(row["_q"]); d = float(row["_d"])
        restore = cfg.boot_restores_to if cfg.boot_restores_to is not None else q
        lvl = q
        for op in before:
            if op in LEVEL_CONSUMING:
                lvl -= d
            elif op == "boot":
                lvl = restore
        u_lvl[u] = lvl

    # --- repartir por indexado: sin listas de Python, sin copias grandes -----
    mul_before, poly_before = u_mul_b[codes], u_poly_b[codes]
    mul_after, pmul_after = u_mul_a[codes], u_pmul_a[codes]
    rot_after, add_after = u_rot_a[codes], u_add_a[codes]
    boot_after, poly_after = u_boot_a[codes], u_poly_a[codes]
    ops_after, pipe_len = u_opsa[codes], u_len[codes]
    logq_inject = u_lvl[codes]
    # Categorical: guarda codigos int8 + un diccionario chico, en vez de n
    # strings de Python (que para 5M filas son varios GB por si solos).
    # Dos combinaciones distintas (p.ej. mismo pipeline con otro logQ) pueden
    # compartir firma, asi que las categorias hay que deduplicarlas.
    sig_cats, sig_of_u = np.unique(u_sig.astype(str), return_inverse=True)
    sigs_cat = pd.Categorical.from_codes(sig_of_u[codes], categories=list(sig_cats))

    logQ_np, logDelta_np = logQ.to_numpy(), logDelta.to_numpy()

    # --- ruta preferida: op_depth / mult_depth del esquema real -------------
    if cols.get("op_depth") is not None and cols.get("mult_depth") is not None:
        od = g("op_depth").to_numpy()
        md = g("mult_depth").to_numpy()
        mul_before = od
        mul_after = np.maximum(0.0, md - od)
        logq_inject = logQ_np - logDelta_np * od
        poly_after = np.maximum(poly_after, mul_after)
        nb = g("doBoot").to_numpy()
        if float(np.nanmax(nb)) > 0:
            print(f"  aviso: {(nb > 0).mean():.1%} de las filas tienen doBoot>0. "
                  f"Sin el orden de\n         las ops no se sabe DONDE resetea el "
                  f"nivel: logQ_at_inject queda\n         aproximado en esas filas.")
        print("  usando op_depth/mult_depth para el nivel y las mult restantes.")

    # --- referencia de modulo segun la etapa ---------------------------------
    # Las etapas de plaintext (encode) trabajan con un modulo mayor que el de los
    # ciphertext, asi que el mismo `bit` significa algo distinto ahi. Sin esto,
    # `bit_minus_q_inject` mezcla dos escalas y deja de ser invariante -- que es
    # el mismo error que medir `bit` crudo en vez de `bit - logDelta`.
    stage_col = cols.get("stage")
    is_pt = np.zeros(n, dtype=bool)
    if stage_col is not None:
        sv = df[stage_col].astype(str).str.lower().str.replace("_", "", regex=False)
        is_pt = sv.isin(cfg.plaintext_stages).to_numpy()
    if is_pt.any():
        if cfg.encode_ref == "2q":
            ref = 2.0 * logQ_np
        elif cfg.encode_ref == "bpc":
            ref = (g("bitPerCoeff", 64.0).to_numpy() if cols.get("bitPerCoeff")
                   else 2.0 * logQ_np)
        else:
            ref = logQ_np
        logq_inject = np.where(is_pt, ref, logq_inject)
        if cfg.encode_ref != "q":
            print(f"  {is_pt.mean():.1%} de las filas son etapas de plaintext "
                  f"({', '.join(sorted(set(sv[is_pt])))}); su modulo de")
            print(f"  referencia pasa a '{cfg.encode_ref}'. Ojo: sobre 179k "
                  f"inyecciones de encode el")
            print(f"  umbral medido cae en logQ, no en 2logQ. Verificalo con "
                  f"diagnose antes de fiarte.")

    cl = lambda a: np.clip(a, -C, C)
    cc = lambda a: np.clip(a, 0, KC)

    # --- features de escala, relativas y recortadas ---------------------------
    feats["bit_minus_delta"] = cl(bit.to_numpy() - logDelta.to_numpy())
    feats["bit_minus_q_inject"] = cl(bit.to_numpy() - logq_inject)
    feats["is_above_q_inject"] = (bit.to_numpy() >= logq_inject).astype(float)
    feats["is_below_delta"] = (bit.to_numpy() < logDelta.to_numpy()).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        feats["bit_frac_q"] = np.nan_to_num(bit.to_numpy() / np.maximum(logQ.to_numpy(), 1))
        feats["logq_inject_frac"] = np.nan_to_num(logq_inject / np.maximum(logQ.to_numpy(), 1))
        levels_left = (logq_inject - logDelta.to_numpy()) / np.maximum(logDelta.to_numpy(), 1)
    feats["levels_left"] = np.clip(np.nan_to_num(levels_left), -KC, KC)

    # --- features del pipeline, relativas a la inyeccion y recortadas ---------
    feats["n_mul_after"] = cc(mul_after)
    feats["n_pmul_after"] = cc(pmul_after)
    feats["n_rot_after"] = cc(rot_after)
    feats["n_add_after"] = cc(add_after)
    feats["n_boot_after"] = cc(boot_after)
    feats["n_polymul_after"] = cc(poly_after)
    feats["has_polymul_after"] = (poly_after > 0).astype(float)
    feats["n_mul_before"] = cc(mul_before)
    feats["n_polymul_before"] = cc(poly_before)
    with np.errstate(divide="ignore", invalid="ignore"):
        feats["ops_after_frac"] = np.nan_to_num(ops_after / np.maximum(pipe_len, 1))
    feats["pipeline_len"] = np.clip(pipe_len, 0, 8)

    # --- estructura de coeficientes ------------------------------------------
    gap = np.array([slot_gap(logN.iloc[i], logSlots.iloc[i], cfg.gap_formula)
                    for i in range(n)])
    coeff_np = coeff.to_numpy()
    mod = np.mod(coeff_np, np.maximum(gap, 1))
    feats["is_slot_aligned"] = (mod == 0).astype(float)
    # El coeficiente N/2 resulto INMUNE en las 12 campanas medidas, aun siendo
    # multiplo del gap. Mecanismo probable: con isComplex=0 solo se decodifica
    # la parte real, y el coeficiente N/2 alimenta unicamente la componente
    # imaginaria, que se descarta. Prediccion falsable: con isComplex=1 deberia
    # dejar de ser inmune. Por eso entra la feature Y su interaccion.
    is_nyq = (coeff_np == (half_n_pre := np.power(2.0, np.maximum(
        logN.to_numpy() - 1.0, 0.0)))).astype(float)
    feats["is_nyquist_coeff"] = is_nyq
    feats["coeff_mod_gap_frac"] = mod / np.maximum(gap, 1)
    half_n = np.power(2.0, np.maximum(logN.to_numpy() - 1.0, 1.0))
    feats["coeff_frac"] = np.clip(coeff_np / np.maximum(half_n, 1), 0, 2)
    n_slots = np.power(2.0, logSlots.to_numpy())
    feats["slot_idx_frac"] = np.clip(
        np.floor_divide(coeff_np, np.maximum(gap, 1)) / np.maximum(n_slots, 1), 0, 1)

    # --- interacciones explicitas --------------------------------------------
    # Un arbol puede descubrirlas, pero dandoselas hechas necesita menos datos y
    # el modelo queda legible para el paper.
    feats["log2_slots"] = logSlots.to_numpy()
    feats["log2_gap"] = np.log2(np.maximum(gap, 1))
    feats["aligned_x_polymul"] = feats["is_slot_aligned"] * feats["has_polymul_after"]
    feats["nyquist_x_real"] = is_nyq * (1.0 - feats.get(
        "is_complex", np.zeros(n)) if "is_complex" in feats else is_nyq)
    feats["resilient_pattern"] = ((1 - feats["is_slot_aligned"]) *
                                  (1 - feats["has_polymul_after"]))

    # --- features estructurales del esquema real -----------------------------
    # Los flags do* son composicion de pipeline, no identidad: un pipeline nuevo
    # es una combinacion nueva de flags ya vistos, que es justo lo que un arbol
    # sabe recombinar. Por eso entran, PERO el CV tiene que agrupar por firma de
    # pipeline o el numero que salga es mentira.
    for canon, fname in [("doAdd", "do_add"), ("doMul", "do_mul"),
                         ("doPlainMul", "do_pmul"), ("doScalarMul", "do_smul"),
                         ("doRot", "do_rot"), ("doBoot", "do_boot")]:
        if cols.get(canon) is not None:
            feats[fname] = np.clip(g(canon).to_numpy(), 0, KC)

    # withNTT es potencialmente LA variable: si el ciphertext esta en dominio
    # NTT, un bit flip en un coeficiente NTT ya corresponde a un error esparcido
    # en el dominio de coeficientes. Toda la regla de "coeff % gap != 0 es
    # resiliente" solo tiene sentido en UNO de los dos dominios.
    for canon, fname in [("withNTT", "with_ntt"), ("isComplex", "is_complex"),
                         ("dnum", "dnum")]:
        if cols.get(canon) is not None:
            v = pd.to_numeric(df[cols[canon]], errors="coerce")
            if v.isna().all():
                v = pd.Series(pd.factorize(df[cols[canon]])[0], index=df.index)
            feats[fname] = v.fillna(0).to_numpy().astype(float)

    # `stage` como one-hot. Un stage nuevo queda en todo-ceros, que es honesto:
    # el modelo dice "no vi esto" en vez de inventar un orden entre etapas.
    if stage_col is not None:
        vocab = (list(cfg.stage_vocab) if cfg.stage_vocab
                 else sorted(set(df[stage_col].astype(str)))[:12])
        cfg.stage_vocab = tuple(vocab)
        sv_raw = df[stage_col].astype(str).to_numpy()
        for st in vocab:
            feats[f"stage_{st}"] = (sv_raw == st).astype(float)
        feats["is_plaintext_stage"] = is_pt.astype(float)
        # La resiliencia por alineacion a slot NO vale igual en todas las etapas:
        # medido, P(err | NO alineado) va de 0.000 en encode a 0.638 en
        # encrypt_c1. O sea que `is_slot_aligned` solo discrimina donde la
        # estructura de slots sigue intacta. Sin esta interaccion el arbol tiene
        # que redescubrirla rama por rama.
        for st in vocab:
            feats[f"aligned_x_{st}"] = (feats["is_slot_aligned"] *
                                        feats[f"stage_{st}"])

    if cols.get("mult_depth") is not None:
        feats["mult_depth"] = np.clip(g("mult_depth").to_numpy(), 0, 8)
    if cols.get("op_depth") is not None:
        feats["op_depth"] = np.clip(g("op_depth").to_numpy(), 0, 8)
    if cols.get("bitPerCoeff") is not None:
        bpc = g("bitPerCoeff", 64.0).to_numpy()
        feats["bit_frac_word"] = np.clip(bit.to_numpy() / np.maximum(bpc, 1), 0, 2)
        feats["logq_frac_word"] = np.clip(logQ.to_numpy() / np.maximum(bpc, 1), 0, 2)
        # referencias alternativas: si la etapa corre el origen del eje bit, una
        # de estas es la invariante correcta. Que decida el dato, no yo.
        feats["bit_minus_bpc"] = cl(bit.to_numpy() - bpc)
        # Cuando logQ es la cadena RNS completa, el modulo relevante para un bit
        # flip es el del limb (~bitPerCoeff), no la cadena. Se toma el menor de
        # los dos: si el coeficiente es mas angosto que logQ, manda el
        # coeficiente.
        eff = np.minimum(logq_inject, bpc)
        feats["bit_minus_eff_mod"] = cl(bit.to_numpy() - eff)
        feats["is_above_eff_mod"] = (bit.to_numpy() >= eff).astype(float)
    feats["bit_minus_2logq"] = cl(bit.to_numpy() - 2.0 * logQ_np)

    if cfg.include_raw_scale:
        feats["logQ_raw"] = logQ.to_numpy()
        feats["logDelta_raw"] = logDelta.to_numpy()
        feats["logN_raw"] = logN.to_numpy()
        feats["logSlots_raw"] = logSlots.to_numpy()
        feats["bit_raw"] = bit.to_numpy()

    # float32 en vez de float64: HistGradientBoosting bina a uint8 igual, asi
    # que la mitad de la memoria no aportaba nada. Se convierte in-place para
    # que el array de float64 se libere feature por feature y no se acumulen.
    for _k in list(feats):
        feats[_k] = np.asarray(feats[_k], dtype=np.float32)
    X = pd.DataFrame(feats, index=df.index, copy=False)
    del feats
    cfg.feature_names = list(X.columns)
    # guardadas para el baseline de regla
    X.attrs["logq_inject"] = logq_inject
    X.attrs["bit"] = bit.to_numpy()
    X.attrs["logDelta"] = logDelta.to_numpy()
    return X, pd.Series(sigs_cat, index=df.index, name="pipeline_sig")


# ---------------------------------------------------------------------------
# 4. Baseline de regla explicita (la fisica que ya dedujiste a mano)
# ---------------------------------------------------------------------------

def rule_is_error(X: pd.DataFrame, slack: float = 0.0) -> np.ndarray:
    """Predice si la inyeccion produce ALGUN error visible. Regla, no modelo.

    Medido sobre las 12 campanas reales de stage=encode:

    1. `coeff % 2^(logN-1-logSlots) != 0`  -> NUNCA hay error (0.0000 de tasa).
       Esa es la formula correcta del gap; la variante (logN-1)/logSlots deja
       pasar un 0.96% de falsos, o sea no es.
    2. `coeff == N/2` -> tampoco hay error, aun siendo multiplo del gap.
       Inmune en las 12 campanas.
    3. `bit >= logQ` es NECESARIO: con slack=0 el recall sobre los errores
       reales ya es 1.000 (cero falsos negativos en 21.698 errores). Subir el
       slack solo agrega falsos positivos, por eso el default es 0.

    Lo que la regla NO puede hacer es predecir la SEVERIDAD. Arriba de logQ el
    error vale 2^bit mod q, que depende del primo q concreto y no del ancho en
    bits, asi que la magnitud es pseudoaleatoria desde el punto de vista de los
    parametros. La regla es una sobre-aproximacion SANA: descarta con certeza,
    no confirma.
    """
    aligned = X["is_slot_aligned"].to_numpy() > 0.5
    nyquist = X.get("is_nyquist_coeff", pd.Series(np.zeros(len(X)))).to_numpy() > 0.5
    above = X["bit_minus_q_inject"].to_numpy() >= -slack
    return aligned & (~nyquist) & above


def rule_baseline(X: pd.DataFrame, target: str = "class_worst",
                  slack: float = 0.0) -> np.ndarray:
    """Baseline de regla adaptado al target pedido."""
    err = rule_is_error(X, slack)
    if target in ("is_any_error",):
        return err.astype(int)
    if target in ("log2_rel_error", "rel_error", "n_affected", "frac_affected"):
        # magnitud esperada: el bit por encima del factor de escala
        mag = X["bit_minus_delta"].to_numpy()
        return np.where(err, mag, -40.0)
    # clases: magnitud esperada -> umbrales medidos. Abajo de logQ la ley es
    # limpia (log2(rel_error) = bit - logDelta); arriba es pseudoaleatoria, y
    # ahi la regla necesariamente falla en la severidad aunque acierte el
    # "hay error". Eso se ve en el reporte binario que se imprime al lado.
    mag = X["bit_minus_delta"].to_numpy()
    out = classes_from_log2(np.where(err, mag, -40.0))
    out[~err] = "correct"
    return out


# ---------------------------------------------------------------------------
# 5. Metricas
# ---------------------------------------------------------------------------

def report_reg(y_true, y_pred, title: str) -> dict:
    from sklearn.metrics import mean_absolute_error, r2_score
    y_true = np.asarray(y_true, float); y_pred = np.asarray(y_pred, float)
    mae = mean_absolute_error(y_true, y_pred)
    base = mean_absolute_error(y_true, np.full_like(y_true, np.median(y_true)))
    r2 = r2_score(y_true, y_pred)
    print(f"\n--- {title} ---")
    print(f"  MAE      : {mae:.3f}   (baseline mediana {base:.3f}, "
          f"mejora {base-mae:+.3f})")
    print(f"  R2       : {r2:.4f}")
    print(f"  el target esta en bits (log2), asi que MAE={mae:.2f} significa "
          f"errar por un factor 2^{mae:.2f}")
    return {"macro_f1": r2, "accuracy": -mae, "baseline_acc": -base,
            "lift": base - mae, "mae": mae, "r2": r2}


def report(y_true, y_pred, title: str) -> dict:
    from sklearn.metrics import (accuracy_score, f1_score, confusion_matrix,
                                 classification_report)
    y_true = np.asarray(y_true).astype(str)
    y_pred = np.asarray(y_pred).astype(str)
    acc = accuracy_score(y_true, y_pred)
    macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    vals, counts = np.unique(y_true, return_counts=True)
    base = counts.max() / counts.sum()
    print(f"\n--- {title} ---")
    print(f"  macro F1 : {macro:.4f}")
    print(f"  accuracy : {acc:.4f}   (baseline mayoria {base:.4f}, "
          f"lift {acc-base:+.4f})")
    labels = sorted(set(y_true.tolist()) | set(y_pred.tolist()))
    print("  matriz de confusion (filas=real, cols=predicho):",
          "  ".join(f"{l}" for l in labels))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    for lab, row in zip(labels, cm):
        print(f"    {lab:<12} {row}")
    print(classification_report(y_true, y_pred, zero_division=0, digits=3))
    return {"macro_f1": macro, "accuracy": acc, "baseline_acc": base,
            "lift": acc - base}


# ---------------------------------------------------------------------------
# 6. Entrenamiento
# ---------------------------------------------------------------------------

def pipeline_signature(df: pd.DataFrame, cols: dict, sigs: pd.Series) -> pd.Series:
    """Firma del pipeline. Prefiere los flags do* del esquema real."""
    flag_cols = [cols[c] for c in ["doAdd", "doMul", "doPlainMul", "doScalarMul",
                                   "doRot", "doBoot"] if cols.get(c)]
    if cols.get("mult_depth"):
        flag_cols.append(cols["mult_depth"])
    if flag_cols:
        return df[flag_cols].astype(str).agg("|".join, axis=1)
    return sigs


def build_groups(df: pd.DataFrame, cols: dict, sigs: pd.Series,
                 split: str) -> pd.Series:
    if split == "pipeline":
        return pipeline_signature(df, cols, sigs)
    if split == "campaign":
        if cols.get("campaign_id"):
            return df[cols["campaign_id"]].astype(str)
        raise SystemExit("--split campaign necesita la columna campaign_id.")
    if split == "stage":
        # Leave-one-stage-out. Es la pregunta honesta cuando el regimen fisico
        # lo define la etapa y no el pipeline: mide cuanto de lo aprendido en
        # unas etapas sirve en una que nunca se vio.
        if cols.get("stage"):
            return df[cols["stage"]].astype(str)
        raise SystemExit("--split stage necesita la columna stage.")
    if split == "stage_x_config":
        keys = [cols[c] for c in ["logN", "logDelta", "logQ", "logSlots"]
                if cols.get(c)]
        if not cols.get("stage"):
            raise SystemExit("--split stage_x_config necesita la columna stage.")
        return (df[cols["stage"]].astype(str) + "//" +
                df[keys].astype(str).agg("|".join, axis=1))
    if split == "config":
        keys = [cols[c] for c in ["logN", "logDelta", "logQ", "logSlots"] if cols.get(c)]
        return df[keys].astype(str).agg("|".join, axis=1)
    if split == "both":
        keys = [cols[c] for c in ["logN", "logDelta", "logQ", "logSlots"] if cols.get(c)]
        return (df[keys].astype(str).agg("|".join, axis=1) + "//" +
                pipeline_signature(df, cols, sigs))
    raise ValueError(split)


def train(args) -> None:
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)
    from sklearn.model_selection import GroupKFold
    from sklearn.utils.class_weight import compute_sample_weight

    df = read_any(args.csv, getattr(args, "limit", None),
                  getattr(args, "sample_per_campaign", None),
                  getattr(args, "max_rows", 2_000_000),
                  getattr(args, "jobs", None))
    overrides = dict(kv.split("=", 1) for kv in (args.col or []))
    cols = resolve_columns(df, overrides)
    print_resolution(cols, df)

    missing = [c for c in REQUIRED if cols.get(c) is None]
    if missing:
        raise SystemExit(f"\nNo puedo seguir: faltan {missing}.")


    cfg = FeatConfig(clip=args.clip, count_clip=args.count_clip,
                     gap_formula=args.gap_formula, polymul_set=args.polymul_set,
                     boot_restores_to=args.boot_restores_to,
                     include_raw_scale=args.include_raw_scale,
                     encode_ref=getattr(args, "encode_ref", "q"))

    sc0 = cols.get("stage")
    only = getattr(args, "only_stage", None)
    excl = getattr(args, "exclude_stage", None)
    if sc0 is not None and (only or excl):
        sv0 = df[sc0].astype(str)
        n0 = len(df)
        if only:
            df = df[sv0.isin(only)]
        if excl:
            df = df[~df[sc0].astype(str).isin(excl)]
        df = df.reset_index(drop=True)
        print(f"  filtro de etapas: {n0:,} -> {len(df):,} filas "
              f"({sorted(set(df[sc0].astype(str)))})")
        if df.empty:
            raise SystemExit("El filtro de etapas no dejo ninguna fila.")

    mr = getattr(args, "max_rows", None)
    if mr and len(df) > mr:
        print(f"  --max-rows: muestreo {mr:,} de {len(df):,} filas antes de "
              f"featurizar")
        df = df.sample(n=mr, random_state=args.seed).reset_index(drop=True)

    print("\n=== Featurizando ===")
    X, sigs = featurize(df, cols, cfg)
    tg = build_targets(df, cols)
    if tg.empty:
        raise SystemExit(
            "No encontre ni los contadores de clase (correct/degraded/"
            "corrupted/failed) ni rel_error en los csv.gz. Sin target no hay "
            "nada que entrenar.")
    y, is_reg = resolve_target(tg, args.target)
    print(f"  target: {args.target}  ({'regresion' if is_reg else 'clasificacion'})")
    HGB = (HistGradientBoostingRegressor if is_reg
           else HistGradientBoostingClassifier)
    rep = report_reg if is_reg else report
    X_full = X.copy()          # la regla siempre usa el set completo
    drop = [c for c in getattr(args, "drop_features", []) or [] if c in X.columns]
    if drop:
        X = X.drop(columns=drop)
        print(f"  features excluidas del MODELO: {drop}")
        print("  (el baseline de regla sigue usando el set completo)")
    print(f"  {X.shape[0]} filas, {X.shape[1]} features")
    if is_reg:
        floor = float(np.min(y))
        at_floor = float(np.mean(np.isclose(y, floor)))
        print(f"  target continuo: min={y.min():.2f} mediana={np.median(y):.2f} "
              f"max={y.max():.2f}")
        if at_floor > 0.05:
            print(f"  OJO: {at_floor:.1%} de las filas estan en el piso "
                  f"({floor:.1f}) = 'no paso nada'.")
            print(f"       El target esta inflado en cero: gran parte del R2 sale")
            print(f"       de acertar SI hay error, no CUANTO. Mira tambien la")
            print(f"       metrica condicional de abajo.")
    else:
        vals, cnts = np.unique(y, return_counts=True)
        print(f"  clases: {dict(zip(vals.tolist(), cnts.tolist()))}")
    psig = pipeline_signature(df, cols, sigs)
    print(f"  pipelines distintos: {psig.nunique()}")
    if cols.get("campaign_id"):
        ncamp = df[cols["campaign_id"]].nunique()
        print(f"  campanas: {ncamp}  ({len(df)/max(ncamp,1):.0f} inyecciones por campana)")
        if psig.nunique() < 3:
            print("  !! Menos de 3 pipelines distintos: no se puede estimar")
            print("     generalizacion a un pipeline nuevo con estos datos.")

    # ---- baseline de regla, sobre TODO el dataset ---------------------------
    rule_pred = rule_baseline(X_full, args.target)
    rule_m = rep(y, rule_pred, "BASELINE DE REGLA (fisica medida, sin entrenar)")

    # ---- modo test-csv: entrenar en todo esto, testear en otro archivo -------
    if getattr(args, "test_csv", None):
        df_te = read_any(args.test_csv, None,
                         getattr(args, "sample_per_campaign", None),
                         getattr(args, "max_rows", 2_000_000),
                  getattr(args, "jobs", None))
        cols_te = resolve_columns(df_te, overrides)
        print(f"\n=== Test externo: {args.test_csv} ({len(df_te)} filas) ===")
        X_te_full, sigs_te = featurize(df_te, cols_te, cfg)
        X_te = align_features(X_te_full.copy(), list(X.columns), strict=True)
        y_te, _ = resolve_target(build_targets(df_te, cols_te, quiet=True),
                                 args.target)

        overlap = set(sigs) & set(sigs_te)
        print(f"  pipelines del test ya vistos en train: {len(overlap)}"
              f"/{sigs_te.nunique()}")
        # reporte de extrapolacion: que fraccion del test cae fuera del rango
        oor = {}
        for c in X.columns:
            lo, hi = X[c].min(), X[c].max()
            frac = float(((X_te[c] < lo) | (X_te[c] > hi)).mean())
            if frac > 0.01:
                oor[c] = frac
        if oor:
            print("  features con filas FUERA del rango de entrenamiento:")
            for c, f in sorted(oor.items(), key=lambda kv: -kv[1]):
                flag = "  <-- 100% fuera de rango, sacala" if f > 0.99 else ""
                print(f"    {c:<22} {f:6.1%}{flag}")
        else:
            print("  ninguna feature se sale del rango de entrenamiento.")

        rule_te = rep(y_te, rule_baseline(X_te_full, args.target),
                      "BASELINE DE REGLA sobre el test")

        model = HGB(max_depth=args.max_depth, learning_rate=args.lr,
                    max_iter=args.max_iter, l2_regularization=1.0,
                    random_state=args.seed)
        sw = (compute_sample_weight("balanced", y)
              if args.class_weight == "balanced" and not is_reg else None)
        model.fit(X, y, sample_weight=sw)
        m = rep(y_te, model.predict(X_te),
                "MODELO entrenado en train -> test externo")

        print("\n=== Veredicto ===")
        print(f"  CV en train (regla)   macro F1 = {rule_m['macro_f1']:.4f}")
        print(f"  regla sobre test      macro F1 = {rule_te['macro_f1']:.4f}")
        print(f"  modelo sobre test     macro F1 = {m['macro_f1']:.4f}   "
              f"(lift {m['lift']:+.4f})")
        if m["macro_f1"] < rule_te["macro_f1"] - 0.01:
            print("  -> El modelo aprendido transfiere PEOR que la regla escrita")
            print("     a mano. Sintoma clasico de features que no son")
            print("     invariantes: mira arriba que features se salen de rango.")
        if m["lift"] < 0.05:
            print(f"  !! lift {m['lift']:+.4f}: el modelo no le gana a predecir")
            print("     siempre la clase mayoritaria.")
        if args.save:
            import joblib
            joblib.dump(make_bundle(model, cols, cfg, X, y, df, sigs,
                                    args.target, is_reg), args.save)
            print(f"\nModelo guardado en {args.save}")
        return

    # ---- split ---------------------------------------------------------------
    if args.split == "depth":
        # La profundidad multiplicativa real le gana al largo reconstruido.
        if "mult_depth" in X.columns:
            lens, dname = X["mult_depth"].to_numpy(), "mult_depth"
        else:
            lens, dname = X["pipeline_len"].to_numpy(), "largo de pipeline"
        vals = np.unique(lens)
        if len(vals) < 2:
            raise SystemExit(
                f"split 'depth': todas las filas tienen {dname}={vals[0]:.0f}. "
                f"No hay nada que extrapolar; usa --split pipeline.")
        thr = np.median(lens)
        tr, te = lens <= thr, lens > thr
        if te.sum() == 0 or tr.sum() == 0:      # mediana pegada a un extremo
            thr = vals[len(vals) // 2 - 1] if te.sum() == 0 else vals[0]
            tr, te = lens <= thr, lens > thr
        if te.sum() == 0 or tr.sum() == 0:
            raise SystemExit(f"split 'depth': no pude partir por {dname} "
                             f"(valores: {vals}). Usa --split pipeline.")
        print(f"\n=== Split por profundidad ({dname}): "
              f"train <={thr:.0f} ({tr.sum():,} filas), "
              f"test >{thr:.0f} ({te.sum():,} filas) ===")
        print(f"    valores de {dname} en el dataset: {vals.astype(int).tolist()}")
        folds = [(np.where(tr)[0], np.where(te)[0])]
    else:
        groups = build_groups(df, cols, sigs, args.split)
        ng = groups.nunique()
        print(f"\n=== Split '{args.split}': {ng} grupos distintos ===")
        if ng < 2:
            raise SystemExit(
                f"Solo hay {ng} grupo con --split {args.split}. No hay forma de "
                f"estimar generalizacion a un grupo nuevo. Necesitas datos con "
                f"varios valores de ese grupo.")
        k = min(args.folds, ng)
        folds = list(GroupKFold(n_splits=k).split(X, y, groups=groups))

    # ---- CV ------------------------------------------------------------------
    oof_pred = np.empty(len(y), dtype=float if is_reg else object)
    oof_mask = np.zeros(len(y), dtype=bool)
    for fi, (tr_i, te_i) in enumerate(folds):
        model = HGB(max_depth=args.max_depth, learning_rate=args.lr,
                    max_iter=args.max_iter, l2_regularization=1.0,
                    random_state=args.seed)
        sw = (compute_sample_weight("balanced", y[tr_i])
              if args.class_weight == "balanced" and not is_reg else None)
        model.fit(X.iloc[tr_i], y[tr_i], sample_weight=sw)
        oof_pred[te_i] = model.predict(X.iloc[te_i])
        oof_mask[te_i] = True
        # chequeo de honestidad
        if args.split != "depth":
            gtr = set(groups.iloc[tr_i]); gte = set(groups.iloc[te_i])
            leak = gtr & gte
            if leak:
                print(f"  !! fold {fi}: {len(leak)} grupos aparecen en train Y test. "
                      f"El CV esta inflado.")

    model_m = rep(y[oof_mask], oof_pred[oof_mask],
                  f"MODELO hgb, split '{args.split}' (out-of-fold)")
    if is_reg:
        floor = float(np.min(y))
        real = oof_mask & ~np.isclose(y, floor)
        if real.sum() > 50:
            rep(y[real], oof_pred[real],
                "MODELO solo en las filas que SI tuvieron error (condicional)")
        # DOS ETAPAS: regresion -> umbrales conocidos -> clases.
        # Comparable directo contra entrenar un clasificador de 4 clases.
        if args.target == "log2_rel_error" and "class_worst" in tg.columns:
            yc = tg["class_worst"].to_numpy()[oof_mask]
            pc = classes_from_log2(np.asarray(oof_pred[oof_mask], float))
            report(yc, pc, "MISMO MODELO, umbralado a las 4 clases "
                           "(regresion -> 0.01/0.1/10)")
            print("  ^ compara esto contra `--target class_worst`: mismo problema,")
            print("    pero aprovechando el orden de las clases y los umbrales.")
    else:
        # la regla solo determina SI hay error, no la severidad: el numero
        # comparable es el binario.
        if len(np.unique(y)) > 2:
            yb = (np.asarray(y, dtype=object) != "correct").astype(int)
            rb = (np.asarray(rule_pred, dtype=object) != "correct").astype(int)
            mb = (np.asarray(oof_pred[oof_mask], dtype=object) != "correct").astype(int)
            print("\n" + "=" * 62)
            print("Colapsado a binario (hay error / no hay error) -- que es lo")
            print("unico que la fisica determina:")
            report(yb, rb, "REGLA, binario")
            report(yb[oof_mask], mb, "MODELO, binario")

    # ---- veredicto -----------------------------------------------------------
    # Con una etapa acaparando el 80% de las filas, la metrica global es esa
    # etapa y nada mas. Las chicas quedan invisibles.
    sc_ = cols.get("stage")
    if sc_ is not None and df[sc_].nunique() > 1 and oof_mask.sum():
        from sklearn.metrics import f1_score
        print("\n=== Desempeno por etapa (donde funciona y donde no) ===")
        print(f"  {'stage':<22}{'filas':>10}{'%total':>8}"
              f"{'macro F1' if not is_reg else 'MAE':>10}")
        sv_ = df[sc_].astype(str).to_numpy()
        for st in sorted(set(sv_)):
            m_ = oof_mask & (sv_ == st)
            if m_.sum() < 50:
                continue
            if is_reg:
                v = float(np.mean(np.abs(np.asarray(y[m_], float) -
                                         np.asarray(oof_pred[m_], float))))
            else:
                v = f1_score(np.asarray(y[m_]).astype(str),
                             np.asarray(oof_pred[m_]).astype(str),
                             average="macro", zero_division=0)
            print(f"  {st:<22}{m_.sum():>10,}{m_.sum()/len(df):>7.1%}{v:>10.3f}")
        print("  Si una etapa se lleva casi todas las filas, el numero global es")
        print("  el de esa etapa. Mira esta tabla antes de sacar conclusiones.")

    print("\n=== Veredicto ===")
    metric = "R2" if is_reg else "macro F1"
    d = model_m["macro_f1"] - rule_m["macro_f1"]
    print(f"  regla    {metric} = {rule_m['macro_f1']:.4f}")
    print(f"  modelo   {metric} = {model_m['macro_f1']:.4f}   ({d:+.4f})")
    if d < 0.01:
        print("  -> El modelo NO le gana a la regla. O la fisica ya esta toda")
        print("     capturada por la regla (buena noticia para el paper), o a las")
        print("     features les falta la variable que explica el resto.")
    else:
        print("  -> El modelo encuentra estructura que la regla no captura.")
        print("     Mira la importancia de abajo para ver donde esta.")
    if not is_reg and model_m["lift"] < 0.05:
        print(f"  !! lift sobre mayoria = {model_m['lift']:+.4f}. Cuidado: la")
        print("     accuracy alta puede ser puro desbalance de clases.")

    # ---- importancia por permutacion ----------------------------------------
    if args.importance:
        from sklearn.inspection import permutation_importance
        tr_i, te_i = folds[-1]
        m = HGB(max_depth=args.max_depth, learning_rate=args.lr,
                max_iter=args.max_iter, random_state=args.seed)
        sw = (compute_sample_weight("balanced", y[tr_i])
              if args.class_weight == "balanced" and not is_reg else None)
        m.fit(X.iloc[tr_i], y[tr_i], sample_weight=sw)
        # permutation_importance copia X por cada feature y repeticion. Sobre
        # cientos de miles de filas eso solo es memoria quemada: con 20k filas
        # el ranking ya es estable.
        cap = min(len(te_i), 20000)
        rng = np.random.default_rng(args.seed)
        sub = rng.choice(te_i, size=cap, replace=False) if len(te_i) > cap else te_i
        print(f"  (importancia sobre {cap:,} filas del ultimo fold)")
        r = permutation_importance(
            m, X.iloc[sub], y[sub], n_repeats=4, random_state=args.seed,
            scoring="r2" if is_reg else "f1_macro")
        order = np.argsort(r.importances_mean)[::-1]
        print(f"\n=== Importancia por permutacion (caida de "
              f"{'R2' if is_reg else 'macro F1'}) ===")
        for i in order[:15]:
            if r.importances_mean[i] > 1e-4:
                print(f"  {X.columns[i]:<22} {r.importances_mean[i]:.4f} "
                      f"+/- {r.importances_std[i]:.4f}")

    # ---- guardar -------------------------------------------------------------
    if args.save:
        import joblib
        final = HGB(max_depth=args.max_depth, learning_rate=args.lr,
                    max_iter=args.max_iter, random_state=args.seed)
        sw = (compute_sample_weight("balanced", y)
              if args.class_weight == "balanced" and not is_reg else None)
        final.fit(X, y, sample_weight=sw)
        joblib.dump(make_bundle(final, cols, cfg, X, y, df, sigs,
                                args.target, is_reg), args.save)
        print(f"\nModelo guardado en {args.save}")


# ---------------------------------------------------------------------------
# 7. inspect: ver si las features separan las clases, antes de entrenar
# ---------------------------------------------------------------------------

def inspect(args) -> None:
    df = read_any(args.csv, getattr(args, "limit", None),
                  getattr(args, "sample_per_campaign", None),
                  getattr(args, "max_rows", 2_000_000),
                  getattr(args, "jobs", None))
    overrides = dict(kv.split("=", 1) for kv in (args.col or []))
    cols = resolve_columns(df, overrides)
    print_resolution(cols, df)

    missing = [c for c in REQUIRED if cols.get(c) is None]
    if missing:
        raise SystemExit(f"\nFaltan {missing}; no puedo featurizar.")

    for formula in (["pow2", "ratio"] if args.gap_formula == "both"
                    else [args.gap_formula]):
        cfg = FeatConfig(gap_formula=formula, polymul_set=args.polymul_set,
                         encode_ref=getattr(args, "encode_ref", "q"))
        X, sigs = featurize(df, cols, cfg)
        print(f"\n=== gap_formula = {formula} ===")
        print(f"  is_slot_aligned: {X['is_slot_aligned'].mean():.3f} de las filas")
        if cols.get("label"):
            y = df[cols["label"]].astype(str)
            print("\n  Poder de separacion de cada feature (mutual information "
                  "con la etiqueta):")
            from sklearn.feature_selection import mutual_info_classif
            mi = mutual_info_classif(X, y, random_state=0)
            for i in np.argsort(mi)[::-1][:12]:
                print(f"    {X.columns[i]:<22} {mi[i]:.4f}")
            print("\n  Tabla cruzada de los dos patrones que declaraste:")
            key = (X["has_polymul_after"].astype(int).astype(str) + "_" +
                   X["is_slot_aligned"].astype(int).astype(str))
            print(pd.crosstab(key.rename("polymul_after|slot_aligned"), y,
                              normalize="index").round(3))
            print("\n  Baseline de regla sobre todo el dataset:")
            report(y.to_numpy(), rule_baseline(X), f"regla ({formula})")


# ---------------------------------------------------------------------------
# 8. selftest: fisica conocida, para verificar el codigo
# ---------------------------------------------------------------------------

def make_synth(n=6000, seed=0, len_lo=1, len_hi=5, levels_lo=3, levels_hi=7,
               nn_shape=False) -> pd.DataFrame:
    """Dataset sintetico con la fisica declarada.

    nn_shape=True imita la forma de una red neuronal en CKKS: pipelines largos
    dominados por rot/add (las rotaciones de un matvec) con pocas mult que
    consumen nivel, y logQ mas grande porque hacen falta mas niveles.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        logN = int(rng.choice([14, 15, 16]))
        logSlots = int(rng.choice([3, 5, 8]))
        logDelta = int(rng.choice([30, 35, 40]))
        logQ = logDelta * int(rng.integers(levels_lo, levels_hi))
        k = int(rng.integers(len_lo, len_hi))
        if nn_shape:
            # matvec = muchas rot + add, pocas pmul/mul
            ops = list(rng.choice(["rot", "add"], size=k,
                                  p=[0.6, 0.4]))
            for _ in range(int(rng.integers(1, 4))):
                ops.insert(int(rng.integers(0, len(ops) + 1)),
                           str(rng.choice(["pmul", "mul"])))
            k = len(ops)
        else:
            ops = list(rng.choice(["add", "mul", "pmul", "rot"], size=k))
        step = int(rng.integers(0, k + 1))
        bit = int(rng.integers(0, logQ + 8))
        gap = 2 ** max(0, logN - 1 - logSlots)
        coeff = int(rng.integers(0, 2 ** (logN - 1)))

        before, after = ops[:step], ops[step:]
        lvl = logQ - logDelta * sum(1 for o in before if o in ("mul", "pmul"))
        has_poly = any(o in ("mul", "pmul", "rot") for o in after)
        aligned = (coeff % gap) == 0

        if bit >= lvl:
            lab = "failed"
        elif bit < logDelta:
            lab = "correct"
        elif not has_poly and not aligned:
            lab = "correct"
        else:
            lab = "corrupted"
        if rng.random() < 0.04:           # 4% de ruido de etiqueta
            lab = str(rng.choice(["correct", "corrupted", "failed"]))

        rows.append({"logN": logN, "logDelta": logDelta, "logQ": logQ,
                     "logSlots": logSlots, "bit": bit, "coeff": coeff, "limb": 0,
                     "pipeline": ",".join(ops), "op_step": step, "label": lab})
    return pd.DataFrame(rows)


def selftest(args) -> None:
    print("=" * 72)
    print("Dataset A: pipelines SIMPLES (lo que tenes hoy)")
    print("=" * 72)
    tr = make_synth(n=6000, seed=args.seed, len_lo=1, len_hi=5,
                    levels_lo=3, levels_hi=7)
    tr_path = "/tmp/heaan_simple.csv"
    tr.to_csv(tr_path, index=False)
    print(f"  {len(tr)} filas -> {tr_path}")
    print(f"  largo de pipeline: {tr['pipeline'].str.count(',').add(1).min()}"
          f"-{tr['pipeline'].str.count(',').add(1).max()}")
    print(f"  logQ: {sorted(tr['logQ'].unique())[:6]} ...")

    print("\n" + "=" * 72)
    print("Dataset B: forma de RED NEURONAL (lo que queres predecir)")
    print("  pipelines largos dominados por rot/add, pocas mult, y logQ MAS")
    print("  GRANDE -- porque mas profundidad necesita mas niveles. Esa")
    print("  correlacion entre profundidad y logQ es real y es la trampa:")
    print("  extrapolar a la red implica extrapolar en logQ, quieras o no.")
    print("=" * 72)
    te = make_synth(n=4000, seed=args.seed + 1, len_lo=8, len_hi=20,
                    levels_lo=10, levels_hi=15, nn_shape=True)
    te_path = "/tmp/heaan_nn_like.csv"
    te.to_csv(te_path, index=False)
    print(f"  {len(te)} filas -> {te_path}")
    print(f"  largo de pipeline: {te['pipeline'].str.count(',').add(1).min()}"
          f"-{te['pipeline'].str.count(',').add(1).max()}")
    print(f"  logQ: {sorted(te['logQ'].unique())[:6]} ...")

    base = dict(csv=tr_path, col=[], clip=32.0, count_clip=3,
                gap_formula="pow2", polymul_set="wide", boot_restores_to=None,
                include_raw_scale=False, split="pipeline", folds=5,
                max_depth=None, lr=0.1, max_iter=300, class_weight="balanced",
                seed=0, importance=True, save=None, test_csv=None,
                drop_features=[], target="label", limit=None,
                sample_per_campaign=0)

    print("\n\n" + "#" * 72)
    print("# ESCENARIO 1 -- leave-one-pipeline-out DENTRO de los simples")
    print("#   (esto es lo que vas a ver en tu CV; ojo con creerle de mas)")
    print("#" * 72)
    train(argparse.Namespace(**base))

    print("\n\n" + "#" * 72)
    print("# ESCENARIO 2 -- entrenar en simples, TESTEAR en la red")
    print("#   variante A: features relativas y recortadas")
    print("#" * 72)
    train(argparse.Namespace(**{**base, "test_csv": te_path,
                                "importance": False}))

    print("\n\n" + "#" * 72)
    print("# ESCENARIO 2 -- misma cosa, variante B: escala CRUDA incluida")
    print("#   y conteos sin recortar. Es el modelo 'obvio'.")
    print("#" * 72)
    train(argparse.Namespace(**{**base, "test_csv": te_path,
                                "include_raw_scale": True, "count_clip": 99,
                                "importance": False}))

    print("\n\n" + "#" * 72)
    print("# ESCENARIO 3 -- SOLO escala cruda: se le sacan las features")
    print("#   relativas y queda con bit, logQ, logDelta absolutos. Esto es")
    print("#   el equivalente a tu --feature-set raw de la corrida anterior.")
    print("#" * 72)
    train(argparse.Namespace(**{**base, "test_csv": te_path,
                                "include_raw_scale": True, "count_clip": 99,
                                "importance": False,
                                "drop_features": [
                                    "bit_minus_q_inject", "bit_minus_delta",
                                    "is_above_q_inject", "is_below_delta",
                                    "resilient_pattern", "aligned_x_polymul",
                                    "logq_inject_frac", "bit_frac_q"]}))



# ---------------------------------------------------------------------------
# 9. Guardar / predecir sobre un set de test aparte
# ---------------------------------------------------------------------------
BUNDLE_FORMAT = 2


def make_bundle(model, cols, cfg, X, y, df, sigs, target, is_reg) -> dict:
    """Guarda el modelo Y lo necesario para avisar cuando el test se sale del
    dominio de entrenamiento. Un modelo sin su dominio no sirve: predice con
    total seguridad sobre cosas que nunca vio."""
    cfgkeys = [cols[c] for c in ["logN", "logDelta", "logQ", "logSlots"]
               if cols.get(c)]
    return {
        "format": BUNDLE_FORMAT,
        "model": model,
        "cols": cols,
        "cfg": cfg,
        "features": list(X.columns),
        "target": target,
        "is_reg": bool(is_reg),
        # dominio de entrenamiento
        "feat_min": X.min().to_dict(),
        "feat_max": X.max().to_dict(),
        "train_configs": sorted(set(
            df[cfgkeys].astype(str).agg("|".join, axis=1))) if cfgkeys else [],
        "train_pipelines": sorted(set(pipeline_signature(df, cols, sigs))),
        "classes": (sorted(set(np.asarray(y).tolist())) if not is_reg else None),
        "n_train_rows": int(len(X)),
    }


def align_features(X_new: pd.DataFrame, wanted: list[str],
                   strict: bool = True) -> pd.DataFrame:
    """Alinea columnas SIN rellenar en silencio con 0.

    Rellenar con 0 una feature que falta es la peor clase de bug: el modelo
    devuelve numeros con total confianza a partir de datos inventados. Aca eso
    corta, salvo que se pida --allow-missing explicitamente.
    """
    missing = [c for c in wanted if c not in X_new.columns]
    if missing:
        msg = (f"Al set de test le faltan {len(missing)} features que el modelo "
               f"usa: {missing}\n"
               f"Eso pasa cuando el CSV de test no tiene alguna columna que si "
               f"tenia el de train.\n"
               f"Arreglalo mapeando la columna con --col, o reentrena sin esas "
               f"features usando --drop-features.")
        if strict:
            raise SystemExit(msg)
        print("  !! " + msg)
        for c in missing:
            X_new[c] = 0.0
    return X_new[wanted]


def extrapolation_report(X_new: pd.DataFrame, b: dict) -> None:
    print("\n=== Reporte de extrapolacion ===")
    rows = []
    for c in b["features"]:
        lo, hi = b["feat_min"].get(c), b["feat_max"].get(c)
        if lo is None:
            continue
        frac = float(((X_new[c] < lo) | (X_new[c] > hi)).mean())
        if frac > 0.005:
            rows.append((c, frac, lo, hi, X_new[c].min(), X_new[c].max()))
    if not rows:
        print("  ninguna feature se sale del rango de entrenamiento.")
        return
    print(f"  {'feature':<24}{'fuera':>8}  rango train      ->  rango test")
    for c, frac, lo, hi, nlo, nhi in sorted(rows, key=lambda r: -r[1]):
        flag = "   <-- 100% fuera; el modelo NO tiene nada que interpolar" \
            if frac > 0.99 else ""
        print(f"  {c:<24}{frac:>7.1%}  [{lo:>7.2f},{hi:>7.2f}] -> "
              f"[{nlo:>7.2f},{nhi:>7.2f}]{flag}")
    print("\n  Una feature 100% fuera de rango significa que el arbol solo puede")
    print("  devolver su hoja mas extrema. Si son varias, el numero que salga")
    print("  abajo no es una estimacion, es una extrapolacion ciega.")


def predict(args) -> None:
    import joblib
    b = joblib.load(args.model)
    if b.get("format") != BUNDLE_FORMAT:
        raise SystemExit(
            f"El .joblib es de formato {b.get('format')} y este script usa "
            f"{BUNDLE_FORMAT}. Reentrena con --save.")

    print(f"=== Modelo {args.model} ===")
    print(f"  target: {b['target']}  "
          f"({'regresion' if b['is_reg'] else 'clasificacion'})")
    print(f"  entrenado con {b['n_train_rows']:,} filas, "
          f"{len(b['features'])} features")
    print(f"  configuraciones vistas: {len(b['train_configs'])}")
    print(f"  pipelines vistos: {len(b['train_pipelines'])}")

    df = read_any(args.csv, getattr(args, "limit", None),
                  getattr(args, "sample_per_campaign", None),
                  getattr(args, "max_rows", 2_000_000),
                  getattr(args, "jobs", None))
    overrides = dict(kv.split("=", 1) for kv in (args.col or []))
    cols = resolve_columns(df, overrides)
    missing = [c for c in REQUIRED if cols.get(c) is None]
    if missing:
        raise SystemExit(f"Al set de test le faltan columnas: {missing}")

    print("\n=== Featurizando el test con la MISMA config del modelo ===")
    X_new, sigs_new = featurize(df, cols, b["cfg"])
    X_new = align_features(X_new, b["features"], strict=not args.allow_missing)

    # que tan nuevo es este set
    cfgkeys = [cols[c] for c in ["logN", "logDelta", "logQ", "logSlots"]
               if cols.get(c)]
    if cfgkeys and b["train_configs"]:
        newcfg = set(df[cfgkeys].astype(str).agg("|".join, axis=1))
        seen = newcfg & set(b["train_configs"])
        print(f"\n  configuraciones del test ya vistas: {len(seen)}/{len(newcfg)}")
        if not seen:
            print("  !! TODAS las configuraciones son nuevas. Esto es")
            print("     extrapolacion, no interpolacion -- leelo con eso en mente.")
    newpipe = set(pipeline_signature(df, cols, sigs_new))
    seenp = newpipe & set(b["train_pipelines"])
    print(f"  pipelines del test ya vistos: {len(seenp)}/{len(newpipe)}")
    if not seenp:
        print("  !! Ningun pipeline del test se vio en entrenamiento.")

    extrapolation_report(X_new, b)

    pred = b["model"].predict(X_new)
    out = pd.DataFrame(index=df.index)
    for c in ["campaign_id", "bit", "coeff", "limb"]:
        if cols.get(c):
            out[c] = df[cols[c]].to_numpy()
    out["pred"] = pred
    if b["is_reg"] and b["target"] == "log2_rel_error":
        out["pred_rel_error"] = np.power(2.0, np.clip(pred, -60, 60))
        out["pred_class"] = classes_from_log2(np.asarray(pred, float))
        print("\n  (target continuo: agrego pred_rel_error y pred_class con los "
              "umbrales 0.01/0.1/10)")

    # si el test trae etiquetas, evaluar de verdad
    tg = build_targets(df, cols, quiet=True)
    if not tg.empty:
        try:
            y_true, is_reg = resolve_target(tg, b["target"])
        except SystemExit:
            y_true = None
        if y_true is not None:
            print("\n=== El test TIENE etiquetas: evaluacion real ===")
            rep = report_reg if b["is_reg"] else report
            rep(y_true, pred, "MODELO sobre el test")
            rep(y_true, rule_baseline(X_new, b["target"]),
                "BASELINE DE REGLA sobre el test")
            if b["is_reg"] and b["target"] == "log2_rel_error" \
                    and "class_worst" in tg.columns:
                report(tg["class_worst"].to_numpy(), out["pred_class"].to_numpy(),
                       "MODELO umbralado a las 4 clases")
            out["y_true"] = y_true
    else:
        print("\n  El test no trae etiquetas: solo escribo predicciones.")

    out.to_csv(args.out, index=False)
    print(f"\nPredicciones -> {args.out}  ({len(out):,} filas)")




# ---------------------------------------------------------------------------
# 10. diagnose: por que se rompe la regla
# ---------------------------------------------------------------------------
# La regla de fisica se midio sobre stage=encode. Cuando el dataset trae otras
# etapas y pipelines con multiplicaciones, sus tres condiciones pueden dejar de
# valer -- por separado. Este comando dice CUAL se rompe y DONDE, en vez de
# dejarte con un macro F1 malo y ninguna pista.

def diagnose(args) -> None:
    df = read_any(args.csv, getattr(args, "limit", None),
                  getattr(args, "sample_per_campaign", None),
                  getattr(args, "max_rows", 2_000_000),
                  getattr(args, "jobs", None))
    overrides = dict(kv.split("=", 1) for kv in (args.col or []))
    cols = resolve_columns(df, overrides)
    missing = [c for c in REQUIRED if cols.get(c) is None]
    if missing:
        raise SystemExit(f"Faltan columnas: {missing}")

    cfg = FeatConfig(gap_formula=args.gap_formula, polymul_set=args.polymul_set,
                     encode_ref=getattr(args, "encode_ref", "q"))
    X, sigs = featurize(df, cols, cfg)
    tg = build_targets(df, cols, quiet=True)
    if "is_any_error" not in tg.columns:
        raise SystemExit("No hay etiquetas para diagnosticar.")
    err = tg["is_any_error"].to_numpy().astype(bool)

    aligned = X["is_slot_aligned"].to_numpy() > 0.5
    nyq = X["is_nyquist_coeff"].to_numpy() > 0.5
    above_q = X["bit_minus_q_inject"].to_numpy() >= 0
    above_d = X["bit_minus_delta"].to_numpy() >= LOG2_THRESHOLDS[0]

    print("\n" + "=" * 70)
    print("DIAGNOSTICO: cada condicion de la regla, por separado")
    print("=" * 70)
    print(f"  filas: {len(df):,}   con error real: {err.sum():,} ({err.mean():.1%})")
    print()
    print(f"  {'condicion':<34}{'recall':>9}{'precision':>11}{'cubre':>9}")
    print(f"  {'(recall = de los errores reales,':<34}")
    print(f"  {' cuantos cumplen la condicion)':<34}")
    print("  " + "-" * 61)
    for name, cond in [
            ("coeff alineado al gap de slots", aligned),
            ("coeff != N/2", ~nyq),
            ("bit >= logQ_at_inject", above_q),
            ("bit - logDelta >= log2(0.01)", above_d),
            ("REGLA COMPLETA (las 3 primeras)", aligned & ~nyq & above_q),
            ("variante: alineado + bit-logDelta", aligned & ~nyq & above_d),
            ("variante: sin exigir alineado", ~nyq & above_d)]:
        rec = float(err[cond].size and (cond & err).sum() / max(err.sum(), 1))
        pre = float((cond & err).sum() / max(cond.sum(), 1))
        print(f"  {name:<34}{rec:>9.3f}{pre:>11.3f}{cond.mean():>9.1%}")

    print("\n  Como leerlo: si una condicion tiene recall < 1.000, esta")
    print("  DESCARTANDO errores reales, o sea que como filtro es INVALIDA.")
    print("  La regla original vale solo si las tres tienen recall 1.000.")

    # de los errores que la regla se pierde, quien tiene la culpa
    rule = aligned & ~nyq & above_q
    fn = err & ~rule
    if fn.sum():
        print(f"\n  De los {fn.sum():,} errores que la regla NO detecta, falla por:")
        for name, cond in [("no alineado al gap", ~aligned),
                           ("es el coeff N/2", nyq),
                           ("bit < logQ_at_inject", ~above_q)]:
            print(f"    {name:<26} {float((fn & cond).sum())/fn.sum():>6.1%}")

    # estratificado: donde vale y donde no
    for key, label in [("stage", "stage"), ("mult_depth", "mult_depth")]:
        c = cols.get(key)
        if c is None or df[c].nunique() < 2:
            continue
        print(f"\n  --- Regla del gap de slots, por {label} ---")
        print(f"  {label:<18}{'filas':>10}{'P(err|alin)':>13}{'P(err|NO alin)':>16}")
        for v, sub in df.groupby(c, observed=True).groups.items():
            i = df.index.get_indexer(sub)
            if len(i) < 50:
                continue
            pa = err[i][aligned[i]].mean() if aligned[i].any() else float("nan")
            pn = err[i][~aligned[i]].mean() if (~aligned[i]).any() else float("nan")
            flag = "  <-- la regla NO vale aca" if pn > 0.01 else ""
            print(f"  {str(v):<18}{len(i):>10,}{pa:>13.4f}{pn:>16.4f}{flag}")
        print("  P(err|NO alineado) deberia ser ~0. Si no lo es, en ese grupo el")
        print("  error SI se esparce a coeficientes que no caen en un slot --")
        print("  que es exactamente lo que hace una multiplicacion polinomial.")

    # --- sanidad de rangos: puede `bit` alcanzar siquiera a logQ? -----------
    # Si el barrido de bits llega solo hasta bitPerCoeff y bitPerCoeff < logQ,
    # entonces `bit >= logQ` es INALCANZABLE por construccion y su recall bajo
    # no dice nada de la fisica: dice que la feature esta mal definida.
    print("\n  --- Sanidad: rango de `bit` vs los modulos ---")
    bitv = pd.to_numeric(df[cols["bit"]], errors="coerce").to_numpy()
    qv = pd.to_numeric(df[cols["logQ"]], errors="coerce").to_numpy()
    bpcv = (pd.to_numeric(df[cols["bitPerCoeff"]], errors="coerce").to_numpy()
            if cols.get("bitPerCoeff") else np.full(len(df), np.nan))
    unreachable = bitv.max() < qv
    print(f"  {'':<4}bit va de {int(np.nanmin(bitv))} a {int(np.nanmax(bitv))}")
    print(f"  filas donde el bit MAXIMO barrido no llega a logQ: "
          f"{unreachable.mean():.1%}")
    per_bpc = bitv > bpcv
    if not np.isnan(bpcv).all():
        print(f"  filas con bit > bitPerCoeff: {np.nanmean(per_bpc):.1%}  "
              f"(deberia ser 0% si el barrido respeta el ancho del coeficiente)")
        gt = bpcv < qv
        print(f"  filas con bitPerCoeff < logQ: {np.nanmean(gt):.1%}")
        if np.nanmean(gt) > 0.5:
            print("  !! En la mayoria de las filas el coeficiente es MAS ANGOSTO")
            print("     que logQ. Eso pasa cuando logQ es la cadena de modulos")
            print("     COMPLETA (RNS) y cada limb mide bitPerCoeff. Ahi el modulo")
            print("     que le importa a un bit flip es el del LIMB, no la cadena:")
            print("     `bit >= logQ` es inalcanzable por construccion y hay que")
            print("     medir contra bitPerCoeff.")

    # --- confusion entre stage y pipeline -----------------------------------
    # Si cada stage aparece con su propio pipeline, entonces --split pipeline
    # deja stages ENTEROS afuera del train. Eso no es "dificil de aprender":
    # es imposible. El modelo tiene que responder sobre un regimen que nunca vio.
    sc, pc = cols.get("stage"), None
    psig = pipeline_signature(df, cols, sigs)
    if sc is not None and df[sc].nunique() > 1:
        print("\n  --- stage x pipeline: estan confundidos? ---")
        ct = pd.crosstab(df[sc], psig)
        print(ct.to_string())
        per_stage = (ct > 0).sum(axis=1)
        per_pipe = (ct > 0).sum(axis=0)
        solo = int((per_pipe == 1).sum())
        print(f"\n  pipelines que aparecen en UNA sola etapa: {solo}/{len(per_pipe)}")
        if solo == len(per_pipe):
            print("  !! stage y pipeline estan COMPLETAMENTE confundidos.")
            print("     Con --split pipeline, dejar un pipeline afuera deja tambien")
            print("     su etapa afuera. El numero que salga no mide generalizacion")
            print("     a un pipeline nuevo: mide extrapolacion a un regimen nuevo.")
            print("     Hace falta el mismo pipeline en varias etapas, o aceptar")
            print("     que la pregunta es otra y usar --split campaign.")
        elif solo:
            print(f"  Ojo: {solo} pipelines viven en una sola etapa; los folds que")
            print("  los dejen afuera van a estar extrapolando de regimen.")

    # --- que referencia hace constante el umbral, por etapa ------------------
    if sc is not None:
        bitv = pd.to_numeric(df[cols["bit"]], errors="coerce").to_numpy()
        qv = pd.to_numeric(df[cols["logQ"]], errors="coerce").to_numpy()
        dv = pd.to_numeric(df[cols["logDelta"]], errors="coerce").to_numpy()
        bv = (pd.to_numeric(df[cols["bitPerCoeff"]], errors="coerce").to_numpy()
              if cols.get("bitPerCoeff") else np.full(len(df), np.nan))
        print("\n  --- Umbral de bit por ETAPA, contra cada referencia ---")
        print(f"  {'stage':<16}{'n':>9}{'bit_min':>9}{'-logQ':>8}{'-2logQ':>9}"
              f"{'-logDelta':>11}{'-bitPerCoeff':>14}")
        for v, sub in df.groupby(sc, observed=True).groups.items():
            i = df.index.get_indexer(sub)
            if not err[i].any():
                continue
            m = bitv[i][err[i]].min()
            print(f"  {str(v):<16}{len(i):>9,}{m:>9.0f}"
                  f"{m-np.median(qv[i]):>8.0f}{m-2*np.median(qv[i]):>9.0f}"
                  f"{m-np.median(dv[i]):>11.0f}"
                  f"{(m-np.median(bv[i])) if not np.isnan(bv[i]).all() else float('nan'):>14.0f}")
        print("\n  La columna que quede mas CONSTANTE entre etapas es la")
        print("  referencia correcta para el eje bit. Si `-logQ` varia mucho pero")
        print("  `-2logQ` no, el encode efectivamente trabaja con el doble de")
        print("  modulo y hay que correr con --encode-ref 2q (que ya es el default).")

    # umbral de bit por configuracion
    print("\n  --- Umbral de bit por configuracion ---")
    ck = [cols[k] for k in ["logN", "logQ", "logDelta", "logSlots"] if cols.get(k)]
    if ck:
        bit = pd.to_numeric(df[cols["bit"]], errors="coerce").to_numpy()
        rows = []
        for v, sub in df.groupby(ck, observed=True).groups.items():
            i = df.index.get_indexer(sub)
            if not err[i].any():
                continue
            b = bit[i][err[i]]
            d = dict(zip(ck, v if isinstance(v, tuple) else (v,)))
            rows.append({**d, "n": len(i), "bit_min": int(b.min()),
                         "menos_logDelta": int(b.min()) - d.get(cols.get("logDelta"), 0),
                         "menos_logQ": int(b.min()) - d.get(cols.get("logQ"), 0)})
        if rows:
            t = pd.DataFrame(rows).sort_values("bit_min")
            print(t.head(20).to_string(index=False))
            print("\n  Si `menos_logDelta` es mas constante que `menos_logQ`, el")
            print("  umbral lo fija el factor de escala y no el modulo, y la regla")
            print("  tiene que usar bit-logDelta.")



# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("csv")
        sp.add_argument("--col", action="append", metavar="CANON=REAL",
                        help="forzar mapeo de columna, ej: --col label=outcome")
        sp.add_argument("--gap-formula", default="pow2",
                        choices=["pow2", "ratio", "both"])
        sp.add_argument("--polymul-set", default="wide", choices=["wide", "narrow"],
                        help="wide incluye rot como mult polinomial (key switching)")
        sp.add_argument("--encode-ref", default="q", choices=["q", "2q", "bpc"],
                        help="modulo de referencia en las etapas de plaintext. "
                             "Default q: MEDIDO sobre 179k inyecciones de encode, "
                             "el umbral cae en logQ (-2 y -10 bits), no en 2logQ "
                             "(-42 y -70). Usa 2q solo si diagnose lo respalda "
                             "en TU dataset.")
        sp.add_argument("--limit", type=int, default=None,
                        help="leer solo las primeras N campanas (para probar rapido)")
        sp.add_argument("--max-rows", type=int, default=2_000_000,
                        help="presupuesto GLOBAL de filas, repartido entre las "
                             "campanas y aplicado mientras carga. 0 = sin tope "
                             "(cuidado: 97M inyecciones no entran en RAM).")
        sp.add_argument("--sample-per-campaign", type=int, default=0,
                        help="tope por campana, si preferis fijarlo a mano. "
                             "0 = derivarlo de --max-rows.")
        sp.add_argument("--jobs", type=int, default=None,
                        help="procesos para leer los csv.gz (default: nucleos-1)")
        sp.add_argument("--only-stage", nargs="*", default=None,
                        help="quedarse solo con estas etapas. Con una etapa "
                             "acaparando el 80% de las filas, entrenar una por "
                             "etapa suele decir mas que un modelo unico.")
        sp.add_argument("--exclude-stage", nargs="*", default=None)

    sp = sub.add_parser("inspect", help="ver el mapeo y el poder de las features")
    common(sp)
    sp.set_defaults(func=inspect)

    sp = sub.add_parser("train", help="entrenar y evaluar")
    common(sp)
    sp.add_argument("--split", default="pipeline",
                    choices=["pipeline", "config", "both", "depth", "campaign",
                             "stage", "stage_x_config"])
    sp.add_argument("--folds", type=int, default=5)
    sp.add_argument("--clip", type=float, default=32.0)
    sp.add_argument("--count-clip", type=int, default=3)
    sp.add_argument("--boot-restores-to", type=float, default=None)
    sp.add_argument("--include-raw-scale", action="store_true")
    sp.add_argument("--max-depth", type=int, default=None)
    sp.add_argument("--lr", type=float, default=0.1)
    sp.add_argument("--max-iter", type=int, default=300)
    sp.add_argument("--class-weight", default="balanced",
                    choices=["balanced", "none"])
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--importance", action=argparse.BooleanOptionalAction,
                    default=True, help="usa --no-importance para saltearla (es cara)")
    sp.add_argument("--target", default="class_worst",
                    help="class_worst (peor slot) | class_major | is_any_error | "
                         "log2_rel_error (regresion, recomendado) | n_affected | "
                         "frac_affected | spread")
    sp.add_argument("--drop-features", nargs="*", default=[],
                    help="features a excluir, ej: --drop-features bit_minus_q_inject")
    sp.add_argument("--save")
    sp.add_argument("--test-csv", default=None,
                    help="CSV de test externo: entrena con todo --csv y evalua aca")
    sp.set_defaults(func=train)

    sp = sub.add_parser("layout", help="mostrar el esquema real de results/ (CORRE ESTO PRIMERO)")
    sp.add_argument("root", help="directorio results/ que contiene campaigns_start.csv")
    sp.set_defaults(func=layout)

    sp = sub.add_parser("diagnose", help="por que se rompe la regla de fisica")
    common(sp)
    sp.set_defaults(func=diagnose)

    sp = sub.add_parser("predict", help="aplicar un modelo guardado a un set nuevo")
    sp.add_argument("model", help="el .joblib guardado con train --save")
    sp.add_argument("csv", help="results_test/ o results_test/campaigns_start.csv")
    sp.add_argument("--out", default="predicciones.csv")
    sp.add_argument("--col", action="append", metavar="CANON=REAL")
    sp.add_argument("--limit", type=int, default=None)
    sp.add_argument("--sample-per-campaign", type=int, default=0)
    sp.add_argument("--max-rows", type=int, default=2_000_000)
    sp.add_argument("--jobs", type=int, default=None)
    sp.add_argument("--allow-missing", action="store_true",
                    help="rellenar con 0 las features que falten en vez de cortar "
                         "(peligroso: el modelo predice sobre datos inventados)")
    sp.set_defaults(func=predict)

    sp = sub.add_parser("selftest", help="verificar el codigo con datos sinteticos")
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=selftest)

    args = p.parse_args()
    if args.cmd == "inspect" and not hasattr(args, "gap_formula"):
        args.gap_formula = "pow2"
    args.func(args)


if __name__ == "__main__":
    main()
