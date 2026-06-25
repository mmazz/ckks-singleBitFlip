#!/usr/bin/env python3
"""
run_campaign.py — Ejecuta una campaña de experimentos definida en un CSV de configuración.

Cada fila del CSV de config es UNA corrida del binario C++. Las columnas son:
  - run_id     : identificador único de la corrida (para logs y resumability)
  - binary     : nombre del binario (sin path), se busca en <library>/build/bin/<binary>
  - library    : subcarpeta donde correr (heaan, openfhe, ...) -> hace cd ahí
                 y también determina la ubicación del binario
  - <resto>    : cualquier columna se traduce a --columna valor para el binario,
                 EXCEPTO run_id, binary, library, que son control del runner.

Uso:
  python run_campaign.py configs/seeds_analysis.csv
  python run_campaign.py configs/seeds_analysis.csv --jobs 8
  python run_campaign.py configs/seeds_analysis.csv --dry-run
  python run_campaign.py configs/seeds_analysis.csv --resume   # saltea runs ya OK en el log
"""

import argparse
import csv
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

# --- Configuración de paths del proyecto. Ajustar a tu estructura real. ---
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"

# Path del binario relativo a la carpeta de la library (ej: heaan/build/bin/<binary>)
BIN_SUBPATH = Path("build") / "bin"

# Columnas que son control del runner, no parámetros del binario
CONTROL_COLUMNS = {"run_id", "binary", "library"}


def build_command(row: dict) -> list[str]:
    """Convierte una fila del CSV en el comando a ejecutar.

    El binario vive dentro de la carpeta de su library, ej:
    PROJECT_ROOT/heaan/build/bin/exhaustiveSingleBitFlip
    """
    binary_path = PROJECT_ROOT / row["library"] / BIN_SUBPATH / row["binary"]
    cmd = [str(binary_path)]
    for key, value in row.items():
        if key in CONTROL_COLUMNS:
            continue
        if value == "" or value is None:
            continue  # columna vacía en esa fila = no pasar ese flag
        cmd.append(f"--{key}")
        cmd.append(str(value))
    return cmd


def run_one(row: dict, dry_run: bool, log_path: Path, lock: Lock) -> tuple[str, bool, str]:
    """Ejecuta una fila. Devuelve (run_id, ok, mensaje)."""
    run_id = row["run_id"]
    library = row["library"]
    cwd = PROJECT_ROOT / library
    cmd = build_command(row)

    if dry_run:
        return run_id, True, f"[DRY-RUN] cd {cwd} && {' '.join(cmd)}"

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=None,  # ajustar si querés un timeout por corrida
        )
        elapsed = time.time() - start
        ok = result.returncode == 0
        msg = f"exit={result.returncode} time={elapsed:.1f}s"
        if not ok:
            # Guardamos stderr en un archivo separado para no inundar la consola
            err_file = LOG_DIR / f"{run_id}.stderr.log"
            err_file.write_text(result.stderr)
            msg += f" -> stderr guardado en {err_file}"
    except Exception as e:
        elapsed = time.time() - start
        ok = False
        msg = f"EXCEPTION tras {elapsed:.1f}s: {e}"

    # Append al log de la campaña (un archivo, escritura serializada con lock)
    with lock:
        with open(log_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([run_id, "OK" if ok else "FAIL", msg, time.strftime("%Y-%m-%d %H:%M:%S")])

    return run_id, ok, msg


def load_completed_runs(log_path: Path) -> set[str]:
    """Lee el log existente y devuelve el set de run_ids que ya terminaron OK."""
    if not log_path.exists():
        return set()
    completed = set()
    with open(log_path, newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1] == "OK":
                completed.add(row[0])
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="CSV de configuración de la campaña")
    parser.add_argument("--jobs", "-j", type=int, default=1, help="Corridas en paralelo (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar comandos sin ejecutar")
    parser.add_argument("--resume", action="store_true", help="Saltear run_ids ya marcados OK en el log")
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(f"No existe el archivo de config: {args.config}")

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"{args.config.stem}.log.csv"

    with open(args.config, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        sys.exit("El config no tiene filas.")

    completed = load_completed_runs(log_path) if args.resume else set()
    pending = [r for r in rows if r["run_id"] not in completed]

    print(f"Campaña: {args.config.name}")
    print(f"Total filas: {len(rows)} | Ya completadas: {len(completed)} | Pendientes: {len(pending)}")
    if args.dry_run:
        print("--- DRY RUN: no se ejecuta nada, solo se muestran los comandos ---")

    lock = Lock()
    ok_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(run_one, row, args.dry_run, log_path, lock): row["run_id"] for row in pending}
        for future in as_completed(futures):
            run_id, ok, msg = future.result()
            status = "OK  " if ok else "FAIL"
            print(f"[{status}] {run_id}: {msg}")
            if ok:
                ok_count += 1
            else:
                fail_count += 1

    print(f"\nResumen: {ok_count} OK, {fail_count} FAIL (de {len(pending)} corridas intentadas)")
    if fail_count > 0:
        print(f"Revisá {log_path} y los .stderr.log en {LOG_DIR} para las que fallaron.")
        print(f"Podés re-correr solo las que faltan con --resume")


if __name__ == "__main__":
    main()
