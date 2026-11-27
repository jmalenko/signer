#!/bin/sh
# Run Signer via the project virtual environment (macOS/Linux).
# Usage: ./signer.sh [-document <file>] [-signature <file>]
cd "$(dirname "$0")"
"./.venv/bin/python" main.py "$@"
