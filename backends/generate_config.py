#!/usr/bin/env python3
"""
generate_config.py — Genera un CSV de config para run_campaign.py a partir de
un producto cartesiano de parámetros, definido en un diccionario Python.

Esto reemplaza los `for s in SEEDS; do for s_input in SEEDS; do ...` del Makefile.

Editá la sección "DEFINIR ACA" más abajo para cada análisis que quieras generar,
o copiá este archivo como base para nuevos análisis (ej: generate_seeds_analysis.py,
generate_mul_inside.py, etc.) si preferís tener un generador por análisis versionado.

Uso:
  python generate_config.py
  -> escribe configs/<nombre>.csv
"""

import csv
import itertools
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SEEDS_PRNG = 4
SEEDS_INP = 3
def cartesian_product_rows(fixed: dict, sweep: dict) -> list[dict]:
    """
    fixed: parámetros que NO varían (mismo valor en todas las filas)
    sweep: parámetros que SÍ varían -> se genera el producto cartesiano de sus listas

    Devuelve una lista de dicts (filas), cada una con run_id ya generado.
    """
    sweep_keys = list(sweep.keys())
    sweep_values = [sweep[k] for k in sweep_keys]

    rows = []
    for combo in itertools.product(*sweep_values):
        row = dict(fixed)
        row.update(dict(zip(sweep_keys, combo)))
        # run_id legible: junta los valores que varían, ej. "s1_si2"
        run_id_parts = [f"{k}{v}" for k, v in zip(sweep_keys, combo)]
        row["run_id"] = "_".join(run_id_parts)
        rows.append(row)
    return rows


def write_csv(name: str, rows: list[dict]):
    if not rows:
        print(f"[{name}] no se generaron filas, se omite.")
        return
    # Unimos todas las claves que aparecen en cualquier fila, preservando orden:
    # run_id primero, control después, parámetros después.
    all_keys = []
    for row in rows:
        for k in row.keys():
            if k not in all_keys:
                all_keys.append(k)
    ordered = ["run_id", "binary", "library"] + [
        k for k in all_keys if k not in ("run_id", "binary", "library")
    ]

    out_path = CONFIG_DIR / f"{name}.csv"
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[{name}] {len(rows)} filas -> {out_path}")


# ============================================================
# DEFINIR ACA: un bloque por análisis. Comentá/descomentá o
# agregá los que necesites.
# ============================================================

def gen_seeds_analysis():
    """Equivalente a 'seeds_analysis' del Makefile original: 15x15 = 225 corridas."""
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",
        "logN": 6,
        "logQ": 60,
        "bitPerCoeff": 64,
        "logDelta": 40,
        "stage": "encrypt_c0",
        "logSlots": 5,
        "withNTT": 0,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
    }
    write_csv("seeds_analysis", cartesian_product_rows(fixed, sweep))


def gen_mul_inside():
    """Equivalente a 'mul_inside' del Makefile original: 13 corridas (antes copiadas a mano)."""
    fixed = {
        "binary": "exhaustiveSingleBitFlip",
        "library": "heaan",  # ajustar si corresponde a $(LIBRARY)
        "logN": 6,
        "logQ": 120,
        "bitPerCoeff": 144,
        "logDelta": 40,
        "stage": "mul_inside",
        "op_step": 1,
        "doMul": 1,
        "mult_depth": 2,
        "logSlots": 4,
    }
    sweep = {
        "seed": list(range(1, SEEDS_PRNG+1)),
        "seed_input": list(range(1, SEEDS_INP+1)),
        "op_index": list(range(13)),  # 0..12
    }
    write_csv("mul_inside", cartesian_product_rows(fixed, sweep))


if __name__ == "__main__":
    gen_seeds_analysis()
    gen_mul_inside()
