#!/usr/bin/env python3
"""
Rewrite NN-pipeline injection sites into basic-pipeline terms.

A fault injected during encrypted NN inference is recorded at an NN-specific
location (hidden_layer step 4, cheby_tanh3 step 2, ...). The severity model was
trained on the basic HEAAN pipeline and has never seen those stage names. What
it did learn is how severity depends on the operations still to be applied to
the ciphertext after the injection point.

So each (stage, op_step) of the NN is translated into:
  - an equivalent basic-pipeline stage the model knows, and
  - the operations that remain: doAdd, doPlainMul, doMul, doRot

The original location is preserved in original_stage / original_op_step /
original_op_depth so results can be reported against the real NN site. Those
columns are pass-through metadata: prepare_heaan.py keeps them and the trainer
never uses them as features.

Rows whose (stage, op_step) is not in the mapping are left COMPLETELY untouched
— stage, op_step and their own operation counts all survive. That matters when
the input mixes NN campaigns with basic-pipeline ones.

A row whose stage appears elsewhere in the mapping but whose op_step does not is
a hole in the table, not a basic-pipeline row. Those are reported and, unless
--allow-holes is given, abort the run: leaving them alone sends the model a
stage it has never seen, which silently produces an all-zero one-hot.

Usage:
    python3 NN_modeling.py campaigns_start.csv
    python3 NN_modeling.py campaigns_start.csv -o campaigns_nn.csv
    python3 NN_modeling.py campaigns_start.csv --report
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


# ============================================================
# Mapping:
#
#   (stage, op_step) -> {
#       doAdd, doPlainMul, doMul, doRot,   # operations still to come
#       stage, op_step,                    # equivalent basic-pipeline site
#       op_depth,   (optional)             # only if it must be overridden
#       doBoot,     (optional)
#   }
#
# Estos valores se definen UNA VEZ de acuerdo con la
# aproximación que decidamos para la NN.
# ============================================================
PIPELINE_MAPPING = {
    # --------------------------------------------------------
    # hidden_layer
    # --------------------------------------------------------

    # Antes de multByPoly(W1)
    # Queda W1 PlainMul + reduceSum + bias + cheby
    ("hidden_layer", 0): {
        "doAdd": 2, "doPlainMul": 3, "doMul": 2, "doRot": 1,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 1): {
        "doAdd": 2, "doPlainMul": 3, "doMul": 2, "doRot": 1,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Después de multByPoly(W1)
    # Queda reduceSum + bias + cheby
    ("hidden_layer", 2): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 1,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 3): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 1,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Antes de la rotación seleccionada dentro de reduceSum
    ("hidden_layer", 4): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 1,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 5): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 1,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Después de hacer la rotación, antes del add
    ("hidden_layer", 6): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 7): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Flip en s antes del add del reduceSum
    ("hidden_layer", 8): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 9): {
        "doAdd": 2, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Después del add del reduceSum seleccionado
    ("hidden_layer", 10): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 11): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Después del bias de hidden layer.
    # Solo queda cheby.
    ("hidden_layer", 12): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("hidden_layer", 13): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # --------------------------------------------------------
    # cheby_tanh3
    # --------------------------------------------------------

    # Antes de square(s):
    # square -> mult -> 2 PlainMul -> add
    ("cheby_tanh3", 0): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("cheby_tanh3", 1): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 2, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },

    # square ya ocurrió:
    # mult -> 2 PlainMul -> add
    ("cheby_tanh3", 2): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 1, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("cheby_tanh3", 3): {
        "doAdd": 1, "doPlainMul": 2, "doMul": 1, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },

    # c3 ya se calculó.
    # El error está solamente en s:
    # s * 0.98 -> add
    ("cheby_tanh3", 4): {
        "doAdd": 1, "doPlainMul": 1, "doMul": 0, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("cheby_tanh3", 5): {
        "doAdd": 1, "doPlainMul": 1, "doMul": 0, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Justo antes de s * 0.98
    ("cheby_tanh3", 6): {
        "doAdd": 1, "doPlainMul": 1, "doMul": 0, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("cheby_tanh3", 7): {
        "doAdd": 1, "doPlainMul": 1, "doMul": 0, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # Después de s * 0.98.
    # Solo queda c3 + s.
    ("cheby_tanh3", 8): {
        "doAdd": 1, "doPlainMul": 0, "doMul": 0, "doRot": 0,
        "stage": "encrypt_c0", "op_step": 0,
    },
    ("cheby_tanh3", 9): {
        "doAdd": 1, "doPlainMul": 0, "doMul": 0, "doRot": 0,
        "stage": "encrypt_c1", "op_step": 0,
    },

    # --------------------------------------------------------
    # deco y decrypt — nada queda por aplicar
    # --------------------------------------------------------
    ("decrypt_c0", 0): {
        "doAdd": 0, "doPlainMul": 0, "doMul": 0, "doRot": 0,
        "stage": "decrypt_c0", "op_step": 0,
    },
    # NOTE: this deliberately maps to decrypt_c0, not decrypt_c1. If the model
    # was trained with a distinct decrypt_c1 stage, change it — as written, both
    # halves are treated as the same site.
    ("decrypt_c1", 0): {
        "doAdd": 0, "doPlainMul": 0, "doMul": 0, "doRot": 0,
        "stage": "decrypt_c0", "op_step": 0,
    },
    ("decode", 0): {
        "doAdd": 0, "doPlainMul": 0, "doMul": 0, "doRot": 0,
        "stage": "decode", "op_step": 0,
    },
}

OP_COLUMNS = ["doAdd", "doPlainMul", "doMul", "doRot"]
REQUIRED_KEYS = OP_COLUMNS + ["stage", "op_step"]
OPTIONAL_KEYS = ["op_depth", "doBoot"]


def validate_mapping() -> None:
    """Catch a malformed table at startup rather than halfway through a run."""
    problems = []

    for key, entry in PIPELINE_MAPPING.items():
        if not (isinstance(key, tuple) and len(key) == 2):
            problems.append(f"{key!r}: key must be (stage, op_step)")
            continue

        missing = [k for k in REQUIRED_KEYS if k not in entry]
        if missing:
            problems.append(f"{key!r}: missing {missing}")

        unknown = [k for k in entry if k not in REQUIRED_KEYS + OPTIONAL_KEYS]
        if unknown:
            problems.append(f"{key!r}: unknown keys {unknown}")

    if problems:
        sys.exit("PIPELINE_MAPPING is malformed:\n  " + "\n  ".join(problems))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", help="campaigns_start.csv to rewrite")
    ap.add_argument(
        "-o",
        "--out",
        default=None,
        metavar="CSV",
        help="output path (default: <input>_NN.csv)",
    )
    ap.add_argument(
        "--allow-holes",
        action="store_true",
        help=(
            "do not abort when a stage present in the mapping has an op_step "
            "that is not — those rows pass through unmapped"
        ),
    )
    ap.add_argument(
        "--report",
        action="store_true",
        help="print the full (stage, op_step) -> mapped site table",
    )
    args = ap.parse_args()

    validate_mapping()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"no such file: {input_path}")

    out_path = (
        Path(args.out)
        if args.out
        else input_path.with_name(f"{input_path.stem}_NN{input_path.suffix}")
    )

    df = pd.read_csv(input_path)

    missing = [c for c in ("stage", "op_step") if c not in df.columns]
    if missing:
        sys.exit(f"{input_path.name} is missing required columns: {missing}")

    # -- preserve the real location ----------------------------------------

    df["original_stage"] = df["stage"].astype(str)
    df["original_op_step"] = df["op_step"]
    if "op_depth" in df.columns:
        df["original_op_depth"] = df["op_depth"]

    # -- apply the mapping, vectorised --------------------------------------

    keys = list(
        zip(df["stage"].astype(str), pd.to_numeric(df["op_step"], errors="coerce")
            .fillna(-1).astype(int))
    )
    hit = pd.Series([k in PIPELINE_MAPPING for k in keys], index=df.index)

    n_total = len(df)
    n_mapped = int(hit.sum())

    if n_mapped:
        entries = pd.DataFrame(
            [PIPELINE_MAPPING[k] for k, h in zip(keys, hit) if h],
            index=df.index[hit],
        )
        for col in REQUIRED_KEYS:
            df.loc[hit, col] = entries[col]

        # Optional overrides apply only where the entry actually provides one,
        # so a row's real op_depth / doBoot survives unless deliberately replaced.
        for col in OPTIONAL_KEYS:
            if col in entries.columns:
                have = entries[col].notna()
                if have.any():
                    if col not in df.columns:
                        df[col] = pd.NA
                    df.loc[entries.index[have], col] = entries.loc[have, col]

    # -- unmapped rows: untouched, but classify them -------------------------

    mapped_stages = {s for s, _ in PIPELINE_MAPPING}
    unmapped = df.index[~hit]

    holes = [
        (s, o)
        for i, (s, o) in zip(df.index, keys)
        if i in set(unmapped) and s in mapped_stages
    ]
    foreign = sorted(
        {s for i, (s, o) in zip(df.index, keys) if i in set(unmapped) and s not in mapped_stages}
    )

    print(f"{n_total:,} campaigns · {n_mapped:,} mapped · {n_total - n_mapped:,} untouched")

    if foreign:
        print(
            "  not part of the NN mapping, passed through with their own stage, "
            "op_step and operation counts: " + ", ".join(foreign)
        )

    if holes:
        counts = pd.Series(holes).value_counts()
        print(f"\n  {len(holes):,} row(s) hit a HOLE in the mapping:")
        for (stage, op_step), n in counts.items():
            print(f"    ({stage}, op_step={op_step})  {n:,} row(s)")
        print(
            "  These keep an NN stage name the severity model has never seen, so\n"
            "  every stage_* one-hot will be zero and the prediction is garbage.\n"
            "  Add them to PIPELINE_MAPPING, or pass --allow-holes to proceed."
        )
        if not args.allow_holes:
            return 1

    if args.report:
        table = pd.DataFrame(
            [
                {
                    "nn_stage": s,
                    "nn_op_step": o,
                    "-> stage": e["stage"],
                    "-> op_step": e["op_step"],
                    **{k: e[k] for k in OP_COLUMNS},
                }
                for (s, o), e in sorted(PIPELINE_MAPPING.items())
            ]
        )
        print("\nMapping table")
        print(table.to_string(index=False))

    df.to_csv(out_path, index=False)
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
