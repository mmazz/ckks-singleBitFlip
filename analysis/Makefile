LIBRARY		   ?= heaan

seeds_analysis:
	python3 seeds_analysis.py    --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0

seeds_analysis_mul:
	python3 seeds_analysis.py    --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0 --doMul 2

encode_analysis:
	python3 encode_analysis.py   --library $(LIBRARY) --logN 3  --logSlots 2  --logQ 60  --logDelta 40 --bitPerCoeff 130 --stage encode     --seed 1 --withNTT 0

encrypt_analysis:
	python3 encrypt_analysis.py  --library $(LIBRARY) --logN 2  --logSlots 1  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0 --seed 1 --withNTT 0

logN_analysis:
	python3 logN_analysis.py     --library $(LIBRARY) --logN 16 --logSlots 15 --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0

logQ_analysis:
	python3 logQ_analysis.py     --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 50 --bitPerCoeff 64  --stage encrypt_c0

logDelta_analysis:
	python3 logDelta_analysis.py --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 50 --bitPerCoeff 64  --stage encrypt_c0

gap_analysis:
	python3 gap_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 5  --logQ 60  --logDelta 40 --bitPerCoeff 64  --stage encrypt_c0

mul_analysis:
	python3 mul_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 120 --logDelta 30 --bitPerCoeff 150 --stage encrypt_c0 --doMul 3 --mult_depth 0

add_rot_analysis:
	python3 add_rot_analysis.py  --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c1 --doRot 1 --doAdd 1

add_rot_analysis_RNS:
	python3 add_rot_analysis.py  --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c1 --doRot 1 --doAdd 1 --mult_depth 3

add_analysis:
	python3 add_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doAdd 1 --title add

add_analysis_RNS:
	python3 add_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doAdd 1 --mult_depth 3 --title add_RNS

rot_analysis:
	python3 rot_analysis.py      --library $(LIBRARY) --logN 6  --logSlots 3  --logQ 60  --logDelta 30 --bitPerCoeff 64  --stage encrypt_c0 --doRot 3



heaanNN:
	python3 heaanNN.py --library heaanNN --logN 12  --logQ 220  --bitPerCoeff 250  --logDelta 30 --stage encrypt_c0 --logSlots 10 --seed 2 --withNTT 0



