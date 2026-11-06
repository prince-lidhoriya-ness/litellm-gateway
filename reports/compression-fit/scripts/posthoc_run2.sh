#!/usr/bin/env bash
# Second post-hoc arm ll2g_gw: LLMLingua-2 at the gateway's literal non_sensitive setting (rate 0.6, force_reserve_digit=True), added after the main results were seen.
# Run after posthoc_run.sh has finished (both measure latency, so they must not overlap).
set -u
cd /c/Users/P7120489/litellm-gateway
CF=reports/compression-fit
export PYTHONPATH="C:/Users/P7120489/litellm-gateway/$CF/.pylib" HF_HUB_OFFLINE=1 PYTHONIOENCODING=utf-8
./.venv-compression/Scripts/python.exe $CF/scripts/compress_all.py --run > $CF/raw/logs/posthoc2_compress.log 2>&1
echo "compress exit=$?" >> $CF/raw/logs/posthoc2_compress.log
unset PYTHONPATH
python $CF/scripts/run_llm.py --arms ll2g_gw --out $CF/raw/llm_runs_posthoc.jsonl > $CF/raw/logs/posthoc2_llm.log 2>&1
echo "llm exit=$?" >> $CF/raw/logs/posthoc2_llm.log
