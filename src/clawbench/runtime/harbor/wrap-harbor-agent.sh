#!/bin/bash
set -euo pipefail

wrap_agent() {
  local executable=$1
  local path real

  path=$(command -v "$executable" 2>/dev/null || true)
  if [[ -z "$path" && -x "$HOME/.local/bin/$executable" ]]; then
    path="$HOME/.local/bin/$executable"
  fi
  [[ -n "$path" && -x "$path" ]] || return 0

  real="${path}.clawbench-real"
  if [[ ! -e "$real" ]]; then
    mv "$path" "$real"
  fi

  cat >"$path" <<'WRAPPER'
#!/bin/bash
set +e

real="${BASH_SOURCE[0]}.clawbench-real"
stop_file=${CLAWBENCH_STOP_FILE:-/data/.stop-requested}
stop_result=${CLAWBENCH_STOP_RESULT:-/data/agent-stop.json}
rm -f "$stop_file" "$stop_result"

"$real" "$@" <&0 &
agent_pid=$!
(
  while kill -0 "$agent_pid" 2>/dev/null; do
    if [[ -f "$stop_file" ]]; then
      detected_at=$(date +%s.%N)
      printf '{"stop_detected_at":%s,"signal":"INT"}\n' "$detected_at" >"$stop_result"
      kill -INT "$agent_pid" 2>/dev/null || true
      for _ in $(seq 1 20); do
        kill -0 "$agent_pid" 2>/dev/null || break
        sleep 0.1
      done
      if kill -0 "$agent_pid" 2>/dev/null; then
        kill -TERM "$agent_pid" 2>/dev/null || true
      fi
      exit 0
    fi
    sleep 0.1
  done
) &
watcher_pid=$!

wait "$agent_pid"
status=$?
kill "$watcher_pid" 2>/dev/null || true
wait "$watcher_pid" 2>/dev/null || true

if [[ -f "$stop_file" ]]; then
  exit 0
fi
exit "$status"
WRAPPER
  chmod 0755 "$path"
}

if (( $# > 0 )); then
  for executable in "$@"; do
    wrap_agent "$executable"
  done
else
  wrap_agent claude
  wrap_agent codex
fi
