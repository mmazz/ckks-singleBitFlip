BIN_EXHAUSTIVE := ./build/bin/exhaustiveSingleBitFlip
BIN_RANDOM     := ./build/bin/randomSingleBitFlip
SEEDS := 1 2 3 4 5

.PHONY: logN_analysis

logQ_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logQ 40  --bitPerCoeff 50  --logN 6 --logDelta 30 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logQ 60  --bitPerCoeff 75  --logN 6 --logDelta 45 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logQ 80  --bitPerCoeff 100 --logN 6 --logDelta 60 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logQ 100 --bitPerCoeff 125 --logN 6 --logDelta 75 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0

logN_analysis:
	@cd heaan && \
	$(BIN_RANDOM)     --logN 16 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0

gap_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 4 --seed 1 --withNTT 0
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 3 --seed 1 --withNTT 0

seeds_analysis:
	@cd heaan && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
		$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --bitPerCoeff 64 --logDelta 40 \
			--stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 ; \
	done

