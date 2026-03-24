#!/usr/bin/env bash
# Smoke test: run each source script and validate JSON output.
# Requires network access. Not for CI — for manual validation.
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$ROOT_DIR/scripts/sources"
PYTHON="${ROOT_DIR}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
FAILURES=0

for script in "$SCRIPT_DIR"/*.py; do
  name=$(basename "$script")
  # Skip __init__.py files
  [ "$name" = "__init__.py" ] && continue
  echo "Testing $name..."
  output=$("$PYTHON" "$script" 2>&1) || {
    echo "  FAIL: $name exited with error"
    echo "  $output"
    FAILURES=$((FAILURES + 1))
    continue
  }
  # Validate JSON array
  echo "$output" | python3 -c "import sys,json; d=json.load(sys.stdin); assert isinstance(d,list), 'Not a list'" 2>&1 || {
    echo "  FAIL: $name did not output a valid JSON array"
    FAILURES=$((FAILURES + 1))
    continue
  }
  count=$(echo "$output" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  echo "  OK: $count items"
done

if [ $FAILURES -gt 0 ]; then
  echo "FAILED: $FAILURES script(s) failed"
  exit 1
fi
echo "All smoke tests passed"
