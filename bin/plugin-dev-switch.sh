#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: bin/plugin-dev-switch.sh dev|package|status

Commands:
  dev      Replace the plugin cache copy with a symlink to this repository.
  package  Restore the original plugin cache copy from the .bak directory.
  status   Show whether the cache currently points at dev or package.
USAGE
}

die() {
  echo "error: $*" >&2
  exit 1
}

find_cache_entry() {
  local entry
  entry="$(python3 -c "
import json, sys
from pathlib import Path
p = Path.home() / '.claude/plugins/installed_plugins.json'
if not p.exists():
    print('', end='')
    sys.exit(0)
data = json.loads(p.read_text())
entries = data.get('plugins', {}).get('reviewable-html-workbench@reviewable-html-workbench-local', [])
if entries:
    print(entries[0].get('installPath', ''), end='')
" 2>/dev/null)" || true
  if [[ -z "$entry" ]]; then
    die "plugin がインストールされていません。先に claude plugin install reviewable-html-workbench を実行してください"
  fi
  if [[ ! -e "$entry" && ! -L "$entry" ]]; then
    die "installPath が存在しません: $entry"
  fi
  printf '%s\n' "$entry"
}

show_status() {
  local entry target
  entry="$(find_cache_entry)"

  if [ -L "$entry" ]; then
    target="$(readlink "$entry")"
    echo "dev (symlink -> $target)"
  elif [ -d "$entry" ]; then
    echo "package (cache copy)"
  else
    die "cache entry is neither directory nor symlink: $entry"
  fi
}

switch_to_dev() {
  local entry backup target
  entry="$(find_cache_entry)"
  backup="$entry.bak"

  if [ -L "$entry" ]; then
    target="$(readlink "$entry")"
    if [ "$target" = "$REPO_ROOT" ]; then
      echo "already dev (symlink -> $target)"
      return 0
    fi
    die "cache entry is already a symlink to a different target: $target"
  fi

  [ -d "$entry" ] || die "cache entry is not a directory: $entry"
  [ ! -e "$backup" ] || die "backup already exists: $backup"

  mv "$entry" "$backup"
  ln -s "$REPO_ROOT" "$entry"
  echo "switched to dev (symlink -> $REPO_ROOT)"
}

switch_to_package() {
  local entry backup
  entry="$(find_cache_entry)"
  backup="$entry.bak"

  if [ -d "$entry" ] && [ ! -L "$entry" ]; then
    echo "already package (cache copy)"
    return 0
  fi

  [ -L "$entry" ] || die "cache entry is not a symlink: $entry"
  [ -d "$backup" ] || die "backup not found: $backup"

  rm "$entry"
  mv "$backup" "$entry"
  echo "switched to package (cache copy)"
}

main() {
  local command="${1:-}"

  case "$command" in
    dev)
      switch_to_dev
      ;;
    package)
      switch_to_package
      ;;
    status)
      show_status
      ;;
    -h|--help|"")
      usage
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
