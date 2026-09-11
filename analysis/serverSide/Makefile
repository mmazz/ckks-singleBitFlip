RES ?= ../../results
LIB ?= heaan
P    = logN=6 logQ=120 bitsPerCoeff=144 logDelta=40 logSlots=4
REG  = python3 register_analysis.py --results $(RES)

add_registers:
	$(REG) --title add_register     --where library=$(LIB) $(P) stage=add     "pipeline=add x2"
mul_registers:
	$(REG) --title mul_register     --where library=$(LIB) $(P) stage=mul     "pipeline=mul"
rescale_registers:
	$(REG) --title rescale_register --where library=$(LIB) $(P) stage=rescale "pipeline=mul x2"
rot_registers:
	$(REG) --title rot_register     --where library=$(LIB) $(P) stage=rot     "pipeline=rot 2"j
