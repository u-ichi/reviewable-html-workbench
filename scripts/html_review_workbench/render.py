"""Render document models into reviewable HTML bundles."""

from __future__ import annotations

import hashlib
import json
import re
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
    image_outputs = _prepare_image_assets(model["blocks"], model_path.parent, output_dir)
    body_html, review_blocks = _render_blocks(model["blocks"], diagrams, image_outputs)
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
            "images": list(image_outputs.values()),
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
    image_outputs: dict[str, str],
) -> tuple[str, list[dict[str, Any]]]:
    html_parts: list[str] = []
    review_blocks: list[dict[str, Any]] = []
    for block in blocks:
        block_id = block["id"]
        block_type = block["type"]
        review_required = bool(block.get("review_required", False))
        html_parts.append(_render_block(block, review_required, diagrams.get(block_id), image_outputs.get(block_id)))
        review_blocks.append(
            {
                "id": block_id,
                "type": block_type,
                "review_required": review_required,
                **_review_block_diagram_metadata(diagrams.get(block_id)),
            }
        )
    return "\n".join(html_parts), review_blocks


def _render_block(
    block: dict[str, Any],
    review_required: bool,
    diagram: PlannedDiagram | None,
    image_src: str | None,
) -> str:
    block_id = escape(block["id"], quote=True)
    block_type = escape(block["type"], quote=True)
    review_attr = "true" if review_required else "false"
    title_html = _render_block_title(block.get("title"))
    content_html = _render_block_content(block, diagram, image_src)
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


def _render_block_content(block: dict[str, Any], diagram: PlannedDiagram | None, image_src: str | None) -> str:
    content = block.get("content", "")
    block_type = block["type"]
    if image_src is not None:
        return _render_image(block, image_src)
    if block_type == "html":
        return f'<div class="block-content">{content}</div>'
    if block_type == "callout":
        return f'<div class="block-content callout">{escape(content)}</div>'
    if block_type == "image":
        return _render_image(block, image_src)
    if diagram is not None:
        return _render_diagram(diagram)
    return f'<p class="block-content">{escape(content)}</p>'


def _render_diagram(diagram: PlannedDiagram) -> str:
    source_path = escape(diagram.relative_path, quote=True)
    kind = escape(diagram.kind, quote=True)
    source = escape(diagram.source)
    preview = _render_diagram_preview(diagram)
    return (
        '<figure class="block-content diagram-fallback mermaid-diagram" '
        f'data-diagram-kind="{kind}" data-diagram-source="{source_path}">\n'
        f"{preview}\n"
        f'  <figcaption>Diagram source: <code>{source_path}</code></figcaption>\n'
        f'  <pre class="diagram-source"><code>{source}</code></pre>\n'
        "</figure>"
    )


def _prepare_image_assets(blocks: list[dict[str, Any]], model_dir: Path, output_dir: Path) -> dict[str, str]:
    outputs: dict[str, str] = {}
    images_dir = output_dir / "assets" / "images"
    for block in blocks:
        block_type = block.get("type")
        if block_type not in {"image", "diagram"}:
            continue
        image = block.get("image")
        if not isinstance(image, dict):
            if block_type == "image":
                raise ValueError(f"image block requires generated image.source_path before render: {block['id']}")
            continue
        block_id = block["id"]
        if not image.get("source_path"):
            if block_type == "image":
                raise ValueError(f"image block requires generated image.source_path before render: {block_id}")
            continue
        source = Path(str(image["source_path"]))
        source_path = source if source.is_absolute() else model_dir / source
        if not source_path.is_file():
            raise ValueError(f"image source file not found for block {block_id}: {source_path}")
        images_dir.mkdir(parents=True, exist_ok=True)
        destination = _unique_output_asset(images_dir / source_path.name)
        shutil.copy2(source_path, destination)
        outputs[block_id] = destination.relative_to(output_dir).as_posix()
    return outputs


def _render_image(block: dict[str, Any], image_src: str | None) -> str:
    if image_src is None:
        raise ValueError(f"image block missing prepared image asset: {block['id']}")
    image = block.get("image") if isinstance(block.get("image"), dict) else {}
    alt = escape(str(image.get("alt") or block.get("title") or block["id"]), quote=True)
    caption = image.get("caption") or block.get("content")
    caption_html = f"  <figcaption>{escape(str(caption))}</figcaption>\n" if caption else ""
    return (
        '<figure class="block-content generated-image">\n'
        f'  <img src="{escape(image_src, quote=True)}" alt="{alt}" loading="lazy">\n'
        f"{caption_html}"
        "</figure>"
    )


def _unique_output_asset(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError(f"could not choose unique output image path for: {path}")


def _render_diagram_preview(diagram: PlannedDiagram) -> str:
    nodes, edges = _diagram_preview_graph(diagram.source)
    if not nodes:
        return '<div class="diagram-preview-empty">Diagram preview unavailable.</div>'
    width = 220 * max(1, len(nodes))
    height = 170
    positions = {
        node: (80 + index * 200, 80)
        for index, node in enumerate(nodes)
    }
    svg_parts = [
        f'<svg class="diagram-preview" role="img" aria-label="{escape(diagram.kind, quote=True)} diagram" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z"/></marker></defs>',
    ]
    for source, target in edges:
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        svg_parts.append(
            f'<line class="diagram-edge" x1="{x1 + 54}" y1="{y1}" x2="{x2 - 54}" y2="{y2}" marker-end="url(#arrow)"/>'
        )
    for node, (x, y) in positions.items():
        label = escape(node)
        svg_parts.append(f'<rect class="diagram-node" x="{x - 56}" y="{y - 28}" width="112" height="56" rx="8"/>')
        svg_parts.append(f'<text class="diagram-label" x="{x}" y="{y + 5}" text-anchor="middle">{label}</text>')
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def _diagram_preview_graph(source: str) -> tuple[list[str], list[tuple[str, str]]]:
    edges: list[tuple[str, str]] = []
    labels: dict[str, str] = {}
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if "-->" not in line:
            continue
        left, right = line.split("-->", 1)
        source_id, source_label = _diagram_endpoint(left)
        target_id, target_label = _diagram_endpoint(right)
        labels[source_id] = source_label
        labels[target_id] = target_label
        edges.append((source_id, target_id))
    node_ids: list[str] = []
    for source_id, target_id in edges:
        if source_id not in node_ids:
            node_ids.append(source_id)
        if target_id not in node_ids:
            node_ids.append(target_id)
    return [labels.get(node_id, node_id) for node_id in node_ids], [
        (labels.get(source_id, source_id), labels.get(target_id, target_id))
        for source_id, target_id in edges
    ]


def _diagram_endpoint(value: str) -> tuple[str, str]:
    cleaned = value.strip()
    match = re.search(r"(?P<id>[A-Za-z0-9_]+)\[(?P<label>.+?)\]", cleaned)
    if match:
        return match.group("id"), match.group("label")
    token = re.sub(r"[^A-Za-z0-9_]+", "", cleaned) or cleaned
    return token, cleaned


def _review_block_diagram_metadata(diagram: PlannedDiagram | None) -> dict[str, str]:
    if diagram is None:
        return {}
    return {
        "diagram_kind": diagram.kind,
        "diagram_source": diagram.relative_path,
    }
