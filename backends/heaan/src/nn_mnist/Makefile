PROJECT_ROOT := $(shell cd ../../../.. && pwd)

HEAAN_SRC  := $(PROJECT_ROOT)/src/HEAAN-PRNG-Control
COMMON_SRC := $(PROJECT_ROOT)/src/common

BUILD_DIR := build
BIN_DIR   := $(BUILD_DIR)/bin
OBJ_DIR   := $(BUILD_DIR)/obj

CXX := g++

CXXFLAGS := -std=c++17 -O2 -pthread -MMD -MP \
            -I$(HEAAN_SRC)/src \
            -I$(COMMON_SRC) \
            -Isrc

LDFLAGS := -L$(HEAAN_SRC)/lib -L/usr/local/lib
LIBS    := -lHEAAN -lntl -lgmp -lm


# ------------------------------------------------
# Detect mains automatically
# (todo archivo que NO empiece con utils)
# ------------------------------------------------

MAINS := $(filter-out src/utils%.cpp,$(wildcard src/*.cpp))

PROGRAMS := $(notdir $(MAINS:.cpp=))
TARGETS  := $(addprefix $(BIN_DIR)/,$(PROGRAMS))


# ------------------------------------------------
# Utils / shared code
# ------------------------------------------------

UTILS_SRC := $(filter src/utils%.cpp,$(wildcard src/*.cpp)) \
             $(wildcard $(COMMON_SRC)/*.cpp)

UTILS_OBJ := $(patsubst %.cpp,$(OBJ_DIR)/%.o,$(UTILS_SRC))


# ------------------------------------------------

all: dirs $(TARGETS)

dirs:
	@mkdir -p $(BIN_DIR)


# ------------------------------------------------
# Link rule PER TARGET
# solo linkea SU main + utils
# ------------------------------------------------

$(BIN_DIR)/%: src/%.cpp $(UTILS_OBJ)
	@mkdir -p $(dir $@)

	$(CXX) $(CXXFLAGS) -c $< -o $(OBJ_DIR)/$<.o

	$(CXX) \
	    $(OBJ_DIR)/$<.o \
	    $(UTILS_OBJ) \
	    -o $@ \
	    $(LDFLAGS) $(LIBS)

	@echo "✓ Built $@"


# ------------------------------------------------
# Compile utils
# ------------------------------------------------

$(OBJ_DIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c $< -o $@



clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean dirs

run_bitflips:
	build/bin/nn_mnist_randomBitFlip --logN 12  --logQ 220  --bitPerCoeff 250  --logDelta 30 --stage encrypt_c0 --logSlots 10 --seed 3 --withNTT 0

run:
	build/bin/nn_mnist 6 0 >> log.txt
	build/bin/nn_mnist 7 0 >> log.txt
	build/bin/nn_mnist 8 0 >> log.txt
	build/bin/nn_mnist 9 0 >> log.txt
	build/bin/nn_mnist 10 0 >> log.txt
	build/bin/nn_mnist 11 0 >> log.txt


