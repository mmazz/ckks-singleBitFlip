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
            -I./src

LDFLAGS := -L$(HEAAN_SRC)/lib -L/usr/local/lib
LIBS    := -lHEAAN -lntl -lgmp -lm

# ------------------------------------------------
# Programs
# ------------------------------------------------

PROGRAMS := nn_mnist

TARGETS := $(addprefix $(BIN_DIR)/,$(PROGRAMS))
SRC := $(wildcard *.cpp)
OBJ := $(patsubst %.cpp,$(OBJ_DIR)/%.o,$(SRC))

DEP := $(OBJ:.o=.d)

# ------------------------------------------------

all: dirs $(TARGETS)

dirs:
	@mkdir -p $(BIN_DIR) $(OBJ_DIR)

# Link
$(BIN_DIR)/nn_mnist: $(OBJ)
	$(CXX) $^ -o $@ $(LDFLAGS) $(LIBS)
	@echo "✓ Built $@"


$(OBJ_DIR)/%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@
# Auto dependency include
-include $(DEP)

run:
	build/bin/nn_mnist 6 0 >> log.txt
	build/bin/nn_mnist 7 0 >> log.txt
	build/bin/nn_mnist 8 0 >> log.txt
	build/bin/nn_mnist 9 0 >> log.txt
	build/bin/nn_mnist 10 0 >> log.txt
	build/bin/nn_mnist 11 0 >> log.txt

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean dirs
