BIN_EXHAUSTIVE := ./build/bin/exhaustiveSingleBitFlip

.PHONY: logN_analysis

logQ_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logQ 40  --bitPerCoeff 50  --logN 6 --logDelta 30 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logQ 60  --bitPerCoeff 75  --logN 6 --logDelta 45 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logQ 80  --bitPerCoeff 100 --logN 6 --logDelta 60 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logQ 100 --bitPerCoeff 125 --logN 6 --logDelta 75 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0


