#!/usr/bin/env bash
set -euo pipefail

BIN=./build/bin/exhaustiveSingleBitFlip

START_SEED=1
END_SEED=1000

for ((SEED=START_SEED; SEED<=END_SEED; SEED++)); do
    echo "=== Running seed ${SEED} ==="
    ${BIN} \
        --stage encrypt_c0 \
        --logN 4 \
        --logQ 60 \
        --logDelta 30 \
        --withNTT 0 \
        --num_limbs 1 \
        --verbose 1 \
        --seed "${SEED}"
done
