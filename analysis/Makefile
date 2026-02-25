LIBRARY		   ?= heaan
ISCOMPLEX ?= 0
ANALYSIS_TARGETS := \
	seeds_analysis \
	seeds_analysis_mul \
	encode_analysis \
	encrypt_analysis \
	logN_analysis \
	logQ_analysis \
	logDelta_analysis \
	gap_analysis \
	mul_analysis \
	add_rot_analysis \
	add_analysis \
	rot_analysis \

ANALYSIS_TARGETS_RNS := \
	mul_analysis_RNS \
	add_analysis_RNS \
	add_rot_analysis_RNS \
	rot_analysis_RNS

.PHONY: $(ANALYSIS_TARGETS) $(ANALYSIS_TARGETS_RNS) all_analysis

all_analysis: $(ANALYSIS_TARGETS)

seeds_analysis:
	python3 seeds_analysis.py    --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0

seeds_analysis_mul:
	python3 seeds_analysis.py    --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0 --doMul 2

encode_analysis:
	python3 encode_analysis.py   --library $(LIBRARY) --logN 3  --logSlots 2  --logQ 60  --logDelta 40 --bitPerCoeff 130 --stage encode   --withNTT 0

encrypt_analysis:
	python3 encrypt_analysis.py  --library $(LIBRARY) --logN 2  --logSlots 1  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0  --withNTT 0

logN_analysis:
	python3 logN_analysis.py     --library $(LIBRARY) --logN 16 --logSlots 15 --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0

logQ_analysis:
	python3 logQ_analysis.py     --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 50 --bitPerCoeff 64  --stage encrypt_c0

logDelta_analysis:
	python3 logDelta_analysis.py --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 50 --bitPerCoeff 64  --stage encrypt_c0

gap_analysis:
	python3 gap_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0

mul_analysis:
	python3 mul_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 120 --logDelta 30 --bitPerCoeff 150 --stage encrypt_c0 --doMul 3 --mult_depth 0 --isComplex $(ISCOMPLEX)

mul_analysis_RNS:
	python3 mul_analysis.py      --library openfhe --logN 6  --logSlots 3  --logQ 60 --logDelta 50 --bitPerCoeff 64 --stage encrypt_c0 --doMul 3 --mult_depth 3 --title mul_RNS

add_rot_analysis:
	python3 add_rot_analysis.py  --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doRot 1 --doAdd 1

add_rot_analysis_RNS:
	python3 add_rot_analysis.py  --library openfhe --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doRot 1 --doAdd 1 --mult_depth 3 --title add_rot_RNS

add_analysis:
	python3 add_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doAdd 1 --title add

add_analysis_RNS:
	python3 add_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doAdd 1 --mult_depth 3 --title add_RNS

rot_analysis:
	python3 rot_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doRot 3 --mult_depth 0

rot_analysis_RNS:
	python3 rot_analysis.py      --library openfhe --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doRot 3 --mult_depth 3 --title rot_RNS

multibit:
	python3 multibit.py --library heaan --logN 10  --logQ 60 --bitPerCoeff 64 --logDelta 30 --stage encrypt_c0 --logSlots 9  --withNTT 0


heaanNN:
	python3 heaanNN.py --library heaanNN --logN 12  --logQ 220  --bitPerCoeff 250  --logDelta 30 --stage encrypt_c0 --logSlots 10  --withNTT 0

heaanNNop:
	python3 heaanNN.py --library heaanNN --logN 12  --logQ 220  --bitPerCoeff 250  --logDelta 30 --stage encrypt_c0 --logSlots 10  --withNTT 0 --doMul 1

openfheNN_enco:
	python3 heaanNN.py --library openfheNN --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50 --stage encode --logSlots 10  --withNTT 1 --mult_depth 5
openfheNN_encrC0:
	python3 heaanNN.py --library openfheNN --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50 --stage encrypt_c0 --logSlots 10  --withNTT 1 --mult_depth 5

openfheNN_encrC1:
	python3 heaanNN.py --library openfheNN --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50 --stage encrypt_c1 --logSlots 10  --withNTT 1 --mult_depth 5
openfheNN_decrC0:
	python3 heaanNN.py --library openfheNN --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50 --stage decrypt_c0 --logSlots 10  --withNTT 1 --mult_depth 5
openfheNN_decrC1:
	python3 heaanNN.py --library openfheNN --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50 --stage decrypt_c1 --logSlots 10  --withNTT 1 --mult_depth 5




