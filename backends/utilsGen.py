import csv
import itertools
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent / "configs"
SEEDS_PRNG = 5
SEEDS_INP = 5
SEEDS_PRNG_NN = 2
SEEDS_INP_NN = 2
EXTRA_SEEDS = 20
stages = ["encode", "encrypt_c0", "encrypt_c1", "decrypt_c0", "decrypt_c1", "decode"]

def cartesian_product_rows(fixed: dict, sweep: dict) -> list[dict]:
    """
    variants: parámetros que varian en pares o solos
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
