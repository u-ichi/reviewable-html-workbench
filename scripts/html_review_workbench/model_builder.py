"""Build document models from natural content for HTML output."""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TITLE = "HTML Output"
DEFAULT_DOCUMENT_ID = "html-output"
IMAGE_KEYWORDS = ("image", "photo", "screenshot", "logo", "画像", "写真", "スクリーンショット", "ロゴ", "画面")
DIAGRAM_KEYWORDS = ("flow", "workflow", "dependency", "architecture", "構成", "依存", "流れ", "処理フロー", "ワークフロー")
CALLOUT_KEYWORDS = ("important", "note", "warning", "決定", "注意", "重要", "前提")
PROMPT_CONTENT_LIMIT = 900
PROMPT_DIAGRAM_LIMIT = 1400


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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        "summary": "Generated from natural input for reviewable HTML output.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "source": str(source_path) if source_path is not None else "inline",
            "planner": "content-and-visual",
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
    sections = split_heading_sections(source_text)
    if sections:
        return [
            html_block(unique_block_id(title, index), title, rich_html(body or title))
            for index, (title, body) in enumerate(sections, start=1)
        ]

    chunks = split_source_chunks(source_text)
    blocks: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        title, body = split_chunk_title(chunk, default_title=f"Section {index}")
        block = visual_block_for_chunk(title, body, index)
        blocks.append(block)
    return blocks or [html_block("content", "Content", paragraphs_html([source_text]))]


def split_heading_sections(source_text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    saw_heading = False

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title is not None:
            sections.append((current_title, current_lines))
        current_title = None
        current_lines = []

    for raw_line in source_text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", raw_line)
        if heading:
            saw_heading = True
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 1 and current_title is None and not current_lines and not sections:
                continue
            flush()
            current_title = title
            continue
        if current_title is None:
            if raw_line.strip():
                current_title = "Overview"
        if current_title is not None:
            current_lines.append(raw_line)

    flush()
    if not saw_heading:
        return []
    return [(title, "\n".join(lines).strip()) for title, lines in sections if title.strip()]


def split_source_chunks(source_text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", source_text.strip()) if part.strip()]
    if len(paragraphs) <= 1:
        return [source_text.strip()]
    return paragraphs


def split_chunk_title(chunk: str, *, default_title: str) -> tuple[str, str]:
    lines = [line.rstrip() for line in chunk.splitlines() if line.strip()]
    if not lines:
        return default_title, ""
    first = lines[0].strip()
    if len(lines) > 1 and len(first) <= 80 and not _looks_like_list_item(first) and not _looks_like_markup(first):
        return first.strip(":："), "\n".join(lines[1:]).strip()
    return default_title, "\n".join(lines).strip()


def visual_block_for_chunk(title: str, body: str, index: int) -> dict[str, Any]:
    content = body or title
    block_id = unique_block_id(title, index)
    lowered = content.lower()
    if should_use_callout(title, content):
        return {
            "id": block_id,
            "type": "callout",
            "title": title,
            "content": content,
            "review_required": True,
        }
    if should_use_diagram(content):
        return diagram_block(block_id, title, content)
    table = table_html(content)
    if table is not None:
        return html_block(block_id, title, table)
    ordered = list_html(content, ordered=True)
    if ordered is not None:
        return html_block(block_id, title, ordered)
    unordered = list_html(content, ordered=False)
    if unordered is not None:
        return html_block(block_id, title, unordered)
    if should_use_code(content):
        return html_block(block_id, title, code_html(content))
    if "table" in lowered and ":" in content:
        return html_block(block_id, title, key_value_table_html(content))
    if should_use_image(content):
        return image_block(block_id, title, content)
    return html_block(block_id, title, paragraphs_html(split_paragraphs(content)))


def rich_html(content: str) -> str:
    parts: list[str] = []
    paragraph_lines: list[str] = []
    fenced_lines: list[str] | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        parts.append(chunk_html("\n".join(paragraph_lines).strip()))
        paragraph_lines = []

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            if fenced_lines is None:
                flush_paragraph()
                fenced_lines = []
            else:
                parts.append(code_html("\n".join(fenced_lines).strip()))
                fenced_lines = None
            continue
        if fenced_lines is not None:
            fenced_lines.append(raw_line)
            continue
        if not stripped:
            flush_paragraph()
            continue
        paragraph_lines.append(raw_line)

    if fenced_lines is not None:
        parts.append(code_html("\n".join(fenced_lines).strip()))
    flush_paragraph()
    return "".join(parts) or paragraphs_html([content])


def chunk_html(content: str) -> str:
    table = table_html(content)
    if table is not None:
        return table
    ordered = list_html(content, ordered=True)
    if ordered is not None:
        return ordered
    unordered = list_html(content, ordered=False)
    if unordered is not None:
        return unordered
    return paragraphs_html(split_paragraphs(content))


def html_block(
    block_id: str,
    title: str,
    content: str,
) -> dict[str, Any]:
    return {
        "id": block_id,
        "type": "html",
        "title": title,
        "content": content,
        "review_required": True,
    }


def image_block(block_id: str, title: str, content: str) -> dict[str, Any]:
    return {
        "id": block_id,
        "type": "image",
        "title": title,
        "content": content,
        "review_required": True,
        "image": {
            "prompt": image_generation_prompt(title, content),
            "alt": title,
            "caption": content[:160],
            "generation_status": "requested",
        },
    }


def diagram_block(block_id: str, title: str, content: str) -> dict[str, Any]:
    source = diagram_source(content)
    return {
        "id": block_id,
        "type": "diagram",
        "title": title,
        "content": source,
        "diagram_kind": "flow",
        "diagram_source": source,
        "image": {
            "prompt": diagram_image_generation_prompt(title, source),
            "alt": f"{title} diagram",
            "caption": title,
            "generation_status": "requested",
        },
        "review_required": True,
    }


def image_generation_prompt(title: str, content: str) -> str:
    return _join_prompt_lines(
        [
            "Create a polished explanatory image for a reviewable HTML report.",
            f"Title/context: {title}",
            "Content to visualize:",
            _limited_prompt_text(content, PROMPT_CONTENT_LIMIT),
            "Style requirements: white background, clean business document aesthetic, generous whitespace, clear hierarchy, Japanese Gothic or clean sans-serif typography only when text is needed.",
            "Accuracy requirements: keep text minimal and accurate; do not invent metrics, facts, brand names, official logos, UI labels, or relationships not present in the content.",
            "If this is a screen or UI concept, render it as a mockup instead of a real screenshot. No watermark.",
        ]
    )


def diagram_image_generation_prompt(title: str, source: str) -> str:
    return _join_prompt_lines(
        [
            "Create a polished business infographic image from this Mermaid source for a reviewable HTML report.",
            f"Title/context: {title}",
            "Preserve every node, label, arrow direction, grouping, and relationship in the Mermaid source.",
            "Use a white background, clean Japanese business-document styling, Japanese Gothic or clean sans-serif typography, balanced spacing, and readable labels.",
            "Do not add nodes, facts, relationships, metrics, brand marks, icons, or decorative elements that are not implied by the Mermaid source.",
            "Render the diagram as a finished image; do not show raw Mermaid syntax in the image.",
            "Mermaid source:",
            _limited_prompt_text(source, PROMPT_DIAGRAM_LIMIT),
        ]
    )


def _join_prompt_lines(lines: list[str]) -> str:
    return "\n".join(line.strip() for line in lines if line.strip())


def _limited_prompt_text(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def should_use_diagram(content: str) -> bool:
    lowered = content.lower()
    return "-->" in content or "->" in content or any(keyword in lowered for keyword in DIAGRAM_KEYWORDS)


def should_use_image(content: str) -> bool:
    lowered = content.lower()
    return any(keyword in lowered for keyword in IMAGE_KEYWORDS)


def should_use_callout(title: str, content: str) -> bool:
    text = f"{title}\n{content}".lower()
    return any(keyword in text for keyword in CALLOUT_KEYWORDS)


def should_use_code(content: str) -> bool:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    code_markers = ("$", "def ", "class ", "import ", "from ", "const ", "let ", "var ", "{", "}")
    return sum(1 for line in lines if line.startswith(code_markers) or line.endswith(";")) >= 2


def table_html(content: str) -> str | None:
    rows = []
    for line in content.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or any(not cell for cell in cells):
            continue
        rows.append(cells)
    if len(rows) < 2:
        return None
    if len(rows) >= 3 and _is_table_separator_row(rows[1]):
        rows = [rows[0], *rows[2:]]
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        return None
    header = "".join(f"<th>{html.escape(cell)}</th>" for cell in rows[0])
    body_rows = [
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows[1:]
    ]
    return "<table><thead><tr>{}</tr></thead><tbody>{}</tbody></table>".format(header, "".join(body_rows))


def key_value_table_html(content: str) -> str:
    rows = []
    for line in content.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
        elif "：" in line:
            key, value = line.split("：", 1)
        else:
            continue
        rows.append((key.strip(), value.strip()))
    if not rows:
        return paragraphs_html([content])
    body = "".join(
        f"<tr><th>{html.escape(key)}</th><td>{html.escape(value)}</td></tr>"
        for key, value in rows
    )
    return f"<table><tbody>{body}</tbody></table>"


def list_html(content: str, *, ordered: bool) -> str | None:
    items = []
    for line in content.splitlines():
        stripped = line.strip()
        if ordered:
            match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        else:
            match = re.match(r"^[-*]\s+(.+)$", stripped)
        if not match:
            continue
        items.append(match.group(1).strip())
    if len(items) < 2:
        return None
    tag = "ol" if ordered else "ul"
    body = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<{tag}>{body}</{tag}>"


def code_html(content: str) -> str:
    return f"<pre><code>{html.escape(content)}</code></pre>"


def paragraphs_html(paragraphs: list[str]) -> str:
    return "".join(f"<p>{html.escape(paragraph.strip())}</p>" for paragraph in paragraphs if paragraph.strip())


def split_paragraphs(content: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()] or [content]


def diagram_source(content: str) -> str:
    edges = extract_edges(content)
    if not edges:
        sentences = [part.strip(" .。") for part in re.split(r"[。\n]+", content) if part.strip()]
        if len(sentences) >= 2:
            edges = list(zip(sentences, sentences[1:]))
        else:
            edges = [("Input", "Output")]
    lines = ["flowchart TD"]
    for source, target in edges[:8]:
        lines.append(f"  {diagram_node_id(source)}[{diagram_label(source)}] --> {diagram_node_id(target)}[{diagram_label(target)}]")
    return "\n".join(lines)


def extract_edges(content: str) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for line in content.splitlines():
        separator = "-->" if "-->" in line else "->" if "->" in line else "=>" if "=>" in line else ""
        if not separator:
            continue
        parts = [part.strip() for part in line.split(separator) if part.strip()]
        edges.extend(zip(parts, parts[1:]))
    return edges


def diagram_node_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    if not slug:
        slug = "node"
    if slug[0].isdigit():
        slug = f"n_{slug}"
    return slug[:40]


def diagram_label(value: str) -> str:
    return value.replace("[", "(").replace("]", ")")[:48]


def unique_block_id(title: str, index: int) -> str:
    slug = slugify(title)
    return f"{slug}-{index}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or DEFAULT_DOCUMENT_ID


def _looks_like_list_item(value: str) -> bool:
    return bool(re.match(r"^(\d+[.)]|[-*])\s+", value.strip()))


def _looks_like_markup(value: str) -> bool:
    return bool(re.search(r"<[^>]+>", value))


def _is_table_separator_row(row: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)
