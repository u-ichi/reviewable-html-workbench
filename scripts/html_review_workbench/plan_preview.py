"""Ephemeral plan preview support for Plan Mode helper views."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from html import escape
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.common import now_iso, pid_is_alive, write_json
from scripts.html_review_workbench.preview_server import PreviewConfigurationError, PreviewMode, start_preview
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.validate_bundle import validate_bundle


MAX_PAYLOAD_BYTES = 512 * 1024
MARKER_FILE = ".rhw-plan-preview"
ROOT_PREFIX = "rhw-plan-preview-"
PLAN_PREVIEW_SENTINEL_DIR_NAME = "claude-plan-preview"
DEFAULT_TTL_SECONDS = 1800.0
_CLEANUP_WATCHERS: list[subprocess.Popen[bytes]] = []


class PlanPreviewError(ValueError):
    """Raised when a plan preview cannot be created or cleaned up."""


@dataclass(frozen=True)
class PlanPreviewResult:
    id: str
    url: str
    root: Path
    pid: int
    ttl: float
    expires_at: str
    stop_command: str
    process: subprocess.Popen[bytes] | None = None
    cleanup_process: subprocess.Popen[bytes] | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "status": "running",
            "ephemeral": True,
            "id": self.id,
            "url": self.url,
            "root": str(self.root),
            "pid": self.pid,
            "ttl": self.ttl,
            "expires_at": self.expires_at,
            "stop_command": self.stop_command,
        }


def read_payload(source: str | None) -> dict[str, Any]:
    if source in (None, "-"):
        raw = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
    else:
        path = Path(source)
        raw = path.read_bytes()
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise PlanPreviewError("plan preview payload exceeds 512 KiB")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanPreviewError(f"plan preview payload is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanPreviewError("plan preview payload must be a JSON object")
    _reject_remote_assets(payload)
    return payload


def create_plan_preview(
    payload: dict[str, Any],
    ttl: float = DEFAULT_TTL_SECONDS,
    mode: PreviewMode = "auto",
    preview_starter: Any = start_preview,
    cleanup_starter: Any = None,
    bundle_validator: Any = validate_bundle,
) -> PlanPreviewResult:
    if ttl <= 0:
        raise PlanPreviewError("ttl must be positive")
    if cleanup_starter is None:
        cleanup_starter = _start_cleanup_watcher
    preview_id = uuid.uuid4().hex[:12]
    root = Path(tempfile.mkdtemp(prefix=ROOT_PREFIX)).resolve()
    _assert_plan_preview_root(root)
    write_json(root / MARKER_FILE, {"id": preview_id, "created_at": now_iso()}, indent=None)

    model = build_plan_preview_model(payload, preview_id)
    model_path = root / "document-model.json"
    try:
        write_json(model_path, model)
        render_bundle(model_path, root)
        _validate_rendered_bundle(root, bundle_validator)
    except (OSError, ValueError, PlanPreviewError):
        shutil.rmtree(root, ignore_errors=True)
        raise
    session = preview_starter(root, mode, idle_timeout=ttl)
    expires_at = (now_iso_datetime() + timedelta(seconds=ttl)).isoformat()
    cleanup_process = cleanup_starter(root, session.pid, ttl)
    _write_plan_preview_sentinel(preview_id)
    return PlanPreviewResult(
        id=preview_id,
        url=session.url,
        root=root,
        pid=session.pid,
        ttl=ttl,
        expires_at=expires_at,
        stop_command=(
            "python3 -m scripts.html_review_workbench.cli plan-preview-stop "
            f"--root {root} --pid {session.pid}"
        ),
        process=session.process,
        cleanup_process=cleanup_process,
    )


def build_plan_preview_model(payload: dict[str, Any], preview_id: str) -> dict[str, Any]:
    title = _string(payload.get("title"), "Plan Preview")
    summary = _string(payload.get("summary"), "Graphical preview of the proposed plan.")
    blocks: list[dict[str, Any]] = [
        {
            "id": "plan-summary",
            "type": "html",
            "heading_level": 2,
            "title": "Summary",
            "content": _paragraph(summary),
            "review_required": True,
        }
    ]

    source_text = _first_string(payload, ("source_text", "proposed_plan", "plan_text", "full_text"))
    if source_text:
        blocks.append(
            {
                "id": "original-plan-text",
                "type": "code",
                "heading_level": 2,
                "title": "Original Plan Text",
                "content": source_text,
                "language": "text",
                "filename": "proposed_plan.txt",
                "review_required": True,
            }
        )

    phase_items = _items(payload.get("phases"))
    if phase_items:
        blocks.append(_list_block("plan-phases", "Plan Phases", phase_items))

    key_changes = _items(payload.get("key_changes"))
    if key_changes:
        blocks.append(_list_block("key-changes", "Key Changes", key_changes))

    blocks.extend(_section_blocks(payload.get("sections")))

    flow = _flow(payload.get("flow"))
    if flow:
        blocks.append(
            {
                "id": "plan-flow",
                "type": "diagram",
                "heading_level": 2,
                "title": "Plan Flow",
                "content": _flow_to_mermaid(flow),
                "review_required": True,
            }
        )

    tests = _items(payload.get("test_plan") or payload.get("tests"))
    if tests:
        blocks.append(_list_block("test-plan", "Test Plan", tests))

    assumptions = _items(payload.get("assumptions"))
    if assumptions:
        blocks.append(_list_block("assumptions", "Assumptions", assumptions))

    supplemental = _items(
        payload.get("visual_notes") or payload.get("review_points") or payload.get("expanded_context")
    )
    if supplemental:
        blocks.append(_list_block("supplemental-context", "Supplemental Context", supplemental))

    return {
        "schema_version": "1.0",
        "document_id": f"plan-preview-{preview_id}",
        "title": title,
        "generated_at": now_iso(),
        "summary": summary,
        "metadata": {
            "status": "draft",
            "status_label": "Plan preview",
            "eyebrow": "RHW Plan Preview",
            "lang": "ja",
        },
        "blocks": blocks,
    }


def _validate_rendered_bundle(root: Path, bundle_validator: Any) -> None:
    result = bundle_validator(root)
    if result.ok:
        return
    details = "; ".join(str(error) for error in result.errors) or "unknown error"
    raise PlanPreviewError(f"plan preview bundle validation failed: {details}")


def stop_plan_preview(
    root: Path,
    pid: int | None = None,
    process: subprocess.Popen[bytes] | None = None,
    cleanup_process: subprocess.Popen[bytes] | None = None,
) -> dict[str, object]:
    root = root.resolve()
    _assert_plan_preview_root(root)
    stopped = False
    if pid is not None and pid_is_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            stopped = True
        except PermissionError as exc:
            raise PlanPreviewError(f"cannot stop plan preview pid {pid}: {exc}") from exc
    if process is not None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.kill(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
    if cleanup_process is not None and cleanup_process.poll() is None:
        try:
            os.kill(cleanup_process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        cleanup_process.wait(timeout=5)
    _cleanup_root(root)
    return {"status": "stopped", "root": str(root), "pid": pid, "process_signalled": stopped}


def _list_block(block_id: str, title: str, items: list[str]) -> dict[str, Any]:
    content = "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"
    return {
        "id": block_id,
        "type": "html",
        "heading_level": 2,
        "title": title,
        "content": content,
        "review_required": True,
    }


def _paragraph(text: str) -> str:
    return f"<p>{escape(text)}</p>"


def _items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            items.append(item)
        elif isinstance(item, dict):
            title = _string(item.get("title") or item.get("step") or item.get("name"), "")
            detail = _string(item.get("detail") or item.get("description"), "")
            if title and detail:
                items.append(f"{title}: {detail}")
            elif title:
                items.append(title)
    return items


def _section_blocks(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    blocks: list[dict[str, Any]] = []
    for index, section in enumerate(value, 1):
        if not isinstance(section, dict):
            continue
        title = _string(section.get("title"), f"Section {index}")
        content = _first_string(section, ("content", "body", "detail", "description", "summary"))
        items = _items(section.get("items"))
        html_parts: list[str] = []
        if content:
            html_parts.append(_paragraph(content))
        if items:
            html_parts.append("<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>")
        if not html_parts:
            continue
        blocks.append(
            {
                "id": f"plan-section-{index}",
                "type": "html",
                "heading_level": 2,
                "title": title,
                "content": "".join(html_parts),
                "review_required": True,
            }
        )
    return blocks


def _flow(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    flow: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = _string(item.get("from"), "")
        target = _string(item.get("to"), "")
        if not source or not target:
            continue
        flow.append({"from": source, "to": target, "label": _string(item.get("label"), "")})
    return flow


def _flow_to_mermaid(flow: list[dict[str, str]]) -> str:
    labels: dict[str, str] = {}
    lines = ["flowchart TD"]
    for edge in flow:
        for label in [edge["from"], edge["to"]]:
            labels.setdefault(label, f"n{len(labels) + 1}")
    for label, node_id in labels.items():
        lines.append(f'  {node_id}["{_mermaid_label(label)}"]')
    for edge in flow:
        source = labels[edge["from"]]
        target = labels[edge["to"]]
        label = edge.get("label") or ""
        if label:
            lines.append(f'  {source} -->|{_mermaid_label(label)}| {target}')
        else:
            lines.append(f"  {source} --> {target}")
    return "\n".join(lines)


def _string(value: object, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


def _first_string(values: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _mermaid_label(value: str) -> str:
    return value.replace('"', "'").replace("[", "(").replace("]", ")").replace("\n", " ")


def _reject_remote_assets(payload: dict[str, Any]) -> None:
    for key in ("assets", "images", "remote_assets", "remote_asset_urls"):
        if key in payload:
            raise PlanPreviewError(f"plan preview payload must not include {key}")


def _assert_plan_preview_root(root: Path) -> None:
    resolved = root.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if temp_root not in resolved.parents:
        raise PlanPreviewError("plan preview root must be under the system temp directory")
    if not resolved.name.startswith(ROOT_PREFIX):
        raise PlanPreviewError(f"plan preview root must start with {ROOT_PREFIX}")
    if not (resolved / MARKER_FILE).exists() and resolved.exists():
        # Creation path calls this before writing the marker.
        if any(resolved.iterdir()):
            raise PlanPreviewError("plan preview root is missing marker")


def _cleanup_root(root: Path) -> None:
    _assert_plan_preview_root(root)
    if not (root / MARKER_FILE).exists():
        raise PlanPreviewError("refusing to clean unmarked plan preview root")
    shutil.rmtree(root)


def _start_cleanup_watcher(root: Path, pid: int, ttl: float) -> subprocess.Popen[bytes]:
    code = (
        "import os, signal, shutil, sys, time\n"
        "pid=int(sys.argv[1]); root=sys.argv[2]; ttl=float(sys.argv[3])\n"
        "time.sleep(ttl)\n"
        "try:\n"
        "    os.kill(pid, signal.SIGTERM)\n"
        "except ProcessLookupError:\n"
        "    pass\n"
        "except PermissionError:\n"
        "    pass\n"
        "marker=os.path.join(root, '.rhw-plan-preview')\n"
        "if os.path.basename(root).startswith('rhw-plan-preview-') and os.path.exists(marker):\n"
        "    shutil.rmtree(root, ignore_errors=True)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(pid), str(root), str(ttl)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _CLEANUP_WATCHERS.append(process)
    return process


def _plan_preview_sentinel_path() -> Path | None:
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id or "/" in session_id or session_id in {".", ".."}:
        return None
    sentinel_dir = Path(tempfile.gettempdir()) / PLAN_PREVIEW_SENTINEL_DIR_NAME
    return sentinel_dir / session_id


def _write_plan_preview_sentinel(preview_id: str) -> None:
    sentinel = _plan_preview_sentinel_path()
    if sentinel is None:
        return
    write_json(
        sentinel,
        {"preview_id": preview_id, "created_at": now_iso()},
        ensure_parent=True,
        indent=None,
    )


def _remove_plan_preview_sentinel() -> None:
    """Remove the test-visible session sentinel if one was written."""
    sentinel = _plan_preview_sentinel_path()
    if sentinel is None:
        return
    sentinel.unlink(missing_ok=True)


def now_iso_datetime() -> "datetime":
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
