#!/bin/bash
set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

if [[ "$TOOL_NAME" != "ExitPlanMode" ]] || [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

if [[ "$SESSION_ID" == *"/"* ]] || [[ "$SESSION_ID" == "." ]] || [[ "$SESSION_ID" == ".." ]]; then
  exit 0
fi

SENTINEL="${TMPDIR:-/tmp}/claude-plan-preview/$SESSION_ID" # lint:allow-os-tmp
if [[ -e "$SENTINEL" ]]; then
  exit 0
fi

LATEST_PLAN=""
shopt -s nullglob
for PLAN_FILE in "$HOME"/.claude/plans/*.md; do
  if [[ -z "$LATEST_PLAN" ]] || [[ "$PLAN_FILE" -nt "$LATEST_PLAN" ]]; then
    LATEST_PLAN="$PLAN_FILE"
  fi
done
shopt -u nullglob

if [[ -n "$LATEST_PLAN" ]] && grep -Eq 'Plan preview: (unavailable|http)' "$LATEST_PLAN"; then
  exit 0
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"ExitPlanMode requires a plan preview. Add `Plan preview: <url>` or `Plan preview: unavailable (<reason>)` to the plan before exiting Plan Mode."}}'
exit 0
