PROJECT_ROOT := $(shell cd ../../../.. && pwd)
RUN_IDS := 0 1 2 3 4 5
RUNS := dirs $(addprefix run,$(RUN_IDS))
RUNS_nonNTT := dirs $(addprefix run_nonNTT,$(RUN_IDS))

.PHONY: allRuns $(RUNS)


allRuns: $(RUNS)


run0:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage encrypt_c0 --logSlots 10 --seed 0 --withNTT 1 --mult_depth 5
run1:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage encrypt_c1 --logSlots 10 --seed 0 --withNTT 1 --mult_depth 5
run2:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage encode --logSlots 10 --seed 0 --withNTT 1 --mult_depth 5
run3:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage decrypt_c0 --logSlots 10 --seed 0 --withNTT 1 --mult_depth 5
run4:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage decrypt_c1 --logSlots 10 --seed 0 --withNTT 1 --mult_depth 5
run5:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage decode --logSlots 10 --seed 0 --withNTT 1 --mult_depth 5

allRuns_nonNTT: $(RUNS_nonNTT)


run_nonNTT0:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage encrypt_c0 --logSlots 10 --seed 0 --withNTT 0 --mult_depth 5
run_nonNTT1:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage encrypt_c1 --logSlots 10 --seed 0 --withNTT 0 --mult_depth 5
run_nonNTT2:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage encode --logSlots 10 --seed 0 --withNTT 0 --mult_depth 5
run_nonNTT3:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage decrypt_c0 --logSlots 10 --seed 0 --withNTT 0 --mult_depth 5
run_nonNTT4:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage decrypt_c1 --logSlots 10 --seed 0 --withNTT 0 --mult_depth 5
run_nonNTT5:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 60  --bitPerCoeff 64  --logDelta 50   --stage decode --logSlots 10 --seed 0 --withNTT 0 --mult_depth 5


dirs:
	@mkdir -p $(BIN_DIR)

clean:
	rm -rf $(BUILD_DIR)


run0OP:
	build/bin/nn_mnist_randomBitFlipOp --logN 15  --logQ 336  --bitPerCoeff 250  --logDelta 30 --stage encrypt_c0 --logSlots 10 --seed 2 --withNTT 0 --doMul 1 --verbose

run:
	build/bin/nn_mnist 6 0 >> log.txt
	build/bin/nn_mnist 7 0 >> log.txt
	build/bin/nn_mnist 8 0 >> log.txt
	build/bin/nn_mnist 9 0 >> log.txt
	build/bin/nn_mnist 10 0 >> log.txt
	build/bin/nn_mnist 11 0 >> log.txt


