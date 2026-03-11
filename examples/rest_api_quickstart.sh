#!/usr/bin/env bash
set -euo pipefail

# Minimal REST API quickstart for AKF.
export AKF_ENV="dev"

# Start in a separate terminal:
# akf serve --host 127.0.0.1 --port 8000

curl -sS -X POST http://127.0.0.1:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a guide on API rate limiting"}'
