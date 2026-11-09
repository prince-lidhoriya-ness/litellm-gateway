#!/usr/bin/env bash
# Runs the prompt-compression evals with the quality-gates toolkit:
#   Gate 4 (live HTTP cases, evals/cases/*.yaml) against the running gateway, then the benchmark scorer
#   (evals/score_results.py) on the B2 result files. Output: evals/results/<phase>/{gate4,compression}.json
#
#   bash evals/run_evals.sh [phase]          default phase: litellm-eval
# Env: QG_DIR (quality-gates folder), RUN (benchmark run id, default B2), PY (python with pyyaml)
# Needs: the gateway on :4000, Ollama for obs-priced-llama. The capture mock on :4010 is started if it is not running.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PHASE="${1:-litellm-eval}"
: "${QG_DIR:=C:/AI-office/jenkins-setup/quality-gates/quality-gates}" "${RUN:=B2}" "${PY:=.venv-compression/Scripts/python}"
export QG_DIR EVALS_DIR="$PWD/evals" THRESHOLDS_FILE="$PWD/evals/thresholds.yaml" RESULTS_DIR="$PWD/evals/results"
# The API key comes from .env and only lives in this process's environment (cases use {{env:LITELLM_MASTER_KEY}}).
LITELLM_MASTER_KEY="$(grep -E '^LITELLM_MASTER_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"'"'"'\r')"
export LITELLM_MASTER_KEY
[ -n "$LITELLM_MASTER_KEY" ] || { echo "LITELLM_MASTER_KEY not found in .env"; exit 2; }

MOCK_PID=""
if ! curl -s -o /dev/null -X POST http://127.0.0.1:4010/v1/chat/completions -H 'Content-Type: application/json' -d '{}'; then
  "$PY" reports/pipeline-proof/scripts/capture_mock.py --port 4010 >/dev/null 2>&1 &
  MOCK_PID=$!
  for _ in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:4010/docs && break; sleep 1; done
fi
trap '[ -n "$MOCK_PID" ] && kill "$MOCK_PID" 2>/dev/null' EXIT

rm -rf "evals/results/$PHASE"
echo ">> Gate 4: live cases ($(grep -c '^- id:' evals/cases/*.yaml) cases)"
"$PY" "$QG_DIR/gates/gate4.py" --phase "$PHASE"; G4=$?
echo ">> Benchmark results ($RUN) against evals/thresholds.yaml"
"$PY" evals/score_results.py --phase "$PHASE" --run "$RUN"; SC=$?
python_ok=$("$PY" -c "import json,sys;print(all(json.load(open(f'evals/results/$PHASE/{g}.json'))['passed'] for g in ('gate4','compression')))")
echo ">> overall: $python_ok   (details: evals/results/$PHASE/)"
[ "$python_ok" = "True" ] && exit 0 || exit 1
