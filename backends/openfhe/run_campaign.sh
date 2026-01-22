#!/usr/bin/env bash
set -euo pipefail

BIN=./build/bin/exhaustiveSingleBitFlip

START_SEED=1
END_SEED=10
LOGN=6
LOGQ=60
LOGDELTA=50
LOGSLOTS=5
WITHNTT=0
NUMLIMBS=1
VERBOSE=0
STAGE="encrypt_c0"


for ((SEED=START_SEED; SEED<=END_SEED; SEED++)); do
    echo "=== Running seed ${SEED} ==="
    ${BIN} --stage ${STAGE} --logN ${LOGN} --logQ ${LOGQ} --logDelta ${LOGDELTA} --logSlots ${LOGSLOTS}\
           --withNTT ${WITHNTT} --num_limbs ${NUMLIMBS} --verbose ${VERBOSE} --seed 12345 --seed-input "${SEED}"
done

