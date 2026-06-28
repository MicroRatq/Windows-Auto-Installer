#!/usr/bin/env bash

set -Eeuo pipefail

ENV_NAME="win-auto-installer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/src/frontend"

print_header() {
  printf '================================\n'
  printf 'Windows Auto Installer - Environment Setup\n'
  printf '================================\n\n'
}

print_header

printf '[1/5] Checking Node.js...\n'
if ! command -v node >/dev/null 2>&1; then
  printf '[ERROR] Node.js was not found. Please install Node.js 20 LTS or newer first.\n'
  printf 'Download: https://nodejs.org/\n'
  exit 1
fi
printf '[OK] Node.js is installed: %s\n\n' "$(node --version)"

printf '[2/5] Checking Conda...\n'
if ! command -v conda >/dev/null 2>&1; then
  printf '[ERROR] Conda was not found. Please install Anaconda or Miniconda first.\n'
  printf 'Download: https://www.anaconda.com/download\n'
  printf '          https://docs.conda.io/en/latest/miniconda.html\n'
  exit 1
fi
printf '[OK] Conda is installed: %s\n\n' "$(conda --version)"

if [[ ! -f "$REPO_ROOT/environment.yml" ]]; then
  printf '[ERROR] environment.yml was not found in the repository root.\n'
  exit 1
fi

printf '[3/5] Creating Conda environment...\n'
env_exists=false
while IFS= read -r line; do
  case "$line" in
    "$ENV_NAME "*|"$ENV_NAME"$'\t'*)
      env_exists=true
      break
      ;;
  esac
done < <(conda env list)

if [[ "$env_exists" == true ]]; then
  read -r -p "[INFO] Environment $ENV_NAME already exists. Recreate it? [y/N] " recreate
  if [[ "$recreate" =~ ^[Yy]$ ]]; then
    printf '[INFO] Removing existing environment...\n'
    conda env remove -n "$ENV_NAME" -y
    printf '[INFO] Creating new environment...\n'
    conda env create -f "$REPO_ROOT/environment.yml"
  else
    printf '[INFO] Updating existing environment...\n'
    conda env update -n "$ENV_NAME" -f "$REPO_ROOT/environment.yml" --prune
  fi
else
  printf '[INFO] Creating new environment...\n'
  conda env create -f "$REPO_ROOT/environment.yml"
fi
printf '[OK] Conda environment is ready\n\n'

printf '[4/5] Activating Conda environment and validating...\n'
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

if ! command -v python >/dev/null 2>&1; then
  printf '[ERROR] Python is not available after activating the Conda environment.\n'
  exit 1
fi
printf '[OK] Python version: %s\n' "$(python --version 2>&1)"

printf '[INFO] Validating key Python packages...\n'
if ! python -c "import pycdlib; print('pycdlib: OK')" 2>/dev/null; then
  printf '[WARN] pycdlib is not installed correctly\n'
fi
if ! python -c "import requests; print('requests: OK')" 2>/dev/null; then
  printf '[WARN] requests is not installed correctly\n'
fi
if ! python -c "import libtorrent; print('libtorrent: OK')" 2>/dev/null; then
  printf '[WARN] libtorrent is not installed correctly\n'
fi
printf '\n'

printf '[5/5] Installing Node.js dependencies...\n'
if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  printf '[INFO] src/frontend/package.json does not exist yet, skipping npm install.\n'
else
  npm install --prefix "$FRONTEND_DIR"
  printf '[OK] Node.js dependencies installed\n'
fi
printf '\n'

printf '================================\n'
printf 'Environment setup completed\n'
printf '================================\n\n'
printf 'Next steps:\n'
printf '1. Run ./scripts/run_dev.sh for local development\n'
printf '2. Continue project initialization if needed\n'
