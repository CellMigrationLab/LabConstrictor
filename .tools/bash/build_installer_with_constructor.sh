#!/usr/bin/env bash
# Build the platform-specific installer using the prepared constructor env.
set -euo pipefail

mkdir -p "${OUTPUT_DIR:?}"
conda run -n "${CONSTRUCTOR_ENV:?}" constructor . --output-dir "${OUTPUT_DIR}"
