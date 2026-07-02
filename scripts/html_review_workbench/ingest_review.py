"""Ingest review comments and write review-cycle state."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.comment_store import (
    CommentStore,
    CommentStoreError,
    make_reply,
    validate_comments_payload,
)
from scripts.html_review_workbench.common import (
    now_iso,
    resolve_bundle_json_path as _resolve_bundle_json_path,
    write_json,
)


DEFAULT_STATE_PATH = "annotations/review-cycle-state.json"
DEFAULT_AGENT_AUTHOR = "codex"

INGESTION_CLASSIFICATIONS = (
    "actionable",
    "needs_clarification",
    "blocked",
    "already_addressed",
)
COMMENT_STATUS_VALUES = ("needs_agent_review", "needs_user_reply", "resolved")

_BLOCKED_KEYWORDS = ("blocked", "cannot", "can't", "unable", "missing source", "no access")
_CLARIFICATION_KEYWORDS = (
    "clarify",
    "which",
    "whether",
    "should",
    "what do you mean",
    "ambiguous",
    "どちら",
    "どれ",
    "未定",
)
_ACTION_KEYWORDS = (
    "replace",
    "rename",
    "fix",
    "typo",
    "add",
    "remove",
    "change",
    "update",
    "変更",
    "置き換え",
    "置換",
    "修正",
    "追加",
    "削除",
    "消して",
    "書いて",
    "まとめて",
    "表に",
    "具体的",
    "掲載禁止",
    "一切書かない",
    "関係無い",
    "関係ない",
)
_REPLACEMENT_PATTERNS = (
    re.compile(r"replace\s+['\"](?P<old>.+?)['\"]\s+with\s+['\"](?P<new>.+?)['\"]", re.IGNORECASE),
    re.compile(r"replace\s+selected\s+text\s+with\s+['\"](?P<new>.+?)['\"]", re.IGNORECASE),
)


class ReviewIngestionError(ValueError):
    """Raised when review ingestion cannot be completed."""


@dataclass(frozen=True)
class ReviewIngestionResult:
    payload: dict[str, Any]
    comments_path: Path
    state_path: Path
    model_path: Path | None = None


def ingest_review(
    root: Path,
    *,
    comments_path: str = "annotations/comments.json",
    state_path: str = DEFAULT_STATE_PATH,
    model_path: Path | None = None,
    apply_model: bool = False,
    agent_author: str = DEFAULT_AGENT_AUTHOR,
) -> ReviewIngestionResult:
    root = root.resolve()
    store = CommentStore(root, comments_path)
    payload = store.read("document")
    validate_comments_payload(payload)

    classifications: list[dict[str, Any]] = []
    replies_added = 0
    for thread in payload["comments"]:
        classified = classify_thread(thread)
        classified["reply_added"] = False
        classified["status_after"] = thread["status"]
        classifications.append(classified)

    model_update_result: dict[str, Any] = {"applied": 0, "skipped": []}
    resolved_model_path = None
    if model_path is not None:
        resolved_model_path = model_path.resolve()
        if apply_model:
            model_update_result = apply_limited_model_updates(resolved_model_path, classifications)
            applied_reply_count = add_implementation_replies(
                payload,
                model_update_result.get("applied_comment_ids", []),
                classifications,
                agent_author=agent_author,
            )
            replies_added += applied_reply_count
        else:
            model_update_result = {"applied": 0, "skipped": ["model updates require --apply-model"]}

    store.write(payload)

    state = build_review_cycle_state(
        document_id=str(payload["document_id"]),
        comments_path=comments_path,
        classifications=classifications,
        replies_added=replies_added,
        model_updates=model_update_result,
    )
    resolved_state_path = resolve_bundle_json_path(root, state_path)
    write_json(resolved_state_path, state, ensure_parent=True)

    from scripts.html_review_workbench.resolution_gate import try_check_gate

    gate_result = try_check_gate(root, comments_path=comments_path, state_path=state_path)
    if gate_result is not None:
        gate_payload = gate_result.to_payload()
    else:
        gate_payload = {"gate": "unknown"}

    return ReviewIngestionResult(
        payload={
            "status": "ok",
            "document_id": payload["document_id"],
            "comments_path": comments_path,
            "state_path": state_path,
            "summary": state["summary"],
            "model_updates": model_update_result,
            "gate": gate_payload,
        },
        comments_path=store.path,
        state_path=resolved_state_path,
        model_path=resolved_model_path,
    )


def classify_thread(thread: dict[str, Any]) -> dict[str, Any]:
    status = str(thread.get("status", ""))
    review_text = " ".join(
        str(thread.get(key, ""))
        for key in ("selected_text", "prefix", "suffix", "comment")
        if thread.get(key)
    )
    normalized = review_text.lower()
    classification = "needs_clarification"
    reason = "default_to_clarification"
    replacement = extract_replacement(thread)

    if status == "resolved" or _has_agent_implementation_reply(thread):
        classification = "already_addressed"
        reason = "thread_already_resolved_or_implemented"
    elif status == "needs_user_reply" and _has_agent_clarification(thread):
        classification = "already_addressed"
        reason = "thread_already_waiting_for_user_reply"
    elif _contains_any(normalized, _BLOCKED_KEYWORDS):
        classification = "blocked"
        reason = "blocked_keyword"
    elif replacement is not None or _contains_any(normalized, _ACTION_KEYWORDS):
        classification = "actionable"
        reason = "action_keyword_or_replacement"
    elif _contains_any(normalized, _CLARIFICATION_KEYWORDS):
        classification = "needs_clarification"
        reason = "clarification_keyword"

    result: dict[str, Any] = {
        "comment_id": thread["id"],
        "block_id": thread["block_id"],
        "classification": classification,
        "reason": reason,
        "status_before": status,
        "status_after": status,
    }
    if replacement is not None:
        result["replacement"] = replacement
    return result


def build_review_cycle_state(
    *,
    document_id: str,
    comments_path: str,
    classifications: list[dict[str, Any]],
    replies_added: int,
    model_updates: dict[str, Any],
) -> dict[str, Any]:
    counts = {value: 0 for value in INGESTION_CLASSIFICATIONS}
    for item in classifications:
        counts[item["classification"]] += 1
    return {
        "schema_version": "1.0",
        "document_id": document_id,
        "comments_path": comments_path,
        "generated_at": now_iso(),
        "summary": {
            "total": len(classifications),
            **counts,
            "replies_added": replies_added,
            "model_updates_applied": model_updates.get("applied", 0),
        },
        "classifications": classifications,
        "actionable_comment_ids": [
            item["comment_id"] for item in classifications if item["classification"] == "actionable"
        ],
        "blocked_comment_ids": [
            item["comment_id"] for item in classifications if item["classification"] == "blocked"
        ],
        "needs_clarification_comment_ids": [
            item["comment_id"] for item in classifications if item["classification"] == "needs_clarification"
        ],
        "model_updates": model_updates,
    }


def apply_limited_model_updates(model_path: Path, classifications: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewIngestionError(f"document model is invalid JSON: {model_path}") from exc
    if not isinstance(model, dict) or not isinstance(model.get("blocks"), list):
        raise ReviewIngestionError("document model must contain a blocks array")

    applied = 0
    applied_comment_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for item in classifications:
        if item["classification"] != "actionable":
            continue
        replacement = item.get("replacement")
        if not isinstance(replacement, dict):
            skipped.append({"comment_id": item["comment_id"], "reason": "no_limited_replacement"})
            continue
        block = _find_model_block(model["blocks"], item["block_id"])
        if block is None:
            skipped.append({"comment_id": item["comment_id"], "reason": "block_not_found"})
            continue
        content = block.get("content")
        if not isinstance(content, str):
            skipped.append({"comment_id": item["comment_id"], "reason": "block_content_not_string"})
            continue
        old = replacement["old"]
        new = replacement["new"]
        if old not in content:
            skipped.append({"comment_id": item["comment_id"], "reason": "selected_text_not_found"})
            continue
        block["content"] = content.replace(old, new, 1)
        applied += 1
        applied_comment_ids.append(item["comment_id"])

    if applied:
        write_json(model_path, model)
    return {"applied": applied, "applied_comment_ids": applied_comment_ids, "skipped": skipped}


def add_implementation_replies(
    payload: dict[str, Any],
    applied_comment_ids: object,
    classifications: list[dict[str, Any]],
    *,
    agent_author: str,
) -> int:
    if not isinstance(applied_comment_ids, list):
        return 0
    applied_ids = {comment_id for comment_id in applied_comment_ids if isinstance(comment_id, str)}
    if not applied_ids:
        return 0
    replacements = {
        item["comment_id"]: item.get("replacement")
        for item in classifications
        if item["comment_id"] in applied_ids
    }
    replies_added = 0
    for thread in payload["comments"]:
        if thread["id"] not in applied_ids:
            continue
        if not _has_agent_implementation_reply(thread):
            replacement = replacements.get(thread["id"])
            thread["replies"].append(
                make_reply(
                    author=agent_author,
                    role="agent",
                    kind="implementation_note",
                    body=implementation_reply_body(replacement),
                )
            )
            replies_added += 1
        thread["status"] = "resolved"
        for item in classifications:
            if item["comment_id"] == thread["id"]:
                item["status_after"] = "resolved"
                item["reply_added"] = True
    return replies_added


def implementation_reply_body(replacement: object) -> str:
    if isinstance(replacement, dict) and replacement.get("old") and replacement.get("new"):
        return f"Applied replacement: {replacement['old']} -> {replacement['new']}"
    return "Applied this review comment."


def extract_replacement(thread: dict[str, Any]) -> dict[str, str] | None:
    comment = str(thread.get("comment", ""))
    selected_text = str(thread.get("selected_text", ""))
    for pattern in _REPLACEMENT_PATTERNS:
        match = pattern.search(comment)
        if not match:
            continue
        old = match.groupdict().get("old") or selected_text
        new = match.group("new")
        if old and new:
            return {"operation": "replace_text", "old": old, "new": new}
    return None


def resolve_bundle_json_path(root: Path, relative_path: str) -> Path:
    return _resolve_bundle_json_path(root, relative_path, label="state", error=ReviewIngestionError)


def _find_model_block(blocks: list[Any], block_id: str) -> dict[str, Any] | None:
    for block in blocks:
        if isinstance(block, dict) and block.get("id") == block_id:
            return block
    return None


def _has_agent_clarification(thread: dict[str, Any]) -> bool:
    return any(
        isinstance(reply, dict) and reply.get("role") == "agent" and reply.get("kind") == "clarification_request"
        for reply in thread.get("replies", [])
    )


def _has_agent_implementation_reply(thread: dict[str, Any]) -> bool:
    return any(
        isinstance(reply, dict) and reply.get("role") == "agent" and reply.get("kind") == "implementation_note"
        for reply in thread.get("replies", [])
    )


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)
