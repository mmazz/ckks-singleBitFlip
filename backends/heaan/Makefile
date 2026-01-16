PROJECT_ROOT := $(shell cd ../.. && pwd)
HEAAN_SRC := $(PROJECT_ROOT)/src/HEAAN-PRNG-Control
COMMON_SRC := $(PROJECT_ROOT)/src/common

CXX := g++
CXXFLAGS := -std=c++17 -O2 -I$(HEAAN_SRC)/src -pthread

# Separar LDFLAGS (directorios) de LIBS (bibliotecas)
LDFLAGS := -L$(HEAAN_SRC)/lib -L/usr/local/lib
LIBS := $(HEAAN_SRC)/lib/libHEAAN.a -I$(COMMON_SRC) -lntl -lgmp -lm

# Directorios
BUILD_DIR := build
BIN_DIR := $(BUILD_DIR)/bin
SRC_DIR := src

# Crear directorios si no existen
$(shell mkdir -p $(BIN_DIR))

# Archivos fuente
SOURCES := $(wildcard $(SRC_DIR)/*.cpp)
TARGETS := $(patsubst $(SRC_DIR)/%.cpp,$(BIN_DIR)/%,$(SOURCES))

# Regla principal
all: $(TARGETS)

# Compilar utils (NO necesita LDFLAGS ni LIBS en compilación, solo al linkear)
$(BIN_DIR)/utils.o: $(SRC_DIR)/utils_heaan.cpp $(SRC_DIR)/utils_heaan.h
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Compilar ejecutables - ORDEN CORRECTO: objects primero, luego libs
$(BIN_DIR)/%: $(SRC_DIR)/%.cpp $(BIN_DIR)/utils.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS) $(LIBS)
	@echo "✓ Compilado: $@"
# Limpiar
clean:
	rm -rf $(BUILD_DIR)
	@echo "✓ Limpieza completada"

# Mostrar configuración
info:
	@echo "Project Root: $(PROJECT_ROOT)"
	@echo "HEAAN Source: $(HEAAN_SRC)"
	@echo "Build Dir: $(BUILD_DIR)"
	@echo "Sources: $(SOURCES)"
	@echo "Targets: $(TARGETS)"

.PHONY: all clean info
