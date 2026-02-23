PROJECT_ROOT := $(shell cd ../.. && pwd)
HEAAN_SRC    := $(PROJECT_ROOT)/src/HEAAN-PRNG-Control
COMMON_SRC   := $(PROJECT_ROOT)/src/common

SRC_DIR   := src
BUILD_DIR := build
BIN_DIR   := $(BUILD_DIR)/bin
OBJ_DIR   := $(BUILD_DIR)/obj

CXX := g++
CXXFLAGS := -std=c++17 -O2 -pthread -MMD -MP \
            -I$(HEAAN_SRC)/src \
            -I$(COMMON_SRC)

LDFLAGS := -L$(HEAAN_SRC)/lib -L/usr/local/lib
LIBS    := -lHEAAN -lntl -lgmp -lm

# ---------- Programs ----------

PROGRAMS := exhaustiveSingleBitFlip randomSingleBitFlip randomMultiBitFlip bootPerformance

COMMON_SOURCES := $(wildcard $(COMMON_SRC)/*.cpp)
COMMON_OBJECTS := $(patsubst $(COMMON_SRC)/%.cpp,$(OBJ_DIR)/common_%.o,$(COMMON_SOURCES))

BACKEND_OBJ := $(OBJ_DIR)/backend.o

# ---------- Targets ----------

all: dirs $(PROGRAMS:%=$(BIN_DIR)/%)

dirs:
	mkdir -p $(BIN_DIR) $(OBJ_DIR)

# Common
$(OBJ_DIR)/common_%.o: $(COMMON_SRC)/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Backend
$(OBJ_DIR)/backend.o: $(SRC_DIR)/backend.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Main objects
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Link each binary with its own main
$(BIN_DIR)/%: $(OBJ_DIR)/%.o $(BACKEND_OBJ) $(COMMON_OBJECTS)
	$(CXX) $^ -o $@ $(LDFLAGS) $(LIBS)
	@echo "✓ Built $@"

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
