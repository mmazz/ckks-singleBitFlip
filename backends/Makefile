BIN_EXHAUSTIVE := ./build/bin/exhaustiveSingleBitFlip
BIN_RANDOM     := ./build/bin/randomSingleBitFlip
BIN_RANDOM_MULTI     := ./build/bin/randomMultiBitFlip
LIBRARY		   ?= heaan
ISCOMPLEX 	   ?= 0
SEEDS := 1 2 3 4
MULTIPLE_SEEDS := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15

ANALYSES = seeds_analysis encode_analysis_heaan encode_analysis_openfhe encrypt_analysis logN_analysis logQ_analysis logDelta_analysis gap_analysis gap_analysis_c1 add_rot_analysis plain_mul_analysis mul_analysis_c1 mul_analysis_c0  add_analysis rot_analysis
ANALYSES_RNS = mul_analysis_c0_RNS mul_analysis_c1_RNS limb_analysis

EXTRAS = seeds_analysis_mul

.PHONY: all_analysis $(ANALYSES) $(ANALYSES_RNS)

all_analysis: $(ANALYSES)

RNS_analysis: $(ANALYSES_RNS)


seeds_analysis:
	@cd $(LIBRARY) && \
	for s in $(MULTIPLE_SEEDS); do \
		for s_input in $(MULTIPLE_SEEDS); do \
		$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --bitPerCoeff 64 --logDelta 40 \
			--stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 ; \
		done; \
	done

seeds_analysis_mul:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
		$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --bitPerCoeff 64 --logDelta 30 \
			--stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 --doMul 2; \
		done; \
	done

encode_analysis_heaan:
	@cd heaan && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 3 --logQ 60 --logDelta 40 --bitPerCoeff 130 --stage encode --logSlots 2 --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done

encode_analysis_openfhe:
	cd ../openfhe && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 3 --logQ 60 --logDelta 40  --stage encode --logSlots 2 --withNTT 0 --seed $$s --seed_input $$s_input; \
		done; \
	done

encrypt_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 2 --logQ 60  --bitPerCoeff 64   --logDelta 40 --stage encrypt_c0 --logSlots 1 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 2 --logQ 60  --bitPerCoeff 64   --logDelta 40 --stage encrypt_c1 --logSlots 1 --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done

logN_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_RANDOM)     --logN 16 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_RANDOM)     --logN 13 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_RANDOM)     --logN 10 --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 15 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5  --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done

logQ_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 40  --bitPerCoeff 50   --logDelta 30 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60  --bitPerCoeff 75   --logDelta 45 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 80  --bitPerCoeff 100  --logDelta 60 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 100 --bitPerCoeff 125  --logDelta 75 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done


logDelta_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 25 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 35 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 45 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60   --logDelta 55 --bitPerCoeff 64 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done

gap_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 4 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 3 --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done

gap_analysis_c1:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c1 --logSlots 5 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c1 --logSlots 4 --seed $$s --seed_input $$s_input --withNTT 0 && \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c1 --logSlots 3 --seed $$s --seed_input $$s_input --withNTT 0; \
		done; \
	done


add_rot_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doRot 1 --doAdd 1 --seed $$s --seed_input $$s_input --mult_depth 3 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doRot 1 --doAdd 1 --seed $$s --seed_input $$s_input --mult_depth 3; \
		done; \
	done

plain_mul_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doPlainMul 1 --seed $$s --seed_input $$s_input --mult_depth 0 && \
	$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doPlainMul 1 --seed $$s --seed_input $$s_input --mult_depth 0; \
		done; \
	done

mul_analysis_c1:
	@cd heaan && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 3 --mult_depth 3 --isComplex $(ISCOMPLEX) --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 1 --mult_depth 3 --isComplex $(ISCOMPLEX) --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c0 --bitPerCoeff 150 --logSlots 3 --doMul 2 --mult_depth 3 --isComplex $(ISCOMPLEX) --seed $$s --seed_input $$s_input; \
		done; \
	done

mul_analysis_c0:
	@cd heaan && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 150 --logSlots 3 --doMul 3 --mult_depth 3 --isComplex $(ISCOMPLEX)  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 150 --logSlots 3 --doMul 1 --mult_depth 3 --isComplex $(ISCOMPLEX)  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 120 --logDelta 30 --stage encrypt_c1 --bitPerCoeff 150 --logSlots 3 --doMul 2 --mult_depth 3 --isComplex $(ISCOMPLEX) --seed $$s --seed_input $$s_input; \
		done; \
	done

add_analysis:
	@cd $(LIBRARY)&& \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c0  --logSlots 3 --doAdd 1 --mult_depth 3  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 30 --stage encrypt_c1  --logSlots 3 --doAdd 1 --mult_depth 3 --seed $$s --seed_input $$s_input; \
		done; \
	done

rot_analysis:
	@cd $(LIBRARY)&& \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logSlots 3 --logQ 60 --logDelta 30 --stage encrypt_c0  --doRot 3 --mult_depth 3 --isComplex $(ISCOMPLEX) --seed $$s --seed_input $$s_input  && \
			$(BIN_EXHAUSTIVE) --logN 6 --logSlots 3 --logQ 60 --logDelta 30 --stage encrypt_c0  --doRot 2 --mult_depth 3 --isComplex $(ISCOMPLEX)  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logSlots 3 --logQ 60 --logDelta 30 --stage encrypt_c0  --doRot 1 --mult_depth 3 --isComplex $(ISCOMPLEX) --seed $$s --seed_input $$s_input; \
		done; \
	done

mul_analysis_c0_RNS:
	@cd openfhe && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doMul 3 --mult_depth 3  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doMul 1 --mult_depth 3  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c0 --bitPerCoeff 64 --logSlots 3 --doMul 2 --mult_depth 3 --seed $$s --seed_input $$s_input; \
		done; \
	done

mul_analysis_c1_RNS:
	@cd openfhe && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doMul 3 --mult_depth 3  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doMul 1 --mult_depth 3  --seed $$s --seed_input $$s_input && \
			$(BIN_EXHAUSTIVE) --logN 6 --logQ 60 --logDelta 50 --stage encrypt_c1 --bitPerCoeff 64 --logSlots 3 --doMul 2 --mult_depth 3 --seed $$s --seed_input $$s_input; \
		done; \
	done

limb_analysis:
	@cd $(LIBRARY) && \
	for s in $(SEEDS); do \
		for s_input in $(SEEDS); do \
			$(BIN_EXHAUSTIVE) --logN 6  --logQ 60  --bitPerCoeff 64  --logDelta 40 --stage encrypt_c0 --logSlots 3 --mult_depth 5 --withNTT 0 --seed $$s --seed_input $$s_input; \
		done; \
	done

multi_analysis:
	@cd heaan && \
	for s in $(SEEDS); do \
		$(BIN_RANDOM_MULTI)     --logN 10 --logQ 60  --bitPerCoeff 64  --logDelta 30 --stage encrypt_c0 --logSlots 9 --seed $$s --seed_input $$s --withNTT 0 && \
		$(BIN_RANDOM_MULTI)     --logN 10 --logQ 60  --bitPerCoeff 64  --logDelta 30 --stage encrypt_c0 --logSlots 7 --seed $$s --seed_input $$s --withNTT 0 && \
		$(BIN_RANDOM_MULTI)     --logN 10 --logQ 60  --bitPerCoeff 64  --logDelta 30 --stage encrypt_c0 --logSlots 5 --seed $$s --seed_input $$s --withNTT 0; \
	done

mult_boot_analysis:
	@cd heaan && \
	./build/bin/bootPerformance --logN 14 --logQ 160  --bitPerCoeff 180  --logDelta 30 --stage encrypt_c0 --logSlots 9 --seed 0 --seed_input 0 --withNTT 0 --doBoot 1\

clean:
	rm -rf ../results



