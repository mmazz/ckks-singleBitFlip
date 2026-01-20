PROJECT_ROOT := $(shell cd ../.. && pwd)
HEAAN_SRC    := $(PROJECT_ROOT)/src/HEAAN-PRNG-Control
COMMON_SRC   := $(PROJECT_ROOT)/src/common

SRC_DIR   := src
BUILD_DIR := build
BIN_DIR   := $(BUILD_DIR)/bin
OBJ_DIR   := $(BUILD_DIR)/obj

CXX := g++
CXXFLAGS := -std=c++17 -O2 -pthread \
            -I$(HEAAN_SRC)/src \
            -I$(COMMON_SRC)

LDFLAGS := -L$(HEAAN_SRC)/lib -L/usr/local/lib
LIBS    := $(HEAAN_SRC)/lib/libHEAAN.a -lntl -lgmp -lm

$(shell mkdir -p $(BIN_DIR) $(OBJ_DIR))

# ---------------- Sources ----------------

COMMON_SOURCES := $(wildcard $(COMMON_SRC)/*.cpp)
COMMON_OBJECTS := $(patsubst $(COMMON_SRC)/%.cpp,$(OBJ_DIR)/common_%.o,$(COMMON_SOURCES))

HEAAN_SOURCES := backend.cpp
HEAAN_OBJECTS := $(OBJ_DIR)/backend.o

MAIN_SOURCE := exhaustiveSingleBitFlip.cpp
MAIN_OBJECT := $(OBJ_DIR)/exhaustiveSingleBitFlip.o
TARGET := $(BIN_DIR)/exhaustiveSingleBitFlip

# ---------------- Rules ----------------

all: $(TARGET)

# Common objects
$(OBJ_DIR)/common_%.o: $(COMMON_SRC)/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# HEAAN backend object
$(OBJ_DIR)/backend.o: $(SRC_DIR)/backend.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Main
$(OBJ_DIR)/exhaustiveSingleBitFlip.o: $(SRC_DIR)/exhaustiveSingleBitFlip.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJ_DIR)/randomSingleBitFlip.o: $(SRC_DIR)/randomSingleBitFlip.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@
# Link
$(TARGET): $(MAIN_OBJECT) $(HEAAN_OBJECTS) $(COMMON_OBJECTS)
	$(CXX) $^ -o $@ $(LDFLAGS) $(LIBS)
	@echo "✓ Built $@"

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
