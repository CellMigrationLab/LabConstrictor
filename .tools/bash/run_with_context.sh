#!/usr/bin/env bash
# Helper to run a command, capture its output, and build a context-rich log.
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: run_with_context.sh <log-path> <step-label> <script-path> <command...>" >&2
  exit 2
fi

LOG_PATH="$1"
shift
STEP_LABEL="$1"
shift
SCRIPT_PATH="$1"
shift

WORKFLOW_PATH="${WORKFLOW_PATH:-.github/workflows/update_on_notebook_change.yml}"
INSTRUCTIONS=$'You are explaining a GitHub Actions error to a non-programmer.\nUse this document to:\n1. Say in one or two sentences what went wrong and where.\n2. Describe the most likely cause in simple language.\n3. List clear next steps to fix or verify (no code unless essential).\n\nThis file contains: (a) the error log, (b) the workflow YAML, (c) the Python script.\n'

mkdir -p "$(dirname "$LOG_PATH")"
TMP_FILE="$(mktemp)"

set +e
"$@" 2>&1 | tee "$TMP_FILE"
STATUS=${PIPESTATUS[0]}
set -e

if [ "$STATUS" -ne 0 ]; then
  {
    printf '%s\n' "$INSTRUCTIONS"
    printf 'There has been an error while running %s, this is the error message:\n' "$STEP_LABEL"
    cat "$TMP_FILE"
    printf '\nThis is the GitHub action workflow:\n'
    cat "$WORKFLOW_PATH"
    printf '\nThis is the %s script:\n' "$STEP_LABEL"
    cat "$SCRIPT_PATH"
  } > "$LOG_PATH"
else
  mv "$TMP_FILE" "$LOG_PATH"
  printf '%s completed successfully.\n' "$STEP_LABEL" >> "$LOG_PATH"
fi

rm -f "$TMP_FILE"
exit "$STATUS"
