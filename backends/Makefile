JOBS := 6

all: firstAnalysis clientOps serverOps serverOps_boot NNServerOps

firstAnalysis:
	python3 run_campaign.py configs/logN_analysis.csv     --jobs $(JOBS) && \
	python3 run_campaign.py configs/gap_analysis.csv      --jobs $(JOBS) && \
	python3 run_campaign.py configs/logQ_analysis.csv     --jobs $(JOBS) && \
	python3 run_campaign.py configs/seeds_analysis.csv    --jobs $(JOBS) && \
	python3 run_campaign.py configs/logDelta_analysis.csv --jobs $(JOBS) && \
	python3 run_campaign.py configs/input_analysis.csv    --jobs $(JOBS) && \
	python3 run_campaign.py configs/heaan_VS_openfhe_plain_analysis.csv  --jobs $(JOBS) && \
	python3 run_campaign.py configs/heaan_plain_VS_c0_VS_c1_analysis.csv --jobs $(JOBS)

clientOps:
	python3 run_campaign.py configs/opClientAdd_analysis.csv        --jobs $(JOBS) && \
	python3 run_campaign.py configs/opClientAddRot_analysis.csv     --jobs $(JOBS) && \
	python3 run_campaign.py configs/opClientAddRot_RNS_analysis.csv --jobs $(JOBS) && \
	python3 run_campaign.py configs/opClientMul_analysis.csv        --jobs $(JOBS) && \
	python3 run_campaign.py configs/opClientRot_analysis.csv        --jobs $(JOBS) && \
	python3 run_campaign.py configs/boot_analysis.csv               --jobs $(JOBS)

NNServerOps:
	python3 run_campaign.py configs/heaanNN_cheby_analysis.csv  --jobs $(JOBS) && \
	python3 run_campaign.py configs/heaanNN_analysis.csv        --jobs $(JOBS) && \
	python3 run_campaign.py configs/heaanNN_hidden_analysis.csv --jobs $(JOBS) && \
	python3 run_campaign.py configs/openfheNN_analysis.csv      --jobs $(JOBS)

serverOps:
	python3 run_campaign.py configs/opServerAdd_analysis.csv      --jobs $(JOBS) && \
	python3 run_campaign.py configs/opServerMulDepth_analysis.csv --jobs $(JOBS) && \
	python3 run_campaign.py configs/opServerMul_analysis.csv      --jobs $(JOBS) && \
	python3 run_campaign.py configs/opServerRescaleDepth_analysis.csv  --jobs $(JOBS) && \
	python3 run_campaign.py configs/opServerRot_analysis.csv      --jobs $(JOBS)

serverOps_boot:
	python3 run_campaign.py configs/bootEval_analysis.csv      --jobs $(JOBS) && \
	python3 run_campaign.py configs/bootOutside_analysis.csv      --jobs $(JOBS)

temp:
	python3 run_campaign.py configs/bootOutside_analysis.csv      --jobs $(JOBS)
