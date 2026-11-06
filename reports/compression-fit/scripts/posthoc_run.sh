#!/usr/bin/env bash
# Post-hoc arm ll2d_2x (LLMLingua-2 + force_reserve_digit, as the gateway's non_sensitive route sets it) added AFTER the main results were seen.
# 1) calibrate its rate on dev items to ~2x and compress every test item  2) send base (repeat) and ll2d_2x prompts to the same local model, interleaved.
set -u
cd /c/Users/P7120489/litellm-gateway
CF=reports/compression-fit
cp -n $CF/raw/calibration.json $CF/raw/calibration_main_pass.json
cp -n $CF/raw/compressor_env.json $CF/raw/compressor_env_main_pass.json
export PYTHONPATH="C:/Users/P7120489/litellm-gateway/$CF/.pylib" HF_HUB_OFFLINE=1 PYTHONIOENCODING=utf-8
./.venv-compression/Scripts/python.exe $CF/scripts/compress_all.py --calibrate --only ll2d --run > $CF/raw/logs/posthoc_compress.log 2>&1
echo "compress exit=$?" >> $CF/raw/logs/posthoc_compress.log
unset PYTHONPATH
python $CF/scripts/run_llm.py --arms base,ll2d_2x --out $CF/raw/llm_runs_posthoc.jsonl > $CF/raw/logs/posthoc_llm.log 2>&1
echo "llm exit=$?" >> $CF/raw/logs/posthoc_llm.log
