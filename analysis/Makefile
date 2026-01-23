
logN_analysis:
	python3 logN_analysis.py --logN 16 --logQ 60 --logDelta 50 --library heaan --stage encrypt_c0 --bitPerCoeff 64 --logSlots 15

logQ_analysis:
	python3 logQ_analysis.py --logN 6 --logDelta 50 --library heaan --stage encrypt_c0 --bitPerCoeff 64

logDelta_analysis:
	python3 logDelta_analysis.py --logN 3 --logQ 60  --library heaan --stage encrypt_c0 --bitPerCoeff 64 --logSlots 2

seeds_analysis:
	python3 seeds_analysis.py --logN 6 --logQ 60 --logDelta 40 --library heaan --stage encrypt_c0 --bitPerCoeff 64 --logSlots 5

gap_analysis:
	python3 gap_analysis.py --logN 6 --logQ 60 --logDelta 40 --library heaan --stage encrypt_c0 --bitPerCoeff 64 --logSlots 5

mul_analysis:
	python3 gap_analysis.py --library heaan --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 4 --doMul 3
	python3 gap_analysis.py --library heaan --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 4 --doMul 2
	python3 gap_analysis.py --library heaan --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 4 --doMul 1
