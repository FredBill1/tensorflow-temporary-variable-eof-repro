#!/usr/bin/env bash
# Three matching cases, run with the instrumented 2.18.1 wheel.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$ROOT/diagnostics/results}"
IMAGE="${IMAGE:-tf-tempvar-instrumented:2.18.1}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd -P)"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image $IMAGE not found. Run ./diagnostics/build.sh first." >&2
  exit 2
fi
mismatches=0
run_case() {
  local name="$1" expect="$2"; shift 2
  local dir="$OUT/$name"
  mkdir -p "$dir"
  echo "==== $name (expected: $expect) ===="
  local exit_code=0
  docker run --rm --platform linux/amd64 --cpus="${CPUS:-8}" \
    -v "$ROOT/repro.py:/app/repro.py:ro" \
    -e TF_CPP_MIN_LOG_LEVEL=0 \
    "$IMAGE" "$@" >"$dir/run.log" 2>&1 || exit_code=$?
  printf '%d\n' "$exit_code" >"$dir/exit_code.txt"
  python3 "$ROOT/diagnostics/analyze.py" "$dir/run.log" >"$dir/summary.txt"
  cat "$dir/summary.txt"
  local actual='UNEXPECTED'
  if [[ "$exit_code" -ne 0 ]] && grep -Eq 'ALREADY_EXISTS|AlreadyExistsError' "$dir/run.log"; then
    actual='ALREADY_EXISTS'
  elif [[ "$exit_code" -eq 0 ]] && grep -q 'Epoch 3/3' "$dir/run.log"; then
    actual='PASS'
  fi
  echo "Exit code: $exit_code; observed: $actual"
  if [[ "$actual" != "$expect" ]]; then
    echo "WARNING: unexpected result; inspect $dir/run.log" >&2
    mismatches=$((mismatches+1))
  fi
  if ! grep -q 'TFRES FUNCTION_RUN_OPTIONS' "$dir/run.log"; then
    echo 'WARNING: instrumented C++ logging not seen; verify build and wheel.' >&2
    mismatches=$((mismatches+1))
  fi
}
run_case bad_addn_unknown ALREADY_EXISTS
run_case known_cardinality PASS --known-cardinality
run_case stack_sum PASS --stack
printf '\nLogs and summaries: %s\n' "$OUT"
if (( mismatches > 0 )); then exit 1; fi
