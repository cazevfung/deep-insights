#!/usr/bin/env bash

# =============================================================
# Research Tool - Dependency Installer (macOS/Linux)
# =============================================================

set -o errexit
set -o pipefail
set -o nounset

SCRIPT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd
)"
cd "$SCRIPT_DIR"

echo "============================================================="
echo "Research Tool - Dependency Installer (macOS/Linux)"
echo "============================================================="
echo

PYTHON_CMD=""

check_python_candidate() {
  local candidate="$1"
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
      PYTHON_CMD="$candidate"
      return 0
    fi
  fi
  return 1
}

if ! check_python_candidate "python3"; then
  check_python_candidate "python" || true
fi

if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python 3.9+ not found!"
  echo "Please install Python 3.9 or newer from https://www.python.org/downloads/"
  echo "Ensure the interpreter is available as 'python3' (recommended) or 'python'."
  exit 1
fi

echo "Python found: $PYTHON_CMD"
"$PYTHON_CMD" --version
echo

echo "Testing Python execution..."
if ! "$PYTHON_CMD" -c "import sys; print('Python path:', sys.executable)"; then
  echo "Python test failed!"
  exit 1
fi
echo "Python test passed!"
echo

START_SERVER=1
HAS_START_ARG=0
ARGS=("$@")

for arg in "${ARGS[@]}"; do
  case "$arg" in
    --no-start)
      START_SERVER=0
      HAS_START_ARG=1
      ;;
    --start)
      START_SERVER=1
      HAS_START_ARG=1
      ;;
  esac
done

echo
echo "============================================================"
echo "Force quitting all server processes..."
echo "============================================================"
echo

PORTS=(3000 3001)

for port in "${PORTS[@]}"; do
  echo "Checking port $port..."
  if PIDS=$(lsof -ti tcp:"$port" -sTCP:LISTENING 2>/dev/null); then
    if [[ -n "$PIDS" ]]; then
      echo "  Gracefully stopping processes on port $port: $PIDS"
      while read -r pid; do
        if [[ -n "$pid" ]]; then
          kill "$pid" 2>/dev/null || true
        fi
      done <<<"$PIDS"

      sleep 1

      if PIDS=$(lsof -ti tcp:"$port" -sTCP:LISTENING 2>/dev/null); then
        if [[ -n "$PIDS" ]]; then
          echo "  Forcing kill on port $port: $PIDS"
          while read -r pid; do
            if [[ -n "$pid" ]]; then
              kill -9 "$pid" 2>/dev/null || true
            fi
          done <<<"$PIDS"
        fi
      fi
    fi
  fi
done

sleep 2

echo "Verifying ports are free..."
PORTS_IN_USE=()
for port in "${PORTS[@]}"; do
  if lsof -ti tcp:"$port" -sTCP:LISTENING >/dev/null 2>&1; then
    PORTS_IN_USE+=("$port")
  fi
done

if (( ${#PORTS_IN_USE[@]} > 0 )); then
  echo "Warning: Ports ${PORTS_IN_USE[*]} may still be in use."
  echo "If you encounter port conflicts, manually kill the processes or restart your computer."
else
  echo "All server ports are free."
fi

echo
echo "============================================================"
echo
echo "Starting dependency installation..."
echo

EXTRA_ARGS=("${ARGS[@]}")
if (( START_SERVER == 1 )) && (( HAS_START_ARG == 0 )); then
  EXTRA_ARGS+=("--start")
fi

set +o errexit
"$PYTHON_CMD" "$SCRIPT_DIR/install_dependencies.py" "${EXTRA_ARGS[@]}"
EXIT_CODE=$?
set -o errexit

if [[ $EXIT_CODE -ne 0 ]]; then
  echo
  echo "Installation completed with errors."
  echo "Exit code: $EXIT_CODE"
  echo
  exit "$EXIT_CODE"
fi

echo
echo "Installation completed successfully!"
echo

