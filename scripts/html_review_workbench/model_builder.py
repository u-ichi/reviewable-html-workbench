"""Build source-capture draft document models for HTML output."""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.common import now_iso, write_json


DEFAULT_TITLE = "HTML Output"
DEFAULT_DOCUMENT_ID = "html-output"


class ModelBuildError(ValueError):
    """Raised when a document model cannot be built from the provided input."""


@dataclass(frozen=True)
class BuildModelResult:
    path: Path
    model: dict[str, Any]


def build_model_from_source(
    *,
    output_path: Path,
    text: str | None = None,
    input_path: Path | None = None,
    title: str | None = None,
    document_id: str | None = None,
) -> BuildModelResult:
    source_text = resolve_source_text(text=text, input_path=input_path)
    model = build_model(source_text, title=title, document_id=document_id, source_path=input_path)
    write_json(output_path, model, ensure_parent=True)
    return BuildModelResult(path=output_path, model=model)


def resolve_source_text(*, text: str | None = None, input_path: Path | None = None) -> str:
    if text is not None and input_path is not None:
        raise ModelBuildError("--text and --input cannot be used together")
    if text is not None:
        source_text = text
    elif input_path is not None:
        source_text = input_path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        source_text = sys.stdin.read()
    else:
        raise ModelBuildError("one of --text, --input, or stdin is required")
    if not source_text.strip():
        raise ModelBuildError("input content is empty")
    return source_text


def build_model(
    source_text: str,
    *,
    title: str | None = None,
    document_id: str | None = None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    resolved_title = title or infer_title(source_text, source_path=source_path)
    resolved_document_id = document_id or slugify(resolved_title)
    blocks = plan_blocks(source_text)
    return {
        "schema_version": "1.0",
        "document_id": resolved_document_id,
        "title": resolved_title,
        "summary": "Source-capture draft for agent-designed reviewable HTML output.",
        "generated_at": now_iso(),
        "metadata": {
            "source": str(source_path) if source_path is not None else "inline",
            "planner": "source-capture-draft",
            "final_model_required": True,
        },
        "review_settings": {
            "enabled": True,
            "mode": "standalone",
        },
        "blocks": blocks,
    }


def infer_title(source_text: str, *, source_path: Path | None = None) -> str:
    for line in source_text.splitlines():
        stripped = line.strip().strip("#").strip()
        if stripped:
            return stripped[:80]
    if source_path is not None:
        return source_path.stem.replace("-", " ").replace("_", " ").strip().title() or DEFAULT_TITLE
    return DEFAULT_TITLE


def plan_blocks(source_text: str) -> list[dict[str, Any]]:
    return [
        html_block(
            "source-capture",
            "Source capture draft",
            source_capture_html(source_text),
        )
    ]


def html_block(
    block_id: str,
    title: str,
    content: str,
) -> dict[str, Any]:
    return {
        "id": block_id,
        "type": "html",
        "heading_level": 2,
        "title": title,
        "content": content,
        "review_required": True,
    }


def source_capture_html(source_text: str) -> str:
    return f"<pre><code>{html.escape(source_text.strip())}</code></pre>"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or DEFAULT_DOCUMENT_ID
