#!/usr/bin/env bash
set -euo pipefail

BIN=./build/bin/exhaustiveSingleBitFlip

START_SEED=1
END_SEED=100
LOGN=4
LOGQ=60
LOGDELTA=30
LOGSLOTS=2
WITHNTT=0
NUMLIMBS=1
VERBOSE=0
STAGE="encrypt_c0"


for ((SEED=START_SEED; SEED<=END_SEED; SEED++)); do
    echo "=== Running seed ${SEED} ==="
    ${BIN} --stage ${STAGE} --logN ${LOGN} --logQ ${LOGQ} --logDelta ${LOGDELTA} --logSlots ${LOGSLOTS}\
           --withNTT ${WITHNTT} --num_limbs ${NUMLIMBS} --verbose ${VERBOSE} --seed "${SEED}" --doMul 1
done
