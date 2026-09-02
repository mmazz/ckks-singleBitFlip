#!/usr/bin/env python3
"""
Puntua una corrida HEAAN preparada con un modelo de severidad ya entrenado.

Toma un bundle escrito por train_heaan_multiclass_site_within_stage.py
(--save-model) mas un directorio preparado por prepare_heaan.py, y reporta la
mezcla de severidad predicha por sitio de inyeccion, la tasa de SDC predicha y
las posiciones de bit mas riesgosas.

Si las filas preparadas traen rel_error, se usa SOLO para puntuar despues de
predecir — nunca como input — asi que ademas se obtiene accuracy, macro F1 y
matriz de confusion.

La matriz de features se arma importando el trainer, asi que hay una sola
implementacion de la politica de features y las predicciones no pueden
desviarse en silencio del entrenamiento.

QUE CAMBIO
----------
- Antes decia "54/54 sites vistos en entrenamiento" y se quedaba tranquilo
  aunque TODAS las configuraciones (logQ, logDelta, ...) fueran nuevas. Ahora
  compara tambien las configuraciones y avisa fuerte.
- Reporta, feature por feature, que fraccion de las filas cae fuera del rango
  visto durante el entrenamiento. Ahi se ve de una si el modelo esta
  extrapolando.
- Ya no rellena con 0 en silencio una columna numerica que falte: eso solo se
  permite para los one-hot de stage, donde 0 significa "no es este stage".

Ejemplos:
  python3 predict_heaan.py heaan_rel.joblib results_test/ml
  python3 predict_heaan.py heaan_rel.joblib results_test/ml --by campaign --out res.csv
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

SUPPORTED_FORMATS = (8,)


def load_trainer():
    if not TRAINER.exists():
        sys.exit(f"no encuentro {TRAINER.name} al lado de este script")

    spec = importlib.util.spec_from_file_location("heaan_trainer", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bundle(path: str):
    import joblib

    if not os.path.exists(path):
        sys.exit(f"no hay modelo en {path}")

    bundle = joblib.load(path)

    fmt = bundle.get("format")
    if fmt not in SUPPORTED_FORMATS:
        sys.exit(
            f"el bundle tiene formato {fmt}, no soportado (se esperaba "
            f"{SUPPORTED_FORMATS}) — reentrena con el "
            "train_heaan_multiclass_site_within_stage.py actual"
        )

    for key in ("model", "columns", "classes", "thresholds"):
        if key not in bundle:
            sys.exit(f"el bundle no tiene '{key}' — no lo escribio el trainer")

    return bundle


# ---------------------------------------------------------------------------
# Alineacion de columnas
# ---------------------------------------------------------------------------

class Aligner:
    """Mapea las columnas de esta corrida a las que vio el modelo.

    Una corrida nueva puede traer un stage que el modelo nunca vio (columna
    stage_* de mas) o no traer uno que si vio (columna stage_* ausente). Para
    los one-hot de stage, 0 es la respuesta correcta ("no es este stage").
    Para cualquier OTRA columna, rellenar con 0 seria inventar un valor, asi
    que se corta.
    """

    def __init__(self, ds_columns: list[str], model_columns: list[str]):
        pos = {c: i for i, c in enumerate(ds_columns)}
        self.idx = np.array([pos.get(c, -1) for c in model_columns], dtype=np.int64)
        self.take = self.idx >= 0

        self.missing = [c for c, i in zip(model_columns, self.idx) if i < 0]
        self.extra = [c for c in ds_columns if c not in set(model_columns)]
        self.n_out = len(model_columns)

        hard = [c for c in self.missing if not c.startswith("stage_")]
        if hard:
            sys.exit(
                "estas columnas que el modelo espera no existen en esta corrida "
                "y no se pueden rellenar sin inventar datos: "
                + ", ".join(hard)
                + "\nRevisa que prepare_heaan.py haya corrido con la misma version "
                "en los dos datasets y que campaigns_start.csv tenga las mismas "
                "columnas."
            )

    def __call__(self, X: np.ndarray) -> np.ndarray:
        if (
            self.take.all()
            and len(self.idx) == X.shape[1]
            and np.array_equal(self.idx, np.arange(X.shape[1]))
        ):
            return X

        out = np.zeros((len(X), self.n_out), dtype=np.float32)
        out[:, self.take] = X[:, self.idx[self.take]]
        return out


# ---------------------------------------------------------------------------
# Agregacion
# ---------------------------------------------------------------------------

class Aggregator:
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
            self.cm += np.bincount(gid * k * k + true * k + pred, minlength=len(self.cm))
            self.bits_true += np.bincount(bit * k + true, minlength=len(self.bits_true))

    def group_pred(self) -> np.ndarray:
        return self.pred.reshape(self.n_groups, self.k)

    def group_cm(self):
        if not self.has_truth:
            return None
        return self.cm.reshape(self.n_groups, self.k, self.k)

    def bit_pred(self) -> np.ndarray:
        return self.bits.reshape(-1, self.k)

    def bit_true(self):
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
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument("model", help="bundle joblib de --save-model")
    ap.add_argument("ml_dir", help="directorio preparado a puntuar")

    ap.add_argument(
        "--by",
        choices=["site", "campaign", "stage", "config", "nn-site", "nn-stage"],
        default="site",
        help="nivel de agregacion del resumen (default: site)",
    )
    ap.add_argument("--out", default=None, metavar="CSV")
    ap.add_argument("--top-bits", type=int, default=15, metavar="N")
    ap.add_argument("--min-rows", type=int, default=200, metavar="N")
    ap.add_argument("--block", type=int, default=2_000_000, metavar="N")
    ap.add_argument("--rebuild-cache", action="store_true")

    args = ap.parse_args()

    T = load_trainer()
    bundle = load_bundle(args.model)

    classes = list(bundle["classes"])
    if classes != T.CLASS_NAMES:
        sys.exit(f"las clases del modelo {classes} no coinciden con {T.CLASS_NAMES}")

    thresholds = bundle["thresholds"]
    correct_max = float(thresholds["correct_max"])
    corrupted_max = float(thresholds["corrupted_max"])

    policy = bundle.get("feature_policy", {})
    feature_set = policy.get("feature_set", "raw")
    clip = float(policy.get("clip", T.DEFAULT_CLIP))
    dropped = list(policy.get("dropped") or [])

    model = bundle["model"]
    model_columns = list(bundle["columns"])

    # -- cargar la corrida -------------------------------------------------

    ds = T.Dataset(
        os.path.abspath(args.ml_dir),
        feature_set=feature_set,
        rebuild=args.rebuild_cache,
        clip=clip,
        drop=dropped,
    )

    aligner = Aligner(ds.columns, model_columns)

    print(f"modelo:  {os.path.abspath(args.model)}")
    print(
        f"         {len(model_columns)} features · 3 clases · "
        f"correct <= {correct_max:g} < corrupted <= {corrupted_max:g} < failed"
        + (f" · feature set '{feature_set}' (clip {clip:g})"
           if feature_set != "raw" else "")
    )

    cv = bundle.get("cv") or {}
    if cv:
        print(
            f"         CV de entrenamiento ({cv.get('split', '?')}): "
            f"macro F1 {cv.get('macro_f1', float('nan')):.4f} · "
            f"SDC F1 {cv.get('sdc_f1', float('nan')):.4f}"
        )
        if cv.get("folds_with_config_in_train"):
            print(
                f"         aviso: {cv['folds_with_config_in_train']} de "
                f"{cv.get('folds_checked')} folds de ese CV compartian "
                "configuracion con train"
            )

    print(
        f"dataset: {ds.n_rows:,} filas · {ds.n_campaigns:,} campañas · "
        + ("rel_error presente" if ds.has_truth else "sin rel_error (solo prediccion)")
    )

    if aligner.missing:
        print(
            f"  aviso: {len(aligner.missing)} columna(s) stage_* que el modelo "
            "espera no estan aca y van en 0: " + ", ".join(aligner.missing[:10])
            + (" ..." if len(aligner.missing) > 10 else "")
        )
    if aligner.extra:
        print(
            f"  aviso: {len(aligner.extra)} columna(s) de aca son desconocidas para "
            "el modelo y se descartan: " + ", ".join(aligner.extra[:10])
            + (" ..." if len(aligner.extra) > 10 else "")
        )

    # -- cobertura ---------------------------------------------------------

    train_sites = set(bundle.get("train_sites") or [])
    train_stages = set(bundle.get("train_stages") or [])
    train_configs = set(bundle.get("train_configs") or [])
    config_keys = bundle.get("train_config_keys") or []

    run_sites = sorted(set(ds.site.tolist()))
    run_stages = sorted(set(ds.stage.tolist()))
    run_configs = sorted(set(ds.config.tolist()))

    new_sites = [s for s in run_sites if s not in train_sites]
    new_stages = [s for s in run_stages if s not in train_stages]
    new_configs = [c for c in run_configs if c not in train_configs]

    print()
    print(
        f"cobertura: {len(run_sites) - len(new_sites)}/{len(run_sites)} sites y "
        f"{len(run_configs) - len(new_configs)}/{len(run_configs)} configuraciones "
        "de esta corrida se vieron en entrenamiento"
    )
    if config_keys:
        print(f"  configuracion = {config_keys}")
    if new_configs:
        print()
        print("  " + "!" * 70)
        print(f"  {len(new_configs)} de {len(run_configs)} CONFIGURACIONES son nuevas.")
        print("  El modelo esta extrapolando a escalas que nunca vio. Salvo que el")
        print("  CV de arriba sea leave-one-config-out, no estima este caso.")
        for c in new_configs[:8]:
            print(f"    {c}")
        if len(new_configs) > 8:
            print(f"    ... y {len(new_configs) - 8} mas")
        print("  " + "!" * 70)
    if new_stages:
        print(f"  {len(new_stages)} stage(s) nunca vistos: " + ", ".join(new_stages[:10]))
    if new_sites:
        print(f"  {len(new_sites)} site(s) nunca vistos: " + ", ".join(new_sites[:8]))

    # -- rango de features -------------------------------------------------

    ranges = bundle.get("feature_ranges") or {}
    if ranges:
        # muestra por salto constante: O(n_probe) memoria, no O(n_rows).
        # rng.choice(replace=False) sobre 50M filas materializa una permutacion
        # entera y rompe el presupuesto de memoria del pipeline.
        n_probe = min(ds.n_rows, 200_000)
        step = max(ds.n_rows // n_probe, 1)
        probe = np.arange(0, ds.n_rows, step, dtype=np.int64)[:n_probe]
        Xp = aligner(ds.features(probe))

        offenders = []
        for i, name in enumerate(model_columns):
            if name not in ranges:
                continue
            lo, hi = ranges[name]
            out = float(((Xp[:, i] < lo) | (Xp[:, i] > hi)).mean())
            if out > 0.01:
                offenders.append((out, name, lo, hi, float(Xp[:, i].min()),
                                  float(Xp[:, i].max())))

        print()
        if offenders:
            offenders.sort(reverse=True)
            print("Features fuera del rango visto en entrenamiento "
                  f"(muestra de {n_probe:,} filas)")
            print(f"  {'feature':<24}{'train min':>11}{'train max':>11}"
                  f"{'aqui min':>11}{'aqui max':>11}{'fuera':>9}")
            for out, name, lo, hi, a, b in offenders[:15]:
                print(f"  {name:<24}{lo:>11.4g}{hi:>11.4g}{a:>11.4g}{b:>11.4g}"
                      f"{out:>8.1%}")
            print("  Un arbol ahi devuelve su hoja mas extrema; logreg/mlp")
            print("  extrapolan linealmente y se saturan. Si esto es grande, el")
            print("  feature set no es tan invariante a escala como parece.")
        else:
            print("Todas las features caen dentro del rango visto en entrenamiento.")

    # -- agrupacion --------------------------------------------------------

    def need(col: str):
        if col not in ds.meta.columns:
            sys.exit(
                f"--by {args.by} necesita la columna '{col}' en heaan_campaigns.csv."
            )
        return ds.meta[col].astype(str).to_numpy()

    if args.by == "site":
        keys = ds.site
    elif args.by == "stage":
        keys = ds.stage
    elif args.by == "config":
        keys = ds.config
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

    seen_group = np.zeros(len(group_names), dtype=bool)
    for c in range(ds.n_campaigns):
        if ds.config[c] in train_configs and ds.site[c] in train_sites:
            seen_group[group_of_campaign[c]] = True

    # -- puntuar -----------------------------------------------------------

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

    # -- global ------------------------------------------------------------

    gp = agg.group_pred()
    totals = gp.sum(axis=0)
    n = int(totals.sum())

    print()
    print("Distribucion de clases predicha")
    for i, name in enumerate(classes):
        print(f"  {name:<12}{int(totals[i]):>14,}{totals[i] / n:>10.3%}")
    print(f"  {'SDC rate':<12}{int(totals[1:].sum()):>14,}{totals[1:].sum() / n:>10.3%}")

    gcm = agg.group_cm()

    if gcm is not None:
        overall = gcm.sum(axis=0)
        stats = T.Stats()
        stats.cm = overall

        true_totals = overall.sum(axis=1)
        majority = int(true_totals.argmax())
        base_acc = float(true_totals[majority] / n)

        print()
        print("Distribucion de clases real (de rel_error)")
        for i, name in enumerate(classes):
            print(f"  {name:<12}{int(true_totals[i]):>14,}{true_totals[i] / n:>10.3%}")
        print(
            f"  {'SDC rate':<12}{int(true_totals[1:].sum()):>14,}"
            f"{true_totals[1:].sum() / n:>10.3%}"
        )

        print()
        print("Puntuado contra rel_error")
        print(f"  macro F1     {stats.macro_f1:.4f}   <- el numero que importa")
        print(f"  bal accuracy {stats.balanced_accuracy:.4f}")
        print(f"  accuracy     {stats.accuracy:.4f}")
        print(f"  base acc     {base_acc:.4f}   (predecir siempre "
              f"'{classes[majority]}')")
        print(f"  lift         {stats.accuracy - base_acc:+.4f}")
        print(f"  weighted F1  {stats.weighted_f1:.4f}")
        print(f"  SDC accuracy {stats.sdc_accuracy:.4f}")
        print(f"  SDC F1       {stats.sdc_f1:.4f}")
        print()
        print("Por clase")
        print(stats.report())
        print()
        print("Matriz de confusion (filas=real, columnas=predicho)")
        print(stats.confusion())

        never = [classes[i] for i in range(len(classes))
                 if overall[:, i].sum() == 0 and true_totals[i] > 0]
        if never:
            print()
            print(f"  >> El modelo NUNCA predice: {', '.join(never)}. Eso solo ya")
            print("     hunde el macro F1. Proba --class-weight balanced y un modelo")
            print("     que pueda recortar un intervalo (hgb/tree) en vez de logreg.")

        if cv and np.isfinite(cv.get("macro_f1", np.nan)):
            delta = stats.macro_f1 - float(cv["macro_f1"])
            verdict = (
                "en linea con el CV"
                if abs(delta) < 0.05
                else ("MEJOR que el CV" if delta > 0 else "PEOR que el CV")
            )
            print()
            print(
                f"  macro F1 aca {stats.macro_f1:.4f} vs CV {cv['macro_f1']:.4f} "
                f"({delta:+.4f}) — {verdict}"
            )

    # -- tabla por grupo ---------------------------------------------------

    rows = []
    for g, name in enumerate(group_names):
        total = int(gp[g].sum())
        if total == 0:
            continue

        rec = {args.by: name, "rows": total, "seen_in_training": bool(seen_group[g])}
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
    print(f"Por {args.by} (ordenado por tasa de SDC predicha)")

    show = [args.by, "rows"] + [f"pred_{c}" for c in classes] + ["pred_sdc_rate"]
    if gcm is not None:
        show += ["true_sdc_rate", "accuracy", "macro_f1"]
    show += ["seen_in_training"]

    with pd.option_context("display.max_rows", 200, "display.width", 200):
        print(summary[show].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # -- bits mas riesgosos ------------------------------------------------

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
                f"Posiciones de bit mas riesgosas (SDC predicho, "
                f">={args.min_rows:,} filas cada una)"
            )
            header = f"  {'bit':>5}{'filas':>12}{'SDC pred':>11}"
            if gcm is not None:
                header += f"{'SDC real':>11}"
            print(header)

            bt = agg.bit_true()
            for b in order:
                line = f"  {b:>5}{int(counts[b]):>12,}{rate[b]:>11.3%}"
                if bt is not None:
                    line += f"{bt[b, 1:].sum() / counts[b]:>11.3%}"
                print(line)

    if args.out:
        out = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        summary.to_csv(out, index=False)
        print(f"\nresumen escrito en {out} ({len(summary)} filas)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
