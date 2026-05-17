"""Render document models into reviewable HTML bundles."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from scripts.html_review_workbench import __version__
from scripts.html_review_workbench.diagram_planner import PlannedDiagram, plan_diagrams, write_diagram_sources


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "templates" / "report.html.j2"
STYLE_PATH = ROOT / "templates" / "style.css"
COMMENTS_JS_PATH = ROOT / "templates" / "review-comments.js"


def render_bundle(model_path: Path, output_dir: Path) -> Path:
    model_bytes = model_path.read_bytes()
    model = json.loads(model_bytes.decode("utf-8"))

    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    rendered_at = datetime.now(timezone.utc).isoformat()

    diagrams = plan_diagrams(model["blocks"])
    diagram_outputs = write_diagram_sources(output_dir, diagrams)
    body_html, review_blocks = _render_blocks(model["blocks"], diagrams)
    review_blocks.insert(
        0,
        {
            "id": "document-header",
            "type": "header",
            "review_required": False,
        },
    )
    html = _render_template(
        {
            "title": escape(model["title"]),
            "document_id": escape(model["document_id"]),
            "summary": _render_optional_summary(model.get("summary")),
            "generated_at": escape(model["generated_at"]),
            "asset_version": escape(rendered_at, quote=True),
            "body": body_html,
        }
    )

    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    shutil.copyfile(STYLE_PATH, assets_dir / "style.css")
    shutil.copyfile(COMMENTS_JS_PATH, assets_dir / "review-comments.js")

    manifest = {
        "schema_version": "1.0",
        "renderer_version": __version__,
        "generated_at": rendered_at,
        "input": {
            "path": str(model_path),
            "sha256": hashlib.sha256(model_bytes).hexdigest(),
        },
        "document": {
            "id": model["document_id"],
            "title": model["title"],
        },
        "outputs": {
            "index": "index.html",
            "assets": ["assets/style.css", "assets/review-comments.js"],
            "diagrams": diagram_outputs,
        },
        "diagrams": [diagram.to_manifest() for diagram in diagrams.values()],
        "review_blocks": review_blocks,
    }
    (output_dir / "renderer-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_path


def _render_template(values: dict[str, str]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{ " + key + " }}", value)
    return template


def _render_optional_summary(summary: object) -> str:
    if not isinstance(summary, str) or not summary:
        return ""
    return f'<p class="document-summary">{escape(summary)}</p>'


def _render_blocks(
    blocks: list[dict[str, Any]],
    diagrams: dict[str, PlannedDiagram],
) -> tuple[str, list[dict[str, Any]]]:
    html_parts: list[str] = []
    review_blocks: list[dict[str, Any]] = []
    for block in blocks:
        block_id = block["id"]
        block_type = block["type"]
        review_required = bool(block.get("review_required", False))
        html_parts.append(_render_block(block, review_required, diagrams.get(block_id)))
        review_blocks.append(
            {
                "id": block_id,
                "type": block_type,
                "review_required": review_required,
                **_review_block_diagram_metadata(diagrams.get(block_id)),
            }
        )
    return "\n".join(html_parts), review_blocks


def _render_block(block: dict[str, Any], review_required: bool, diagram: PlannedDiagram | None) -> str:
    block_id = escape(block["id"], quote=True)
    block_type = escape(block["type"], quote=True)
    review_attr = "true" if review_required else "false"
    title_html = _render_block_title(block.get("title"))
    content_html = _render_block_content(block, diagram)
    return (
        f'<section class="review-block review-block-{block_type}" '
        f'id="{block_id}" data-review-block="{block_id}" '
        f'data-block-type="{block_type}" data-review-required="{review_attr}">\n'
        f"{title_html}\n"
        f"{content_html}\n"
        "</section>"
    )


def _render_block_title(title: object) -> str:
    if not isinstance(title, str) or not title:
        return ""
    return f"<h2>{escape(title)}</h2>"


def _render_block_content(block: dict[str, Any], diagram: PlannedDiagram | None) -> str:
    content = block.get("content", "")
    block_type = block["type"]
    if block_type == "html":
        return f'<div class="block-content">{content}</div>'
    if block_type == "callout":
        return f'<div class="block-content callout">{escape(content)}</div>'
    if diagram is not None:
        return _render_diagram_fallback(diagram)
    return f'<p class="block-content">{escape(content)}</p>'


def _render_diagram_fallback(diagram: PlannedDiagram) -> str:
    source_path = escape(diagram.relative_path, quote=True)
    kind = escape(diagram.kind, quote=True)
    source = escape(diagram.source)
    return (
        '<figure class="block-content diagram-fallback" '
        f'data-diagram-kind="{kind}" data-diagram-source="{source_path}">\n'
        f'  <figcaption>Mermaid source: <code>{source_path}</code></figcaption>\n'
        f'  <pre class="diagram-source"><code>{source}</code></pre>\n'
        "</figure>"
    )


def _review_block_diagram_metadata(diagram: PlannedDiagram | None) -> dict[str, str]:
    if diagram is None:
        return {}
    return {
        "diagram_kind": diagram.kind,
        "diagram_source": diagram.relative_path,
    }
