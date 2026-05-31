#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bin/kill-review-preview.sh [--dry-run] PID [PID ...]

Stops only Reviewable HTML Workbench preview server processes:
  python -m scripts.html_review_workbench.preview_server --serve ...

Each PID is verified before it is stopped. PID is required so a different
session's preview server is not stopped accidentally.
USAGE
}

dry_run=0
pids=()
ps_bin="${REVIEW_PREVIEW_PS:-ps}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      pids+=("$1")
      shift
      ;;
  esac
done

is_numeric_pid() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

is_review_preview_command() {
  local command="$1"
  [[ "$command" == *"-m scripts.html_review_workbench.preview_server"* && "$command" == *"--serve"* ]]
}

command_for_pid() {
  "$ps_bin" -p "$1" -o command= 2>/dev/null || true
}

if [[ ${#pids[@]} -eq 0 ]]; then
  echo "Refusing to stop all review preview processes. Pass an explicit PID." >&2
  exit 2
fi

for pid in "${pids[@]}"; do
  if ! is_numeric_pid "$pid"; then
    echo "Refusing non-numeric PID: $pid" >&2
    exit 2
  fi

  command="$(command_for_pid "$pid")"
  if [[ -z "$command" ]]; then
    echo "PID not found: $pid" >&2
    exit 2
  fi
  if ! is_review_preview_command "$command"; then
    echo "Refusing to stop non-review preview process: $pid" >&2
    echo "$command" >&2
    exit 2
  fi

  if [[ "$dry_run" -eq 1 ]]; then
    echo "Would stop review preview process: $pid"
  else
    kill "$pid"
    echo "Stopped review preview process: $pid"
  fi
done
