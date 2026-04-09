# CKKS Single-Bit Fault Injection Framework

This project studies **single-bit fault injection in CKKS-based FHE schemes** at the **RNS limb level** or without **RNS***.

We inject faults by flipping **one bit of a `uint64_t` coefficient** belonging to a single CRT component (RNS limb) or NTL objetct. Faults can be injected in either:

- **Coefficient domain**
- **NTT domain**

at well-defined pipeline stages:

- Client-side
    - `encode`
    - `encrypt_c0`
    - `encrypt_c1`
    - `decrypt_c0`
    - `decrypt_c1`
    - `decode`
- Server-side
    - `mul_inside`: op_index = [0, doMul], op_step = [0,12]
    - `mul_outside`: op_index = [0, doMul]
    - `hidden_layer`: library=heaanNN, op_index = [0, 11]
    - `chebyTanh3`: library=heaanNN, op_index = [0, 9]

The goal is to analyze numerical degradation, error propagation, and Silent Data Corruption (SDC) behavior under precise, low-level faults.

## Server operations

We define a control flow, were we can choose which operations to make, in some
cases how many sucecive make, but not the order. The order is fix, in this order:

- Operations:
    - Addition: only one
    - Plain multiplication: can choose how many of them
    - Cipher cipher multiplications: can choose how many of them
    - Rotation: only one, can chose the amount of the rotation in powers of two
    - Bootstrapping: only one at the end
---

## CKKS Libraries

In this work we focus on two libraries.
HEAAN for a vanilla version without RNS and NTT, and OpenFHE as state of the
art.
For both we create our own fork with some changes in order to get totally
control of the PRNG.

The installer clone and compile both.
For further reading the repositories of each are:

```
github.com/mmazz/HEAAN-PRNG-Control
github.com/mmazz/openfhe-PRNG-Control
```

---

## Project Structure
```
├── analyse/
│ └── Python scripts for post-processing and data analysis
│
├── src/
│ ├── Third-party libraries (OpenFHE, HEAAN)
│ └── Common components (campaign loggers, helpers, utilities)
│
├── backends/
│ ├── openfhe/
│ │ └── src/ # OpenFHE-specific campaign sources
|  └── nn_mnist/
|    └── src/ # Openfhe-NN specific campaign sources
│ └── heaan/
│ └── src/ # HEAAN-specific campaign sources
|  └── nn_mnist/
|    └── src/ # HEAAN-NN specific campaign sources
│
├── setup_project.sh
└── results/
```
### Setup Script

`setup_project.sh` performs the following:

1. Downloads and builds the supported FHE libraries (OpenFHE, HEAAN)
2. Builds all fault-injection campaigns


---

### Running

The main campaings are setup in the `makefile`.
In there some options are available to change some parameters inside the
`makefile`:
- LIBRARY: heaan or openfhe
- ISCOMPLEX: 1 or 0
    - If the input value is complex or real. Only available for heaan.
- Which type of experiment:
    - Random single bit flips: randomSingleBitFlip
    - Random multi bit flips: randomMultiBitFlip
    - Exhaustive single bit flips: exhaustiveSingleBitFlip

And all the scheme parameters.

### Example
Random bits flip at encoding stage with a ring dimention of 64 doing one
addition followed by two multiplications.

```
./ckks-singleBitFlip/backends/heaan/build/bin/randomSingleBitFlip --logN 6
--logQ 60 --bitPerCoeff 64 --logDelta 30 --logSlot 4 --doAdd 1 --doMul 2 --stage
encode
```


| Parámetro     | Descripción |
|--------------|-------------|
| logN         |   Ring dimention          |
| logQ         |   Total modulus          |
| logDelta     |   Scaling factor         |
| logSlot      |   Total input size         |
| bitPerCoeff  |   Size of the "registers"         |
| mult_depth   |             |
| withNTT      |    If NTT is avialable: only openfhe        |
| stage        |   Stage to attack        |
| verbose      |   -          |
| doAdd        |   one addition at start         |
| doMul        |   Amount of sucecive cipher multilicatios    |
| doPlainMul   |   Amount of sucecive plain multilicatios     |
| doRot        |   One Rotation of that power of 2          |
| doBoot       |   Make boot strap at the end of operations          |
| op_index     |   If valid, operation index within the stage |
| op_step      |   If valid, at  which steo of the inside of the selected operation to attack   |



---

## Results Layout

After running a campaign, a new directory is created under `results/` containing:

- **`campaign_start.csv`**
  One row per campaign execution, including:
  - Unique `campaign_id`
  - All configuration parameters

- **`campaign_end.csv`**
  One row per completed campaign, including:
  - `campaign_id`
  - Execution time
  - Aggregated statistics (e.g., P95 L2 norm, error metrics)

- **`data/` directory**
  Contains **one CSV file per campaign**, with:
  - One row per injected bit flip
  - Detailed fault-level measurements

---

## Campaign Execution Model

- **Multiprocessing is supported**
- **Multithreading is intentionally not used**

Parallelism is achieved by running **multiple independent campaigns in parallel**, not by parallelizing a single campaign.

⚠️ **Important note**
CSV flushing and file appends are **not fully synchronized across processes**.
Race conditions are avoided by design assumptions (append-only files, campaign-level isolation), but no explicit locking is implemented.

---

## Core Components

### `campaign_arguments.*`
- Parses command-line arguments
- Validates campaign configuration

### `campaign_registry.*`
Responsible for **global campaign bookkeeping**:
- Assigns a unique `campaign_id` (atomic, inter-process safe)
- Appends to the global `campaign_start.csv`
- Appends to the global `campaign_end.csv`
- **Append-only semantics**
- No per-campaign data logging

### `campaign_logger.*`
- Writes **per-campaign CSV files** (bit-flip–level data)
- Thread-safe at the local level
- **Never interacts with the registry automatically**

### `campaign_helper.*`
High-level orchestration:
- Parses arguments
- Creates the campaign registry
- Registers campaign start
- Instantiates the campaign logger
- Registers campaign completion at shutdown

---

## Dependencies (in progress)

- `zlib`

---

## Notes

This framework is designed for **fine-grained fault modeling**, not performance benchmarking.
Correctness, reproducibility, and traceability of injected faults take priority over throughput.


