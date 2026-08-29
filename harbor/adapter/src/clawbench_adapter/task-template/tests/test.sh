#!/bin/bash
set -euo pipefail
# Stop the recorder, snapshot /data, then score:
#  Stage 1  interception.json must match the task's eval-schema (url_pattern + method)
#  Stage 2  LLM judge (CLAWBENCH_JUDGE_*) confirms the intercepted payload fulfils the instruction
# reward = 1.0 iff both stages pass; written to /logs/verifier/reward.txt + reward.json
curl -sf -X POST http://127.0.0.1:7878/api/stop || true
curl -sf -X POST http://127.0.0.1:7878/api/stop-recording || true
sleep 2
rm -f /data/.stop-requested
rm -rf /logs/verifier/data
cp -a /data /logs/verifier/data
/app/src/runtime-server/.venv/bin/python /app/src/harbor/verify.py
/app/src/runtime-server/.venv/bin/python /app/src/harbor/cleanup-email.py || true
