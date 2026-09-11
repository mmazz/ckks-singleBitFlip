RES   ?= ../results
LIB   ?= heaan
CURVE  = python3 bit_curve.py    --results $(RES)
REG    = python3 register_map.py --results $(RES)
P      = library=$(LIB) logN=6 logSlots=5 logQ=60 logDelta=40 bitsPerCoeff=64

# --- cliente ---
encrypt:      ; $(CURVE) --title encrypt_c0 --where $(P) stage=encrypt_c0 pipeline=
encrypt_reg:  ; $(REG)   --title encrypt_c0 --where $(P) stage=encrypt_c0 pipeline=
gap:          ; $(CURVE) --title gap        --where $(P) stage=encrypt_c0 pipeline= --split gap
seeds:        ; $(CURVE) --title seeds      --where $(P) stage=encrypt_c0 pipeline= --vary seed
stages:       ; $(CURVE) --title stages     --where $(P) pipeline= --vary stage
logQ:         ; $(CURVE) --title logQ       --where library=$(LIB) logN=6 stage=encrypt_c0 pipeline= --vary logQ --xnorm over_q
libs:         ; $(CURVE) --title libs       --where logN=6 logQ=60 stage=encrypt_c0 pipeline= --vary library

# --- servidor: una figura por op_step ---
PS = library=$(LIB) logN=6 logSlots=4 logQ=120 logDelta=40 bitsPerCoeff=144
add_inside:   ; $(CURVE) --title add_inside --where $(PS) stage=add "pipeline=add x2" --per op_step --split gap
mul_inside:   ; $(CURVE) --title mul_inside --where $(PS) stage=mul pipeline=mul      --per op_step --split gap
mul_reg:      ; $(REG)   --title mul_inside --where $(PS) stage=mul pipeline=mul      --op_step all
