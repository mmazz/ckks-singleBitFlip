LIBRARY		   ?= heaan
ISCOMPLEX ?= 0
ANALYSIS_TARGETS := \
	add_analysis \
	mul_analysis \
	mulDepth_analysis \
	rescale_analysis \
	rot_analysis \

PARAMS = --logN 6 --logQ 120 --bitPerCoeff 144 --logDelta 40 --logSlots 4

.PHONY: $(ANALYSIS_TARGETS) $(ANALYSIS_TARGETS_RNS) all_analysis

all_analysis: $(ANALYSIS_TARGETS)

add_analysis:
	python3 insideOp_analysis.py --library $(LIBRARY) $(PARAMS) --stage add_inside --doAdd 2 --op_step 5 --title add_inside

mul_analysis:
	python3 insideOp_analysis.py --library $(LIBRARY) $(PARAMS) --stage mul_inside --doMul 1 --mult_depth 0 --op_step 25 --title mul_inside

mulDepth_analysis:
	python3 insideOp_analysis.py --library $(LIBRARY) $(PARAMS) --stage mul_inside --doMul 2 --mult_depth 0 --op_depth 1 --op_step 25 --title mulDepth_inside

rescale_analysis:
	python3 insideOp_analysis.py --library $(LIBRARY) $(PARAMS) --stage rescale_inside --doMul 2 --mult_depth 0 --op_step 3 --op_depth 0 --title rescale_inside

rot_analysis:
	python3 insideOp_analysis.py --library $(LIBRARY) $(PARAMS) --stage rot_inside --doRot 2 --op_step 11 --title rot_inside

add_analysis_registers:
	python3 register_analysis.py --library $(LIBRARY) $(PARAMS) --stage add_inside --doAdd 2 --op_step 5 --title add_inside_register

mul_analysis_registers:
	python3 register_analysis.py --library $(LIBRARY) $(PARAMS) --stage mul_inside --doMul 1 --mult_depth 0 --op_step 25 --title mul_inside_register

mulDepth_analysis_registers:
	python3 register_analysis.py --library $(LIBRARY) $(PARAMS) --stage mul_inside --doMul 2 --mult_depth 0 --op_depth 1 --op_step 25 --title mulDepth_inside_register

rescale_analysis_registers:
	python3 register_analysis.py --library $(LIBRARY) $(PARAMS) --stage rescale_inside --doMul 2 --mult_depth 0 --op_step 3 --op_depth 0 --title rescale_inside_register

rot_analysis_registers:
	python3 register_analysis.py --library $(LIBRARY) $(PARAMS) --stage rot_inside --doRot 2 --op_step 11 --title rot_inside_register
