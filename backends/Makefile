BIN_EXHAUSTIVE := ./build/bin/exhaustiveSingleBitFlip
BIN_RANDOM     := ./build/bin/randomSingleBitFlip
LIBRARY		   ?= heaan
ISCOMPLEX 	   ?= 0
SEEDS := 1 2 3 4 5

.PHONY: logN_analysis

seeds_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
		$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --bitPerCoeff 64 --logDelta 40 \
			--stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 ; \
		done; \
	done

seeds_analysis_mul:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
		$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --bitPerCoeff 64 --logDelta 40 \
			--stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 --doMul 2; \
		done; \
	done

encode_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 3 --logQ 60 --logDelta 40 --bitPerCoeff 130 --stage encode --logSlots 2 --seed 1 --withNTT 0 && \
	cd ../openfhe && \
	$(BIN_EXHAUSTIVE) --logN 3 --logQ 60 --logDelta 40  --stage encode --logSlots 2 --seed 1 --withNTT 0

encrypt_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 2 --logQ 60  --bitPerCoeff 64   --logDelta 40 --stage encrypt_c0 --logSlots 1 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 2 --logQ 60  --bitPerCoeff 64   --logDelta 40 --stage encrypt_c1 --logSlots 1 --seed 1 --withNTT 0

logN_analysis:
	@cd $(LIBRARY) && \
		$(BIN_RANDOM)     --logN 16 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed 1 --withNTT 0 && \
		$(BIN_RANDOM)     --logN 13 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed 1 --withNTT 0 && \
		$(BIN_RANDOM)     --logN 10 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed 1 --withNTT 0 && \
		$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0

logQ_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 40  --bitPerCoeff 50   --logDelta 30 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60  --bitPerCoeff 75   --logDelta 45 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 80  --bitPerCoeff 100  --logDelta 60 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 100 --bitPerCoeff 125  --logDelta 75 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0


logDelta_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 25 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 35 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 45 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 55 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0

gap_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 4 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 3 --seed 1 --withNTT 0

gap_analysis_c1:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c1 --logSlots 5 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c1 --logSlots 4 --seed 1 --withNTT 0 && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c1 --logSlots 3 --seed 1 --withNTT 0


add_rot_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doRot 1 --doAdd 1  --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doRot 1 --doAdd 1  --mult_depth 3

plain_mul_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doPlainMul 1  --mult_depth 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doPlainMul 1  --mult_depth 0

mul_analysis:
	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 3 --mult_depth 3 --isComplex $(ISCOMPLEX) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 1 --mult_depth 3 --isComplex $(ISCOMPLEX) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 2 --mult_depth 3 --isComplex $(ISCOMPLEX)

	@cd heaan && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 150 --logSlots 3 --doMul 3 --mult_depth 3 --isComplex $(ISCOMPLEX) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 150 --logSlots 3 --doMul 1 --mult_depth 3 --isComplex $(ISCOMPLEX) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 150 --logSlots 3 --doMul 2 --mult_depth 3 --isComplex $(ISCOMPLEX)

mul_analysis_RNS:
	@cd openfhe && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doMul 3 --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doMul 1 --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doMul 2 --mult_depth 3

	@cd openfhe && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doMul 3 --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doMul 1 --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doMul 2 --mult_depth 3

limb_analysis:
	@cd $(LIBRARY) && \
	$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 3 --mult_depth 5 --seed 1 --withNTT 0

add_analysis:
	@cd $(LIBRARY)&& \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c0  --logSlots 3 --doAdd 1 --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c1  --logSlots 3 --doAdd 1 --mult_depth 3

rot_analysis:
	@cd $(LIBRARY)&& \
	$(BIN_EXHAUSTIVE) --logN 6 --logSlots 3 --logQ 60 --logDelta 30 --stage encrypt_c0  --doRot 3 --mult_depth 3 --isComplex $(ISCOMPLEX) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logSlots 3 --logQ 60 --logDelta 30 --stage encrypt_c0  --doRot 2 --mult_depth 3 --isComplex $(ISCOMPLEX) && \
	$(BIN_EXHAUSTIVE) --logN 6 --logSlots 3 --logQ 60 --logDelta 30 --stage encrypt_c0  --doRot 1 --mult_depth 3 --isComplex $(ISCOMPLEX)

clean:
	rm -rf ../results



