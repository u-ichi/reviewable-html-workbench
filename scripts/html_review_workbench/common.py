"""Shared low-level helpers for Reviewable HTML Workbench modules."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMENTS_SCHEMA_PATH = REPO_ROOT / "schemas" / "comments.schema.json"
MERMAID_INIT_JS = "mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def write_json(path: Path, payload: dict[str, Any], *, ensure_parent: bool = False, indent: int | None = 2) -> None:
    if ensure_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def unique_path(path: Path, *, on_exhausted: Callable[[Path], Exception]) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise on_exhausted(path)


def resolve_bundle_json_path(
    root: Path,
    relative_path: str,
    *,
    label: str,
    error: Callable[[str], Exception],
) -> Path:
    if not relative_path:
        raise error(f"{label} path is required")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise error(f"{label} path must be relative")
    if any(part == ".." for part in candidate.parts):
        raise error(f"{label} path must not contain parent traversal")

    resolved_root = root.resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise error(f"{label} path must stay inside the bundle root")
    if resolved_path.suffix != ".json":
        raise error(f"{label} path must be a JSON file")
    return resolved_path
