# CKKS Single-Bit Fault Injection Framework

This project studies **single-bit fault injection in CKKS-based FHE schemes** at the **RNS limb level**.

We inject faults by flipping **one bit of a `uint64_t` coefficient** belonging to a single CRT component (RNS limb). Faults can be injected in either:

- **Coefficient domain**
- **NTT domain**

at well-defined pipeline stages:

- `encode`
- `encrypt-c0`
- `encrypt-c1`
- `decrypt`

The goal is to analyze numerical degradation, error propagation, and Silent Data Corruption (SDC) behavior under precise, low-level faults.

---

## CKKS Libraries

In this work we foucs on two  libraries.
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
│ └── heaan/
│ └── src/ # HEAAN-specific campaign sources
│
├── setup_project.sh
└── results/
```
### Setup Script

`setup_project.sh` performs the following:

1. Downloads and builds the supported FHE libraries (OpenFHE, HEAAN)
2. Builds all fault-injection campaigns

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

## Dependencies

- `zlib`

---

## Notes

This framework is designed for **fine-grained fault modeling**, not performance benchmarking.
Correctness, reproducibility, and traceability of injected faults take priority over throughput.


