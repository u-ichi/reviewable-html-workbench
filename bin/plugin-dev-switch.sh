#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: bin/plugin-dev-switch.sh dev|package|status

Commands:
  dev      Replace plugin cache copies with symlinks to this repository.
  package  Restore original plugin cache copies from .bak directories.
  status   Show whether plugin caches currently point at dev or package.
USAGE
}

die() {
  echo "error: $*" >&2
  exit 1
}

find_claude_cache_entry() {
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
    return 1
  fi
  if [[ ! -e "$entry" && ! -L "$entry" ]]; then
    die "installPath が存在しません: $entry"
  fi
  printf '%s\n' "$entry"
}

find_codex_cache_entry() {
  local base entry_count repo_version version_entry symlink_entry
  base="$(codex_cache_base)"
  [ -d "$base" ] || return 1
  repo_version="$(codex_repo_version)"

  if [[ -n "$repo_version" && ( -e "$base/$repo_version" || -L "$base/$repo_version" ) ]]; then
    printf '%s\n' "$base/$repo_version"
    return 0
  fi

  symlink_entry="$(find "$base" -mindepth 1 -maxdepth 1 -type l ! -name '*.bak' -print | sort -V | while IFS= read -r candidate; do
    if [ "$(readlink "$candidate")" = "$REPO_ROOT" ]; then
      printf '%s\n' "$candidate"
      break
    fi
  done)"
  if [[ -n "$symlink_entry" ]]; then
    printf '%s\n' "$symlink_entry"
    return 0
  fi

  entry_count="$(find "$base" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) ! -name '*.bak' | wc -l | tr -d ' ')"
  if [[ "$entry_count" = "1" ]]; then
    find "$base" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) ! -name '*.bak' -print
    return 0
  fi

  version_entry="$(find "$base" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) -name '[0-9]*' ! -name '*.bak' | sort -V | tail -n 1)"
  if [[ -n "$version_entry" ]]; then
    printf '%s\n' "$version_entry"
    return 0
  fi
  return 1
}

codex_cache_base() {
  printf '%s\n' "$HOME/.codex/plugins/cache/reviewable-html-workbench-local/reviewable-html-workbench"
}

codex_repo_version() {
  python3 -c "
import json
from pathlib import Path
p = Path('$REPO_ROOT') / '.codex-plugin/plugin.json'
try:
    print(json.loads(p.read_text()).get('version', ''), end='')
except Exception:
    print('', end='')
" 2>/dev/null
}

codex_desired_entry() {
  local version
  version="$(codex_repo_version)"
  [ -n "$version" ] || die "Codex plugin manifest version を読めません"
  printf '%s\n' "$(codex_cache_base)/$version"
}

ensure_codex_plugin_installed() {
  if [ "${RHW_PLUGIN_DEV_SWITCH_SKIP_CODEX_ADD:-}" = "1" ]; then
    return 0
  fi
  command -v codex >/dev/null 2>&1 || die "codex command が見つかりません"
  codex plugin add reviewable-html-workbench@reviewable-html-workbench-local --json >/dev/null \
    || die "codex plugin add に失敗しました"
}

codex_dev_link_names() {
  printf '%s\n' \
    .agents \
    .claude-plugin \
    .codex-plugin \
    agents \
    bin \
    docs \
    schemas \
    scripts \
    skills \
    templates \
    LICENSE \
    README.md \
    pyproject.toml
}

is_codex_dev_dir() {
  local entry marker
  entry="$1"
  marker="$entry/.rhw-plugin-dev-mode"
  [ -f "$marker" ] || return 1
  [ "$(cat "$marker")" = "$REPO_ROOT" ]
}

create_codex_dev_dir() {
  local entry name source
  entry="$1"
  mkdir -p "$entry" || die "codex dev cache directory を作成できません: $entry"
  while IFS= read -r name; do
    source="$REPO_ROOT/$name"
    [ -e "$source" ] || continue
    ln -s "$source" "$entry/$name" || die "codex dev symlink を作成できません: $entry/$name"
  done < <(codex_dev_link_names)
  printf '%s\n' "$REPO_ROOT" >"$entry/.rhw-plugin-dev-mode" || die "codex dev marker を作成できません: $entry"
}

move_stale_codex_entries_to_backup() {
  local desired candidate backup target_path
  desired="$1"
  find "$(codex_cache_base)" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) ! -name "$(basename "$desired")" ! -name '.rhw-plugin-dev-switch-backups' -print | while IFS= read -r candidate; do
    if [ -L "$candidate" ]; then
      target_path="$(readlink "$candidate")"
      [ "$target_path" = "$REPO_ROOT" ] || die "stale codex symlink target is not this repo: $candidate -> $target_path"
      rm "$candidate" || die "stale codex dev symlink を削除できません: $candidate"
    elif [ -d "$candidate" ]; then
      backup="$(backup_entry_for_target codex "$candidate")"
      if [ -e "$backup" ]; then
        rm -rf "$candidate" || die "stale codex package cache を削除できません: $candidate"
      else
        mkdir -p "$(dirname "$backup")" || die "backup directory を作成できません: $(dirname "$backup")"
        mv "$candidate" "$backup" || die "stale codex package cache を退避できません: $candidate -> $backup"
      fi
    fi
  done
}

cache_entry_for_target() {
  case "$1" in
    claude)
      find_claude_cache_entry || return 1
      ;;
    codex)
      find_codex_cache_entry || return 1
      ;;
    *)
      die "unknown target: $1"
      ;;
  esac
}

backup_entry_for_target() {
  local target entry plugin_dir cache_dir version
  target="$1"
  entry="$2"
  plugin_dir="$(dirname "$entry")"
  cache_dir="$(dirname "$plugin_dir")"
  version="$(basename "$entry")"
  printf '%s\n' "$cache_dir/.rhw-plugin-dev-switch-backups/$target/$version"
}

migrate_legacy_backup() {
  local target entry legacy backup
  target="$1"
  entry="$2"
  legacy="$entry.bak"
  backup="$(backup_entry_for_target "$target" "$entry")"
  if [ -e "$legacy" ]; then
    [ ! -e "$backup" ] || die "backup already exists: $backup"
    mkdir -p "$(dirname "$backup")" || die "backup directory を作成できません: $(dirname "$backup")"
    mv "$legacy" "$backup" || die "legacy backup を移動できません: $legacy -> $backup"
  fi
}

show_status_one() {
  local target entry target_path desired
  target="$1"
  entry="$(cache_entry_for_target "$target")" || {
    echo "$target: not installed"
    return 0
  }
  migrate_legacy_backup "$target" "$entry"

  if [ -L "$entry" ]; then
    target_path="$(readlink "$entry")"
    if [ "$target" = "codex" ]; then
      desired="$(codex_desired_entry)"
      echo "$target: stale dev (version symlink -> $target_path, entry -> $entry, expected directory -> $desired)"
      return 0
    fi
    echo "$target: dev (symlink -> $target_path)"
  elif [ -d "$entry" ]; then
    if [ "$target" = "codex" ] && is_codex_dev_dir "$entry"; then
      echo "$target: dev (directory with repo symlinks -> $entry)"
      return 0
    fi
    echo "$target: package (cache copy -> $entry)"
  else
    die "cache entry is neither directory nor symlink: $entry"
  fi
}

switch_to_dev_one() {
  local target entry backup target_path desired old_backup
  target="$1"
  if [ "$target" = "codex" ]; then
    ensure_codex_plugin_installed
    entry="$(codex_desired_entry)"
    backup="$(backup_entry_for_target "$target" "$entry")"
    move_stale_codex_entries_to_backup "$entry"

    if [ -L "$entry" ]; then
      target_path="$(readlink "$entry")"
      [ "$target_path" = "$REPO_ROOT" ] || die "codex cache entry is a symlink to a different target: $target_path"
      rm "$entry" || die "codex version symlink を削除できません: $entry"
    elif [ -d "$entry" ]; then
      if is_codex_dev_dir "$entry"; then
        echo "$target: already dev (directory with repo symlinks -> $entry)"
        return 0
      fi
      if [ -e "$backup" ]; then
        rm -rf "$entry" || die "codex package cache を削除できません: $entry"
      else
        mkdir -p "$(dirname "$backup")" || die "backup directory を作成できません: $(dirname "$backup")"
        mv "$entry" "$backup" || die "codex package cache を退避できません: $entry -> $backup"
      fi
    fi

    create_codex_dev_dir "$entry"
    echo "$target: switched to dev (directory with repo symlinks -> $entry)"
    return 0
  fi
  entry="$(cache_entry_for_target "$target")" || die "$target plugin がインストールされていません"
  migrate_legacy_backup "$target" "$entry"

  backup="$(backup_entry_for_target "$target" "$entry")"

  if [ -L "$entry" ]; then
    target_path="$(readlink "$entry")"
    if [ "$target_path" = "$REPO_ROOT" ]; then
      echo "$target: already dev (symlink -> $target_path)"
      return 0
    fi
    die "$target cache entry is already a symlink to a different target: $target_path"
  fi

  if [ -e "$entry" ]; then
    [ -d "$entry" ] || die "cache entry is not a directory: $entry"
    [ ! -e "$backup" ] || die "backup already exists: $backup"
    mkdir -p "$(dirname "$backup")" || die "backup directory を作成できません: $(dirname "$backup")"
    mv "$entry" "$backup" || die "cache entry を退避できません: $entry -> $backup"
  fi

  mkdir -p "$(dirname "$entry")" || die "cache directory を作成できません: $(dirname "$entry")"
  ln -s "$REPO_ROOT" "$entry" || die "dev symlink を作成できません: $entry"
  echo "$target: switched to dev (symlink -> $REPO_ROOT)"
}

switch_to_package_one() {
  local target entry backup backup_root restored=0 desired
  target="$1"

  if [ "$target" = "codex" ]; then
    desired="$(codex_desired_entry)"
    backup="$(backup_entry_for_target "$target" "$desired")"
    backup_root="$(dirname "$backup")"
    if [ -d "$(codex_cache_base)" ]; then
      move_stale_codex_entries_to_backup "$desired"
    fi
    if [ -d "$(codex_cache_base)" ]; then
      find "$(codex_cache_base)" -mindepth 1 -maxdepth 1 -type l -print | while IFS= read -r candidate; do
        if [ "$(readlink "$candidate")" = "$REPO_ROOT" ]; then
          rm "$candidate" || die "codex dev symlink を削除できません: $candidate"
        fi
      done
    fi
    if [ -L "$desired" ]; then
      if [ "$(readlink "$desired")" = "$REPO_ROOT" ]; then
        rm "$desired" || die "codex dev symlink を削除できません: $desired"
      else
        die "codex cache entry is a symlink to a different target: $(readlink "$desired")"
      fi
    elif [ -d "$desired" ]; then
      if is_codex_dev_dir "$desired"; then
        rm -rf "$desired" || die "codex dev cache directory を削除できません: $desired"
      else
        echo "$target: already package (cache copy)"
        return 0
      fi
    fi
    if [ -d "$backup" ]; then
      [ ! -e "$desired" ] && [ ! -L "$desired" ] || die "restore target already exists: $desired"
      mv "$backup" "$desired" || die "codex package cache を復元できません: $backup -> $desired"
      restored=1
    fi
    if [ "$restored" = "1" ]; then
      echo "$target: switched to package (cache copy)"
    elif [ ! -e "$desired" ] && [ ! -L "$desired" ]; then
      ensure_codex_plugin_installed
      echo "$target: switched to package (cache copy)"
    else
      echo "$target: already package (cache copy)"
    fi
    return 0
  fi

  entry="$(cache_entry_for_target "$target")" || die "$target plugin がインストールされていません"
  migrate_legacy_backup "$target" "$entry"

  backup="$(backup_entry_for_target "$target" "$entry")"

  if [ -d "$entry" ] && [ ! -L "$entry" ]; then
    echo "$target: already package (cache copy)"
    return 0
  fi

  [ -L "$entry" ] || die "cache entry is not a symlink: $entry"
  [ -d "$backup" ] || die "backup not found: $backup"

  rm "$entry"
  mv "$backup" "$entry"
  echo "$target: switched to package (cache copy)"
}

run_for_targets() {
  local command target status=0 targets=()
  command="$1"
  shift
  targets=("$@")

  for target in "${targets[@]}"; do
    case "$command" in
      status)
        show_status_one "$target" || status=1
        ;;
      dev)
        switch_to_dev_one "$target" || status=1
        ;;
      package)
        switch_to_package_one "$target" || status=1
        ;;
    esac
  done
  return "$status"
}

main() {
  local command
  command="${1:-}"

  case "$command" in
    dev|package|status)
      run_for_targets "$command" claude codex
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
