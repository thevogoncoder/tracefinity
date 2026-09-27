#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Backend: same venv layout as the README so `make dev` and `make lint` work unchanged.
python3 -m venv backend/venv
backend/venv/bin/pip install --upgrade pip
# CPU-only torch first, otherwise pip pulls the multi-GB CUDA build.
backend/venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
backend/venv/bin/pip install -r backend/requirements.txt ruff

# Frontend: pnpm version comes from package.json's packageManager field.
corepack enable
(cd frontend && corepack install && pnpm install --frozen-lockfile)
