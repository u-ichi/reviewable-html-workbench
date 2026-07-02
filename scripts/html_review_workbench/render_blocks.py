"""Render individual document blocks for reviewable HTML bundles."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.diagram_planner import PlannedDiagram


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
