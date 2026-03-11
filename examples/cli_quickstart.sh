#!/usr/bin/env bash
set -euo pipefail

# Minimal CLI quickstart for AKF.
export GROQ_API_KEY="${GROQ_API_KEY:-gsk_replace_me}"

akf init
akf generate "Create a checklist for Python dependency security"
akf validate --path ./output
