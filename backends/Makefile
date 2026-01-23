BIN_EXHAUSTIVE := ./build/bin/exhaustiveSingleBitFlip
BIN_RANDOM     := ./build/bin/randomSingleBitFlip
SEEDS := 1 2 3 4 5

.PHONY: logN_analysis

logQ_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 40  --bitPerCoeff 50  --logN 6 --logDelta 30 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60  --bitPerCoeff 75  --logN 6 --logDelta 45 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 80  --bitPerCoeff 100 --logN 6 --logDelta 60 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 100 --bitPerCoeff 125 --logN 6 --logDelta 75 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0

logN_analysis:
	@cd heaan && \
	$(BIN_RANDOM)     --logN 16 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0

logDelta_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 3  --logQ 60   --logDelta 20 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 2 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 3  --logQ 60   --logDelta 30 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 2 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 3  --logQ 60   --logDelta 40 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 2 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 3  --logQ 60   --logDelta 50 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 2 --seed 1 --withNTT 0

gap_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 4 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 3 --seed 1 --withNTT 0

seeds_analysis:
	@cd heaan && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
		$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --bitPerCoeff 64 --logDelta 40 \
			--stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 ; \
	done


mul_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 4 --doMul 3 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 3 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 2 --doMul 3 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 4 --doMul 2 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 2 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 2 --doMul 2 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 4 --doMul 2 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 1 && \
	$(BIN_EXHAUSTIVE) --logN 5 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 2 --doMul 1
