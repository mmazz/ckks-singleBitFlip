#!/usr/bin/env python3

import sys
from pathlib import Path

import pandas as pd


# ============================================================
# Mapping:
#
#   (stage, op_step) -> {
#       doAdd,
#       doPlainMul,
#       doMul,
#       doRot
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
        "doAdd": 2,
        "doPlainMul": 3,
        "doMul": 2,
        "doRot": 1,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 1): {
        "doAdd": 2,
        "doPlainMul": 3,
        "doMul": 2,
        "doRot": 1,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Después de multByPoly(W1)
    # Queda reduceSum + bias + cheby
    ("hidden_layer", 2): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 1,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 3): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 1,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Antes de la rotación seleccionada dentro de reduceSum
    ("hidden_layer", 4): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 1,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 5): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 1,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Después de hacer la rotación, antes del add
    ("hidden_layer", 6): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 7): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Flip en s antes del add del reduceSum
    ("hidden_layer", 8): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 9): {
        "doAdd": 2,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Después del add del reduceSum seleccionado
    ("hidden_layer", 10): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 11): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Después del bias de hidden layer.
    # Solo queda cheby.
    ("hidden_layer", 12): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("hidden_layer", 13): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },


    # --------------------------------------------------------
    # cheby_tanh3
    # --------------------------------------------------------

    # Antes de square(s):
    # square -> mult -> 2 PlainMul -> add
    ("cheby_tanh3", 0): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("cheby_tanh3", 1): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 2,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },

    # square ya ocurrió:
    # mult -> 2 PlainMul -> add
    ("cheby_tanh3", 2): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 1,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("cheby_tanh3", 3): {
        "doAdd": 1,
        "doPlainMul": 2,
        "doMul": 1,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },

    # c3 ya se calculó.
    # El error está solamente en s:
    # s * 0.98 -> add
    ("cheby_tanh3", 4): {
        "doAdd": 1,
        "doPlainMul": 1,
        "doMul": 0,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("cheby_tanh3", 5): {
        "doAdd": 1,
        "doPlainMul": 1,
        "doMul": 0,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Justo antes de s * 0.98
    ("cheby_tanh3", 6): {
        "doAdd": 1,
        "doPlainMul": 1,
        "doMul": 0,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("cheby_tanh3", 7): {
        "doAdd": 1,
        "doPlainMul": 1,
        "doMul": 0,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # Después de s * 0.98.
    # Solo queda c3 + s.
    ("cheby_tanh3", 8): {
        "doAdd": 1,
        "doPlainMul": 0,
        "doMul": 0,
        "doRot": 0,
        "stage": "encrypt_c0",
        "op_step": 0,
    },
    ("cheby_tanh3", 9): {
        "doAdd": 1,
        "doPlainMul": 0,
        "doMul": 0,
        "doRot": 0,
        "stage": "encrypt_c1",
        "op_step": 0,
    },

    # deco y decypt

     ("decrypt_c0", 0): {
        "doAdd": 0,
        "doPlainMul": 0,
        "doMul": 0,
        "doRot": 0,
        "stage": "decrypt_c0",
        "op_step": 0,
    }, 
     ("decrypt_c1", 0): {
        "doAdd": 0,
        "doPlainMul": 0,
        "doMul": 0,
        "doRot": 0,
        "stage": "decrypt_c0",
        "op_step": 0,
    },
     ("decode", 0): {
        "doAdd": 0,
        "doPlainMul": 0,
        "doMul": 0,
        "doRot": 0,
        "stage": "decode",
        "op_step": 0,
    },
}

DEFAULT_OPS = {
    "doAdd": 2,
    "doPlainMul": 3,
    "doMul": 2,
    "doRot": 1,
}


def get_remaining_ops(stage: str, op_step: int) -> dict:
    key = (stage, op_step)

    if key in PIPELINE_MAPPING:
        return PIPELINE_MAPPING[key]

    # Stage no perteneciente al mapping de NN:
    # conservar stage/op_step originales y usar operaciones default.
    return {
        "stage": stage,
        "op_step": op_step,
        **DEFAULT_OPS,
    }

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} input.csv")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    output_path = input_path.with_name(
        f"{input_path.stem}_NN{input_path.suffix}"
    )

    df = pd.read_csv(input_path)

    required = ["stage", "op_step"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}"
        )

    # Guardar ubicación original de la NN para debugging/análisis
    df["original_stage"] = df["stage"]
    df["original_op_step"] = df["op_step"]

    # --------------------------------------------------------
    # Hacer mapping.
    #
    # hidden_layer / cheby_tanh3:
    #   se traducen al pipeline básico.
    #
    # cualquier otro stage:
    #   conserva stage/op_step y recibe DEFAULT_OPS.
    # --------------------------------------------------------
    features = df.apply(
        lambda row: pd.Series(
            get_remaining_ops(
                str(row["stage"]),
                int(row["op_step"]),
            )
        ),
        axis=1,
    )

    # Sobrescribir stage/op_step
    df["stage"] = features["stage"]
    df["op_step"] = features["op_step"]

    # Sobrescribir operaciones
    df["doAdd"] = features["doAdd"]
    df["doPlainMul"] = features["doPlainMul"]
    df["doMul"] = features["doMul"]
    df["doRot"] = features["doRot"]

    # Opcionales
    if "doBoot" in features.columns:
        df["doBoot"] = features["doBoot"]

    if "op_depth" in features.columns:
        df["op_depth"] = features["op_depth"]

    df.to_csv(output_path, index=False)

    print(output_path)


if __name__ == "__main__":
    main()
