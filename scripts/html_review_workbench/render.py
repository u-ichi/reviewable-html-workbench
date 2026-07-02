"""Render document models into reviewable HTML bundles."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

from scripts.html_review_workbench import __version__
from scripts.html_review_workbench.common import MERMAID_INIT_JS, REPO_ROOT, now_iso, unique_path, write_json
from scripts.html_review_workbench.diagram_planner import PlannedDiagram, plan_diagrams, write_diagram_sources


ROOT = REPO_ROOT
TEMPLATE_PATH = ROOT / "templates" / "report.html.j2"
STYLE_PATH = ROOT / "templates" / "style.css"
COMMENTS_JS_PATH = ROOT / "templates" / "review-comments.js"
MERMAID_JS_PATH = ROOT / "templates" / "assets" / "mermaid.min.js"
DIAGRAM_ZOOM_JS_PATH = ROOT / "templates" / "assets" / "diagram-zoom.js"


def render_bundle(model_path: Path, output_dir: Path) -> Path:
    model_bytes = model_path.read_bytes()
    model = json.loads(model_bytes.decode("utf-8"))

    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    rendered_at = now_iso()

    diagrams = plan_diagrams(model["blocks"])
    diagram_outputs = write_diagram_sources(output_dir, diagrams)
    image_outputs = _prepare_image_assets(model["blocks"], model_path.parent, output_dir)
    body_html, review_blocks = _render_blocks(model["blocks"], diagrams, image_outputs)
    has_rendered_mermaid = 'class="mermaid"' in body_html
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
            "mermaid_head": _render_mermaid_head(rendered_at) if has_rendered_mermaid else "",
            "body": body_html,
            "toc": _render_toc(model["blocks"]),
        }
    )

    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    shutil.copyfile(STYLE_PATH, assets_dir / "style.css")
    shutil.copyfile(COMMENTS_JS_PATH, assets_dir / "review-comments.js")
    asset_outputs = ["assets/style.css", "assets/review-comments.js"]
    if has_rendered_mermaid:
        if not MERMAID_JS_PATH.is_file():
            raise ValueError(f"Mermaid asset not found: {MERMAID_JS_PATH}")
        if not DIAGRAM_ZOOM_JS_PATH.is_file():
            raise ValueError(f"Diagram zoom asset not found: {DIAGRAM_ZOOM_JS_PATH}")
        shutil.copyfile(MERMAID_JS_PATH, assets_dir / "mermaid.min.js")
        shutil.copyfile(DIAGRAM_ZOOM_JS_PATH, assets_dir / "diagram-zoom.js")
        asset_outputs.append("assets/mermaid.min.js")
        asset_outputs.append("assets/diagram-zoom.js")

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
            "assets": asset_outputs,
            "diagrams": diagram_outputs,
            "images": list(image_outputs.values()),
        },
        "diagrams": [diagram.to_manifest() for diagram in diagrams.values()],
        "review_blocks": review_blocks,
    }
    write_json(output_dir / "renderer-manifest.json", manifest)
    return index_path


def _render_template(values: dict[str, str]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{ " + key + " }}", value)
    return template


def _render_mermaid_head(asset_version: str) -> str:
    version = escape(asset_version, quote=True)
    return (
        f'  <script src="assets/mermaid.min.js?v={version}"></script>\n'
        f"  <script>{MERMAID_INIT_JS}</script>\n"
        f'  <script src="assets/diagram-zoom.js?v={version}" defer></script>'
    )


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
    if not any(block["heading_level"] == 2 for block in blocks):
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
        heading_level = block["heading_level"]
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
        heading_level = int(block["heading_level"])
        sec_num = None
        if isinstance(title, str) and title:
            if heading_level == 2:
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
                heading_level,
                sec_num,
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
    heading_level: int,
    section_number: str | None = None,
) -> str:
    block_id = escape(block["id"], quote=True)
    block_type = escape(block["type"], quote=True)
    review_attr = "true" if review_required else "false"
    title_html = _render_block_title(block.get("title"), heading_level)
    content_html = _render_block_content(block, diagram, image_src, heading_level, section_number)
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
    heading_level: int,
) -> str:
    if not isinstance(title, str) or not title:
        return ""
    tag = f"h{heading_level}"
    return f"<{tag}>{escape(title)}</{tag}>"


def _render_block_content(
    block: dict[str, Any],
    diagram: PlannedDiagram | None,
    image_src: str | None,
    heading_level: int,
    section_number: str | None = None,
) -> str:
    content = block.get("content", "")
    block_type = block["type"]
    if image_src is not None:
        return _render_image(block, image_src)
    if block_type == "html":
        if section_number is not None:
            content = _shift_content_headings(str(content), heading_level)
        return f'<div class="block-content">{content}</div>'
    if block_type == "callout":
        level = block.get("level", "info")
        icon = {"warn": "!", "success": "✓"}.get(level, "i")
        title_html = ""
        callout_title = block.get("callout_title", "")
        if callout_title:
            title_html = f'<div class="co-title">{escape(callout_title)}</div>'
        return (
            f'<div class="callout {escape(level, quote=True)}" role="doc-note">'
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


def _shift_content_headings(content: str, heading_level: int) -> str:
    if heading_level == 3:
        content = content.replace("<h3>", "<h4>")
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
    return (
        '  <figure class="diagram-wrap">'
        '<button type="button" class="diagram-zoom-btn" aria-label="拡大">⤢</button>'
        f'<pre class="mermaid">{escape(diagram.source)}</pre>'
        '</figure>'
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
    return unique_path(
        path,
        on_exhausted=lambda exhausted: ValueError(f"could not choose unique output image path for: {exhausted}"),
    )


def _review_block_diagram_metadata(diagram: PlannedDiagram | None) -> dict[str, str]:
    if diagram is None:
        return {}
    return {
        "diagram_kind": diagram.kind,
        "diagram_source": diagram.relative_path,
    }
