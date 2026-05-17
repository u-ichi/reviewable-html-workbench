"""Read and write review comments inside a generated HTML bundle."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.schema_validation import validate


ROOT = Path(__file__).resolve().parents[2]
COMMENTS_SCHEMA_PATH = ROOT / "schemas" / "comments.schema.json"
DEFAULT_COMMENTS_PATH = "annotations/comments.json"
DEFAULT_STATUS = "needs_agent_review"


class CommentStoreError(ValueError):
    """Raised when comment data or storage configuration is invalid."""


@dataclass(frozen=True)
class CommentStore:
    root: Path
    comments_path: str = DEFAULT_COMMENTS_PATH

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())
        object.__setattr__(self, "path", resolve_comments_path(self.root, self.comments_path))

    def read(self, document_id: str) -> dict[str, Any]:
        if not self.path.is_file():
            return empty_comments(document_id)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommentStoreError(f"comments file is invalid JSON: {self.path}") from exc
        validate_comments_payload(payload)
        return payload

    def write(self, payload: dict[str, Any]) -> Path:
        validate_comments_payload(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self.path

    def add_thread(
        self,
        *,
        document_id: str,
        block_id: str,
        selected_text: str,
        comment: str,
        prefix: str = "",
        suffix: str = "",
        status: str = DEFAULT_STATUS,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        payload = self.read(document_id)
        thread = make_thread(
            document_id=document_id,
            block_id=block_id,
            selected_text=selected_text,
            comment=comment,
            prefix=prefix,
            suffix=suffix,
            status=status,
            created_at=created_at,
        )
        payload["comments"].append(thread)
        self.write(payload)
        return thread

    def add_reply(
        self,
        *,
        document_id: str,
        thread_id: str,
        author: str,
        role: str,
        kind: str,
        body: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        payload = self.read(document_id)
        thread = _find_thread(payload, thread_id)
        reply = make_reply(author=author, role=role, kind=kind, body=body, created_at=created_at)
        thread["replies"].append(reply)
        thread["status"] = _status_after_reply(role)
        self.write(payload)
        return reply

    def update_status(self, *, document_id: str, thread_id: str, status: str) -> dict[str, Any]:
        payload = self.read(document_id)
        thread = _find_thread(payload, thread_id)
        thread["status"] = status
        self.write(payload)
        return thread


def empty_comments(document_id: str) -> dict[str, Any]:
    if not document_id:
        raise CommentStoreError("document_id is required")
    return {
        "schema_version": "1.0",
        "document_id": document_id,
        "comments": [],
    }


def make_thread(
    *,
    document_id: str,
    block_id: str,
    selected_text: str,
    comment: str,
    prefix: str = "",
    suffix: str = "",
    status: str = DEFAULT_STATUS,
    created_at: str | None = None,
) -> dict[str, Any]:
    payload = {
        "id": f"cmt_{_new_id()}",
        "document_id": document_id,
        "block_id": block_id,
        "selected_text": selected_text,
        "prefix": prefix,
        "suffix": suffix,
        "comment": comment,
        "status": status,
        "created_at": created_at or _now_iso(),
        "replies": [],
    }
    validate_comments_payload({"schema_version": "1.0", "document_id": document_id, "comments": [payload]})
    return payload


def make_reply(*, author: str, role: str, kind: str, body: str, created_at: str | None = None) -> dict[str, Any]:
    payload = {
        "id": f"reply_{_new_id()}",
        "author": author,
        "role": role,
        "kind": kind,
        "body": body,
        "created_at": created_at or _now_iso(),
    }
    schema = _comments_schema()["properties"]["comments"]["items"]["properties"]["replies"]["items"]
    errors = validate(payload, schema)
    if errors:
        raise CommentStoreError("; ".join(f"{error.path}: {error.message}" for error in errors))
    return payload


def validate_comments_payload(payload: dict[str, Any]) -> None:
    errors = validate(payload, _comments_schema())
    if errors:
        raise CommentStoreError("; ".join(f"{error.path}: {error.message}" for error in errors))


def resolve_comments_path(root: Path, comments_path: str = DEFAULT_COMMENTS_PATH) -> Path:
    if not comments_path:
        raise CommentStoreError("comments path is required")
    candidate = Path(comments_path)
    if candidate.is_absolute():
        raise CommentStoreError("comments path must be relative")
    if any(part == ".." for part in candidate.parts):
        raise CommentStoreError("comments path must not contain parent traversal")

    resolved_root = root.resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise CommentStoreError("comments path must stay inside the bundle root")
    if resolved_path.suffix != ".json":
        raise CommentStoreError("comments path must be a JSON file")
    return resolved_path


def _comments_schema() -> dict[str, Any]:
    return json.loads(COMMENTS_SCHEMA_PATH.read_text(encoding="utf-8"))


def _find_thread(payload: dict[str, Any], thread_id: str) -> dict[str, Any]:
    for thread in payload.get("comments", []):
        if isinstance(thread, dict) and thread.get("id") == thread_id:
            return thread
    raise CommentStoreError(f"comment thread not found: {thread_id}")


def _status_after_reply(role: str) -> str:
    if role == "agent":
        return "needs_user_reply"
    if role == "user":
        return "needs_agent_review"
    return DEFAULT_STATUS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]
