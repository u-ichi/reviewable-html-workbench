"""Resolution gate: block document edits while clarification threads are unresolved."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.comment_store import CommentStore
from scripts.html_review_workbench.ingest_review import DEFAULT_STATE_PATH, classify_thread


@dataclass(frozen=True)
class GateResult:
    gate: str
    blocking_threads: list[dict[str, str]]
    resolved_actionable: list[dict[str, str]]

    def to_payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {"gate": self.gate}
        if self.blocking_threads:
            result["blocking_threads"] = self.blocking_threads
        if self.resolved_actionable:
            result["resolved_actionable"] = self.resolved_actionable
        return result


def check_gate(
    root: Path,
    comments_path: str = "annotations/comments.json",
    state_path: str = DEFAULT_STATE_PATH,
) -> GateResult:
    """Check whether the resolution gate is open or blocked.

    The gate is **blocked** when any thread classified as ``needs_clarification``
    has a status other than ``resolved``.  When the gate is open, the result
    includes the list of resolved threads that were classified ``actionable``
    (candidates for document modification).
    """
    root = root.resolve()
    store = CommentStore(root, comments_path)
    payload = store.read("document")

    state = _load_state(root, state_path)

    blocking: list[dict[str, str]] = []
    resolved_actionable: list[dict[str, str]] = []

    for thread in payload.get("comments", []):
        thread_id = thread.get("id", "")
        status = thread.get("status", "")
        classification = _get_classification(thread, state)

        if classification == "needs_clarification" and status != "resolved":
            blocking.append({"thread_id": thread_id, "status": status})
        elif classification == "actionable" and status == "resolved":
            resolved_actionable.append({"thread_id": thread_id})

    gate = "blocked" if blocking else "open"
    return GateResult(
        gate=gate,
        blocking_threads=blocking,
        resolved_actionable=resolved_actionable,
    )


def try_check_gate(
    root: Path,
    comments_path: str = "annotations/comments.json",
    state_path: str = DEFAULT_STATE_PATH,
) -> GateResult | None:
    try:
        return check_gate(root, comments_path=comments_path, state_path=state_path)
    except Exception:
        return None


def _get_classification(thread: dict[str, Any], state: dict[str, Any] | None) -> str:
    """Return the classification for a thread, using state cache or live classify."""
    if state:
        for entry in state.get("classifications", []):
            if entry.get("comment_id") == thread.get("id"):
                return entry.get("classification", "")
    return classify_thread(thread).get("classification", "needs_clarification")


def _load_state(root: Path, state_path: str) -> dict[str, Any] | None:
    path = root / state_path
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
