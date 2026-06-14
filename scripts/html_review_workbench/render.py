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
    metadata = model.get("metadata") if isinstance(model.get("metadata"), dict) else {}
    doc_lang = str(metadata.get("lang", "ja"))
    html = _render_template(
        {
            "lang": escape(doc_lang),
            "title": escape(model["title"]),
            "document_id": escape(model["document_id"]),
            "eyebrow": escape(str(metadata.get("eyebrow", "Reviewable HTML Workbench"))),
            "doc_status": _render_doc_status(metadata),
            "deck": _render_deck(metadata),
            "byline": _render_byline(metadata),
            "meta_grid": _render_meta_grid(metadata, model["generated_at"]),
            "summary": _render_optional_summary(model.get("summary"), doc_lang),
            "generated_at": escape(model["generated_at"]),
            "asset_version": escape(rendered_at, quote=True),
            "body": body_html,
            "toc": _render_toc(model["blocks"]),
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


def _render_optional_summary(summary: object, lang: str = "ja") -> str:
    if not isinstance(summary, str) or not summary:
        return ""
    heading = "Summary (TL;DR)" if lang != "ja" else "要約 (TL;DR)"
    return (
        '<section class="summary">'
        '<div class="summary-h">'
        '<svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">'
        '<path d="M3 4h10M3 8h10M3 12h6"/></svg>'
        f'{heading}'
        '</div>'
        f'<p>{escape(summary)}</p>'
        '</section>'
    )


def _render_doc_status(metadata: dict[str, Any]) -> str:
    status = metadata.get("status")
    label = metadata.get("status_label")
    if not status or not label:
        return ""
    css_class = escape(str(status), quote=True)
    return (
        f'<span class="doc-status {css_class}">'
        f'<span class="dot"></span>{escape(str(label))}'
        '</span>'
    )


def _render_deck(metadata: dict[str, Any]) -> str:
    deck = metadata.get("deck")
    if not isinstance(deck, str) or not deck:
        return ""
    return f'<p class="doc-deck">{escape(deck)}</p>'


def _render_byline(metadata: dict[str, Any]) -> str:
    byline = metadata.get("byline")
    if not isinstance(byline, dict):
        return ""
    parts: list[str] = []
    agent = byline.get("agent")
    if agent:
        parts.append(
            '<span class="agent-badge">'
            '<span class="agent-avatar">AI</span>'
            f'{escape(str(agent))}'
            '</span>'
        )
    reviewers = byline.get("reviewers")
    if reviewers:
        parts.append(f'<span class="muted">人手レビュー: {escape(str(reviewers))}</span>')
    if not parts:
        return ""
    return f'<div class="byline">{"".join(parts)}</div>'


def _render_meta_grid(metadata: dict[str, Any], generated_at: str) -> str:
    cells = metadata.get("meta_grid")
    if not isinstance(cells, list) or not cells:
        return f'<p class="doc-meta document-meta">Source generated at <time>{escape(generated_at)}</time></p>'
    parts: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        key = escape(str(cell.get("key", "")))
        value = str(cell.get("value", ""))
        mono = bool(cell.get("mono", False))
        confidence = cell.get("confidence")
        val_html = ""
        if isinstance(confidence, int):
            bars = []
            for i in range(5):
                fill = " fill" if i < confidence else ""
                bars.append(f'<span class="bar{fill}"></span>')
            val_html = f'<span class="confidence">{"".join(bars)}</span> {escape(value)}'
        elif mono:
            val_html = f'<span class="mono">{escape(value)}</span>'
        else:
            val_html = escape(value)
        parts.append(
            f'<div class="meta-cell">'
            f'<div class="meta-key">{key}</div>'
            f'<div class="meta-val">{val_html}</div>'
            f'</div>'
        )
    if not parts:
        return f'<p class="doc-meta document-meta">Source generated at <time>{escape(generated_at)}</time></p>'
    return f'<div class="meta-grid" aria-label="生成メタデータ">{"".join(parts)}</div>'


def _render_toc(blocks: list[dict[str, Any]]) -> str:
    if not any(block.get("heading_level") == 2 for block in blocks):
        items: list[str] = []
        for block in blocks:
            title = block.get("title")
            if not isinstance(title, str) or not title:
                continue
            block_id = escape(block["id"], quote=True)
            items.append(f'<li><a href="#{block_id}">{escape(title)}</a></li>')
        if not items:
            return ""
        return "<ol>\n" + "\n".join(items) + "\n</ol>"

    html = '<ol class="toc-list">\n'
    in_nested = False
    for block in blocks:
        title = block.get("title")
        if not isinstance(title, str) or not title:
            continue
        block_id = escape(block["id"], quote=True)
        heading_level = block.get("heading_level", 3)
        if heading_level == 2:
            if in_nested:
                html += "</ol>\n</li>\n"
                in_nested = False
            html += f'<li class="toc-h2"><a href="#{block_id}">{escape(title)}</a>\n'
            html += "<ol>\n"
            in_nested = True
        else:
            if not in_nested:
                html += '<li class="toc-h2"><span></span>\n<ol>\n'
                in_nested = True
            html += f'<li><a href="#{block_id}">{escape(title)}</a></li>\n'
    if in_nested:
        html += "</ol>\n</li>\n"
    html += "</ol>"
    return html


def _render_blocks(
    blocks: list[dict[str, Any]],
    diagrams: dict[str, PlannedDiagram],
    image_outputs: dict[str, str],
) -> tuple[str, list[dict[str, Any]]]:
    html_parts: list[str] = []
    review_blocks: list[dict[str, Any]] = []
    h2_counter = 0
    h3_counter = 0
    for block in blocks:
        block_id = block["id"]
        block_type = block["type"]
        review_required = bool(block.get("review_required", False))
        title = block.get("title")
        heading_level = int(block.get("heading_level", 3))
        sec_num = None
        if isinstance(title, str) and title:
            if heading_level == 2:
                if block_id in ("layer1-header", "layer2-header", "layer3-header"):
                    h2_counter += 1
                    sec_num = str(h2_counter)
                h3_counter = 0
            else:
                h3_counter += 1
                if h2_counter > 0:
                    sec_num = f"{h2_counter}.{h3_counter}"
                else:
                    sec_num = str(h3_counter)
        html_parts.append(
            _render_block(
                block,
                review_required,
                diagrams.get(block_id),
                image_outputs.get(block_id),
                sec_num,
                heading_level,
            )
        )
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
    section_number: str | None = None,
    heading_level: int = 3,
) -> str:
    block_id = escape(block["id"], quote=True)
    block_type = escape(block["type"], quote=True)
    review_attr = "true" if review_required else "false"
    title_html = _render_block_title(block.get("title"), block_id, section_number, heading_level)
    content_html = _render_block_content(block, diagram, image_src, section_number, heading_level)
    return (
        '<section class="review-block" '
        f'id="{block_id}" data-review-block="{block_id}" '
        f'data-block-type="{block_type}" data-review-required="{review_attr}">\n'
        f"{title_html}\n"
        f"{content_html}\n"
        "</section>"
    )


def _render_block_title(
    title: object,
    block_id: str = "",
    section_number: str | None = None,
    heading_level: int = 3,
) -> str:
    if not isinstance(title, str) or not title:
        return ""
    sec_span = ""
    if section_number is not None:
        sec_span = f'<span class="sec-no">{section_number}</span>'
    tag = f"h{heading_level}"
    return f"<{tag}>{sec_span}{escape(title)}</{tag}>"


def _render_block_content(
    block: dict[str, Any],
    diagram: PlannedDiagram | None,
    image_src: str | None,
    section_number: str | None = None,
    heading_level: int = 3,
) -> str:
    content = block.get("content", "")
    block_type = block["type"]
    if image_src is not None:
        return _render_image(block, image_src)
    if block_type == "html":
        if section_number is not None:
            content = _shift_content_headings(str(content), section_number, heading_level)
        return f'<div class="block-content">{content}</div>'
    if block_type == "callout":
        level = block.get("level", "info")
        icon = {"warn": "!", "success": "✓"}.get(level, "i")
        title_html = ""
        callout_title = block.get("callout_title", "")
        if callout_title:
            title_html = f'<div class="co-title">{escape(callout_title)}</div>'
        return (
            f'<div class="callout {escape(level, quote=True)}">'
            f'<div class="co-ico">{icon}</div>'
            f'<div>{title_html}<div class="co-body"><p>{escape(content)}</p></div></div>'
            '</div>'
        )
    if block_type == "code":
        return _render_code_block(block)
    if block_type == "log":
        return _render_log_block(block)
    if block_type == "image":
        return _render_image(block, image_src)
    if diagram is not None:
        return _render_diagram(diagram)
    return f'<p class="block-content">{escape(content)}</p>'


def _shift_content_headings(content: str, section_number: str, heading_level: int) -> str:
    sub_counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal sub_counter
        sub_counter += 1
        sub_no = f'{section_number}.{sub_counter}'
        tag = "h4" if heading_level == 3 else "h3"
        return f'<{tag}><span class="sub-sec-no">{sub_no}</span>'

    content = re.sub(r"<h3>", repl, content)
    if heading_level == 3:
        content = content.replace("</h3>", "</h4>")
    return content


def _render_code_block(block: dict[str, Any]) -> str:
    content = block.get("content", "")
    filename = block.get("filename", "")
    language = block.get("language", "")
    lines = content.splitlines()
    line_spans = []
    highlight_lines = set(block.get("highlight_lines", []))
    for i, line in enumerate(lines, 1):
        hl_class = " hl" if i in highlight_lines else ""
        line_spans.append(f'<span class="ln{hl_class}" data-n="{i}">{escape(line)}</span>')
    fname_html = f'<span class="fname">{escape(filename)}</span>' if filename else ""
    lang_html = f'<span class="lang">{escape(language)}</span>' if language else ""
    return (
        '<div class="code">'
        f'<div class="code-bar"><span class="dots"><i></i><i></i><i></i></span>{fname_html}{lang_html}</div>'
        f'<pre class="code-body">{"".join(line_spans)}</pre>'
        '</div>'
    )


def _render_log_block(block: dict[str, Any]) -> str:
    content = block.get("content", "")
    filename = block.get("filename", "")
    language = block.get("language", "LOG")
    lines = content.splitlines()
    log_spans = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        level_class, line_class = _detect_log_level(line)
        log_spans.append(f'<span class="log-line{line_class}">{_format_log_line(line, level_class)}</span>')
    fname_html = f'<span class="fname">{escape(filename)}</span>' if filename else ""
    lang_html = f'<span class="lang">{escape(language)}</span>'
    return (
        '<div class="code log">'
        f'<div class="code-bar"><span class="dots"><i></i><i></i><i></i></span>{fname_html}{lang_html}</div>'
        f'<div class="code-body">{"".join(log_spans)}</div>'
        '</div>'
    )


_LOG_LEVEL_PATTERN = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d{2}[.\d]*)\s+(?P<lvl>INFO|OK|WARN|ERROR|DEBUG)\s+(?P<msg>.*)",
)


def _detect_log_level(line: str) -> tuple[str, str]:
    match = _LOG_LEVEL_PATTERN.search(line)
    if not match:
        return "", ""
    lvl = match.group("lvl").lower()
    line_class = ""
    if lvl == "warn":
        line_class = " is-warn"
    elif lvl in ("error", "err"):
        line_class = " is-err"
    return lvl, line_class


def _format_log_line(line: str, level_class: str) -> str:
    match = _LOG_LEVEL_PATTERN.search(line)
    if not match:
        return escape(line)
    ts = escape(match.group("ts"))
    lvl = escape(match.group("lvl"))
    msg = escape(match.group("msg"))
    lvl_css = level_class if level_class else ""
    if level_class == "error":
        lvl_css = "err"
    return f'<span class="ts">{ts}</span> <span class="lvl {lvl_css}">{lvl:<5s}</span> {msg}'


def _render_diagram(diagram: PlannedDiagram) -> str:
    source_path = escape(diagram.relative_path, quote=True)
    kind = escape(diagram.kind, quote=True)
    source = escape(diagram.source)
    flow_html = _render_diagram_flow(diagram)
    return (
        '<div class="diagram-fallback" '
        f'data-diagram-kind="{kind}" data-diagram-source="{source_path}">\n'
        '  <div class="df-head">'
        '<span class="df-badge">DIAGRAM FALLBACK</span>'
        f' <span>{escape(diagram.kind)} diagram</span>'
        '</div>\n'
        f"{flow_html}\n"
        f'  <div class="df-raw">source: {source_path}</div>\n'
        f'  <pre class="diagram-source"><code>{source}</code></pre>\n'
        "</div>"
    )


def _render_diagram_flow(diagram: PlannedDiagram) -> str:
    nodes, edges = _diagram_preview_graph(diagram.source)
    if not nodes:
        return '<div class="flow"><div class="node"><div class="n-t">Preview unavailable</div></div></div>'
    seen: set[str] = set()
    parts: list[str] = []
    for source_node, target_node in edges:
        if source_node not in seen:
            parts.append(f'<div class="node"><div class="n-t">{escape(source_node)}</div></div>')
            seen.add(source_node)
        parts.append('<div class="arrow">→</div>')
        if target_node not in seen:
            parts.append(f'<div class="node"><div class="n-t">{escape(target_node)}</div></div>')
            seen.add(target_node)
    for node in nodes:
        if node not in seen:
            parts.append(f'<div class="node"><div class="n-t">{escape(node)}</div></div>')
            seen.add(node)
    return f'  <div class="flow">{"".join(parts)}</div>'


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
    src_escaped = escape(image_src, quote=True)
    tag_label = escape(Path(image_src).name)
    caption_parts = []
    if caption:
        caption_parts.append(f"  <figcaption><span class=\"fc-no\">図</span>{escape(str(caption))}</figcaption>\n")
    return (
        '<figure class="figure generated-image">\n'
        f'  <div class="gen-image">'
        f'<span class="gi-tag">generated-image · {tag_label}</span>'
        f'<img src="{src_escaped}" alt="{alt}" loading="lazy" style="width:100%;height:100%;object-fit:contain;position:absolute;inset:0;">'
        f'</div>\n'
        f"{''.join(caption_parts)}"
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
