#!/usr/bin/env bash

set -Eeuo pipefail

AUTO_STOP_AFTER_SECONDS=0
if [[ $# -ge 2 && "$1" == "--auto-stop-after-seconds" ]]; then
  AUTO_STOP_AFTER_SECONDS="$2"
elif [[ $# -ge 1 ]]; then
  printf '[ERROR] Unsupported arguments. Usage: %s [--auto-stop-after-seconds N]\n' "$0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/src/frontend"
ENV_NAME="win-auto-installer"

cleanup_done=false
stop_reason=""
vite_pid=""
electron_pid=""
timer_pid=""

cleanup() {
  if [[ "$cleanup_done" == true ]]; then
    return
  fi
  cleanup_done=true

  printf '\n[INFO] Cleaning up resources...\n'

  if [[ -n "$timer_pid" ]] && kill -0 "$timer_pid" >/dev/null 2>&1; then
    kill "$timer_pid" >/dev/null 2>&1 || true
  fi

  if [[ -n "$electron_pid" ]] && kill -0 "$electron_pid" >/dev/null 2>&1; then
    printf '[INFO] Stopping Electron process tree (PID: %s)...\n' "$electron_pid"
    pkill -TERM -P "$electron_pid" >/dev/null 2>&1 || true
    kill "$electron_pid" >/dev/null 2>&1 || true
  fi

  if [[ -n "$vite_pid" ]] && kill -0 "$vite_pid" >/dev/null 2>&1; then
    printf '[INFO] Stopping Vite process tree (PID: %s)...\n' "$vite_pid"
    pkill -TERM -P "$vite_pid" >/dev/null 2>&1 || true
    kill "$vite_pid" >/dev/null 2>&1 || true
  fi

  if command -v lsof >/dev/null 2>&1; then
    while IFS= read -r port_pid; do
      [[ -z "$port_pid" ]] && continue
      kill "$port_pid" >/dev/null 2>&1 || true
    done < <(lsof -ti tcp:5173 -sTCP:LISTEN 2>/dev/null || true)
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k 5173/tcp >/dev/null 2>&1 || true
  fi

  printf '[INFO] Development server stopped\n'
}

on_sigint() {
  stop_reason="sigint"
  exit 130
}

on_sigterm() {
  if [[ -z "$stop_reason" ]]; then
    stop_reason="sigterm"
  fi
  exit 0
}

trap cleanup EXIT
trap on_sigint INT
trap on_sigterm TERM

wait_for_vite_server() {
  local attempts=30
  local delay_seconds=0.5
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if (echo > /dev/tcp/127.0.0.1/5173) >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay_seconds"
  done
  return 1
}

get_conda_prefix() {
  local line
  while IFS= read -r line; do
    case "$line" in
      "$ENV_NAME "*|"$ENV_NAME"$'\t'*)
        printf '%s\n' "${line##* }"
        return 0
        ;;
    esac
  done < <(conda env list)
  return 1
}

printf '================================\n'
printf 'Windows Auto Installer - Dev Mode\n'
printf '================================\n\n'

printf '[1/3] Checking Conda environment...\n'
if ! command -v conda >/dev/null 2>&1; then
  printf '[ERROR] Conda is not available in PATH. Please run ./scripts/setup_env.sh first.\n'
  exit 1
fi

if ! conda env list | grep -Eq "^[[:space:]]*$ENV_NAME([[:space:]]|$)"; then
  printf '[ERROR] Cannot use Conda environment, please run ./scripts/setup_env.sh first.\n'
  exit 1
fi
printf '[OK] Conda environment ready\n\n'

printf '[2/3] Checking frontend dependencies...\n'
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  printf '[INFO] Frontend dependencies not installed, installing...\n'
  npm install --prefix "$FRONTEND_DIR"
fi
printf '[OK] Frontend dependencies ready\n\n'

printf '[3/3] Starting development server...\n\n'
printf '================================\n'
printf 'Starting Vite dev server and Electron...\n'
printf '================================\n\n'
printf 'Tips:\n'
printf -- '- Vite will run on http://localhost:5173\n'
printf -- '- Electron window will open automatically\n'
printf -- '- Press Ctrl+C to stop server\n'
printf -- '- Make sure the Conda environment is available, Python backend will start automatically\n\n'

printf '[INFO] Checking if port 5173 is in use...\n'
if command -v lsof >/dev/null 2>&1; then
  while IFS= read -r port_pid; do
    [[ -z "$port_pid" ]] && continue
    printf '[INFO] Port 5173 is in use, PID: %s\n' "$port_pid"
    kill "$port_pid" >/dev/null 2>&1 || printf '[WARN] Failed to stop process %s\n' "$port_pid"
  done < <(lsof -ti tcp:5173 -sTCP:LISTEN 2>/dev/null || true)
elif command -v fuser >/dev/null 2>&1; then
  fuser -k 5173/tcp >/dev/null 2>&1 || true
fi

node_path="$(command -v node)"
conda_prefix="$(get_conda_prefix || true)"
vite_script="$FRONTEND_DIR/node_modules/vite/bin/vite.js"
electron_cli="$FRONTEND_DIR/node_modules/electron/cli.js"

export NODE_ENV="development"
export CONDA_DEFAULT_ENV="$ENV_NAME"
export PYTHONUTF8="1"
if [[ -n "$conda_prefix" ]]; then
  export CONDA_PREFIX="$conda_prefix"
  export PATH="$conda_prefix/bin:$PATH"
fi

printf '[INFO] Starting Vite and Electron in a single terminal...\n'
(
  cd "$FRONTEND_DIR"
  "$node_path" "$vite_script"
) &
vite_pid="$!"

if ! wait_for_vite_server; then
  printf '[ERROR] Vite server startup timed out\n' >&2
  exit 1
fi

(
  cd "$FRONTEND_DIR"
  "$node_path" "$electron_cli" .
) &
electron_pid="$!"

if [[ "$AUTO_STOP_AFTER_SECONDS" =~ ^[0-9]+$ ]] && [[ "$AUTO_STOP_AFTER_SECONDS" -gt 0 ]]; then
  (
    sleep "$AUTO_STOP_AFTER_SECONDS"
    printf '\n[INFO] Auto stop triggered after %s seconds\n' "$AUTO_STOP_AFTER_SECONDS"
    kill -TERM "$$"
  ) &
  timer_pid="$!"
fi

set +e
wait "$electron_pid"
electron_exit_code=$?
set -e

if [[ "$electron_exit_code" -ne 0 && -z "$stop_reason" ]]; then
  exit "$electron_exit_code"
fi

if [[ "$stop_reason" == "sigint" ]]; then
  printf '\n[INFO] Ctrl+C received, shutting down...\n'
fi
