#!/bin/bash
set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

if [[ "$TOOL_NAME" != "EnterPlanMode" ]] || [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

if [[ "$SESSION_ID" == *"/"* ]] || [[ "$SESSION_ID" == "." ]] || [[ "$SESSION_ID" == ".." ]]; then
  exit 0
fi

SENTINEL="${TMPDIR:-/tmp}/claude-plan-preview/$SESSION_ID" # lint:allow-os-tmp
rm -f "$SENTINEL" 2>/dev/null || true
exit 0
