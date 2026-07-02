"""Quality checks for agent-designed document models."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.diagram_planner import diagram_source


DEPRECATED_RENDERER_TYPES = frozenset({"section", "text", "table"})
HTML_TAG_RE = re.compile(r"<[A-Za-z][^>]*>")


@dataclass(frozen=True)
class ModelQualityResult:
    ok: bool
    errors: list[str]
    warnings: list[str]

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def check_model_quality(model_path: Path) -> ModelQualityResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ModelQualityResult(ok=False, errors=[f"document model is invalid JSON: {exc}"], warnings=[])
    except OSError as exc:
        return ModelQualityResult(ok=False, errors=[f"document model cannot be read: {exc}"], warnings=[])

    if not isinstance(model, dict):
        return ModelQualityResult(ok=False, errors=["document model must be an object"], warnings=[])

    metadata = model.get("metadata")
    if isinstance(metadata, dict) and metadata.get("planner") == "source-capture-draft":
        errors.append("source-capture draft is not a final HTML document model")

    blocks = model.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        errors.append("document model must contain a non-empty blocks array")
        return ModelQualityResult(ok=False, errors=errors, warnings=warnings)

    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            errors.append(f"block {index} must be an object")
            continue
        block_id = str(block.get("id") or f"#{index}")
        block_type = block.get("type")
        content = block.get("content", "")
        content_text = content if isinstance(content, str) else ""

        if block_type in DEPRECATED_RENDERER_TYPES:
            errors.append(f"block {block_id} uses renderer-unsupported type: {block_type}")
        if block_type == "html":
            _check_html_block(block_id, content_text, errors)
        elif block_type == "callout":
            _check_callout_block(block_id, content_text, errors)
        elif block_type == "image":
            _check_image_block(block_id, block, errors)
        elif block_type == "diagram":
            _check_diagram_block(block_id, block, content_text, errors, warnings)

    return ModelQualityResult(ok=not errors, errors=errors, warnings=warnings)


def _check_html_block(block_id: str, content: str, errors: list[str]) -> None:
    if not HTML_TAG_RE.search(content):
        errors.append(f"html block {block_id} has no HTML structure")
    if "<script" in content.lower():
        errors.append(f"html block {block_id} contains a script tag")
    if re.search(r"\son[a-z]+\s*=", content, flags=re.IGNORECASE):
        errors.append(f"html block {block_id} contains an inline event handler")


def _check_callout_block(block_id: str, content: str, errors: list[str]) -> None:
    if HTML_TAG_RE.search(content):
        errors.append(f"callout block {block_id} must use plain text content")


def _check_image_block(block_id: str, block: dict[str, Any], errors: list[str]) -> None:
    image = block.get("image")
    if not isinstance(image, dict):
        errors.append(f"image block {block_id} must contain image metadata")
        return
    if image.get("generation_status") == "requested" or not image.get("source_path"):
        errors.append(f"image block {block_id} must attach a generated image before render")


def _check_diagram_block(
    block_id: str,
    block: dict[str, Any],
    content: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    source = diagram_source({**block, "content": content})
    if not source.strip():
        errors.append(f"diagram block {block_id} must contain Mermaid source")
    elif not _looks_like_mermaid(source):
        warnings.append(f"diagram block {block_id} does not look like standard Mermaid source")
    image = block.get("image")
    if isinstance(image, dict) and image.get("generation_status") == "requested":
        errors.append(f"diagram block {block_id} must attach a generated image before render")


def _looks_like_mermaid(source: str) -> bool:
    compact = source.strip().lower()
    # This startswith validation is intentionally separate from diagram_planner._classify_diagram.
    return compact.startswith(
        (
            "flowchart",
            "graph",
            "sequencediagram",
            "statediagram",
            "classdiagram",
            "erdiagram",
            "gantt",
            "journey",
            "timeline",
            "mindmap",
            "quadrantchart",
            "c4context",
            "pie",
            "gitgraph",
            "requirementdiagram",
            "sankey",
            "xychart",
            "architecture",
            "block",
            "packet",
            "kanban",
            "radar",
            "treemap",
            "zenuml",
        )
    )
