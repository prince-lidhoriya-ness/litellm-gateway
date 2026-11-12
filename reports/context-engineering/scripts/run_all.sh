#!/usr/bin/env bash
# Reproduces every live part of the benchmark (reports/context-engineering/REPORT.md). Run from litellm-gateway/:
#   bash reports/context-engineering/scripts/run_all.sh [proxy|quality|cache|validate|all]
# Needs: .venv-compression, Ollama on 127.0.0.1:11434 with llama3.2:3b (quality and cache phases), free ports 4011 (MOCK_PORT) and 4100.
# The in-process part is separate: python reports/context-engineering/scripts/offline_bench.py
set -u
PY=.venv-compression/Scripts/python
LITELLM=.venv-compression/Scripts/litellm
S=reports/context-engineering/scripts
RAW=reports/context-engineering/raw
PHASE=${1:-all}
mkdir -p "$RAW"
export PYTHONUTF8=1 LITELLM_LOCAL_MODEL_COST_MAP=True LITELLM_MASTER_KEY=sk-bench-local \
       MOCK_LLM_API_BASE=http://127.0.0.1:${MOCK_PORT:-4011}/v1 MOCK_LLM_API_KEY=mock-not-a-secret

# Benchmark profile "full" (bench_lib.PROFILE_ENV).
FULL="CONTEXT_COMPACTION_ENABLED=true JIT_RETRIEVAL_ENABLED=true JIT_RETRIEVAL_ON_CACHING_PROVIDERS=true CONTEXT_WINDOW_TOKENS=6000"

start_mock() {
  "$PY" prompt_compression/dev/mock_openai_server.py --port ${MOCK_PORT:-4011} > "$RAW/mock.log" 2>&1 &
  MOCK=$!
}

start_proxy() {   # $1: extra env assignments
  env $1 "$LITELLM" --config reports/context-engineering/bench_config.yaml --port 4100 > "$RAW/proxy_$2.log" 2>&1 &
  PROXY=$!
  for _ in $(seq 1 120); do
    curl -s -m 2 http://127.0.0.1:4100/health/liveliness > /dev/null && return 0
    sleep 2
  done
  echo "proxy did not start"; return 1
}

stop_proxy() { kill "$PROXY" 2>/dev/null; wait "$PROXY" 2>/dev/null; sleep 2; }

start_mock
trap 'kill $MOCK 2>/dev/null; kill ${PROXY:-0} 2>/dev/null' EXIT

if [[ $PHASE == all || $PHASE == proxy || $PHASE == quality || $PHASE == cache ]]; then
  start_proxy "$FULL" full || exit 1
  [[ $PHASE == all || $PHASE == proxy ]] && "$PY" "$S/proxy_bench.py"
  [[ $PHASE == all || $PHASE == proxy ]] && { stop_proxy; start_proxy "$FULL" full_reversed && "$PY" "$S/proxy_bench.py" --cold-reverse; }
  [[ $PHASE == all || $PHASE == quality ]] && "$PY" "$S/quality_bench.py"
  [[ $PHASE == all || $PHASE == cache ]] && "$PY" "$S/cache_bench.py"
  [[ $PHASE == all ]] && "$PY" "$S/validate_live.py" --expect full
  stop_proxy
fi

if [[ $PHASE == all || $PHASE == validate ]]; then
  [[ $PHASE == validate ]] && { start_proxy "$FULL" full && "$PY" "$S/validate_live.py" --expect full; stop_proxy; }
  start_proxy "CONTEXT_ENGINEERING_ENABLED=false" disabled && "$PY" "$S/validate_live.py" --expect disabled; stop_proxy
  start_proxy "$FULL OBSERVATION_MASKING_ENABLED=false" nomask && "$PY" "$S/validate_live.py" --expect nomask; stop_proxy
  start_proxy "$FULL CONTEXT_ENGINEERING_MODE=shadow" shadow && "$PY" "$S/validate_live.py" --expect shadow; stop_proxy
  start_proxy "$FULL CONTEXT_ENGINEERING_TIMEOUT_S=0.0001" timeout && "$PY" "$S/validate_live.py" --expect timeout; stop_proxy
fi
