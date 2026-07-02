"""render 済み HTML バンドルからレビュー UI を除去した公開用 standalone HTML を生成する。

renderer が出力する HTML は構造が既知のため、stdlib の文字列操作と regex で
レビュー要素を除去し、CSS インライン化・画像 embed 済みの単一 HTML を出力する。
外部依存なし（Python stdlib のみ）。
"""

from __future__ import annotations

import base64
import mimetypes
import re
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIAGRAM_ZOOM_JS_PATH = ROOT / "templates" / "assets" / "diagram-zoom.js"

_DARK_OVERRIDES = (
    "@media(prefers-color-scheme:dark){:root{"
    "--bg-app:#131519;--bg-rail:#171a1f;--paper:#1c1f24;--paper-2:#20242a;"
    "--ink:#e7e3da;--ink-2:#a6a299;--ink-3:#7d7a72;--ink-faint:#5b5851;"
    "--line-1:#2c2f35;--line-2:#393d44;--line-3:#4a4e56;"
    "--brand:#6ea4dc;--brand-soft:#1f2d3c;"
    "--open:#6ea4dc;--open-bg:#1c2c3b;--open-line:#355472;"
    "--reply:#d6a85a;--reply-bg:#352c18;--reply-line:#604c25;"
    "--resolved:#6dba88;--resolved-bg:#1c2e23;--resolved-line:#345240;"
    "--code-bg:#15181d;--code-bg-2:#1b1f25;--code-line:#262b32;"
    "--sh-1:0 1px 2px rgba(0,0,0,.4),0 0 0 1px rgba(255,255,255,.04);"
    "--sh-2:0 2px 8px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.05);"
    "--sh-3:0 10px 30px rgba(0,0,0,.6),0 2px 6px rgba(0,0,0,.4);"
    "--focus-ring:0 0 0 3px color-mix(in srgb,var(--brand) 40%,transparent);"
    "}}"
)

_PUBLISH_OVERRIDES = (
    "html,body{background:var(--bg-app);}\n"
    ".canvas{overflow:visible;height:auto;min-height:100vh;}\n"
)


class PublishError(Exception):
    pass


def publish_bundle(root: Path, output: Path) -> dict[str, Any]:
    """render 済みバンドルから公開用 standalone HTML を生成する。

    renderer 出力の index.html から article 部分を抽出し、レビュー UI を除去、
    CSS をインライン化、画像を base64 data URI に変換して単一 HTML を出力する。

    Args:
        root: render 済みバンドルのディレクトリ（index.html を含む）
        output: 出力先ディレクトリ

    Returns:
        {"status": "ok", "output": "<path>"} 形式の dict

    Raises:
        PublishError: バンドルが不正な場合
    """
    index_path = root / "index.html"
    style_path = root / "assets" / "style.css"

    if not index_path.is_file():
        raise PublishError(f"index.html not found in {root}")
    if not style_path.is_file():
        raise PublishError(f"assets/style.css not found in {root}")

    source_html = index_path.read_text(encoding="utf-8")
    css = style_path.read_text(encoding="utf-8")

    lang = _extract_attr(source_html, r'<html[^>]*\blang="([^"]*)"') or "ja"
    density = _extract_attr(source_html, r'data-density="([^"]*)"') or "compact"

    canvas_match = re.search(r'<main[^>]*class="canvas([^"]*)"', source_html)
    is_focus = bool(canvas_match and "is-focus" in canvas_match.group(1))

    article = _extract_article(source_html)
    article = _strip_review_attrs(article)
    article = _strip_review_elements(article)
    article = _embed_images(article, root)
    mermaid_script = _inline_mermaid_script(source_html, article, root)

    title = _extract_text(article, r'<h1 class="doc-title">(.*?)</h1>') or "document"
    description = _extract_description(article)

    html = _assemble(
        lang=lang,
        density=density,
        title=title,
        description=description,
        css=css,
        article=article,
        is_focus=is_focus,
        mermaid_script=mermaid_script,
    )

    output.mkdir(parents=True, exist_ok=True)
    output_path = output / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return {"status": "ok", "output": str(output_path)}


def _extract_attr(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html)
    return m.group(1) if m else None


def _extract_article(html: str) -> str:
    """<article class="doc-main">...</article> を抽出する。"""
    start_marker = '<article class="doc-main">'
    start = html.find(start_marker)
    if start == -1:
        raise PublishError("article.doc-main not found in index.html")
    end = html.find("</article>", start)
    if end == -1:
        raise PublishError("closing </article> not found")
    return html[start : end + len("</article>")]


def _strip_review_attrs(html: str) -> str:
    """レビュー用 data 属性を除去する。"""
    for attr in ("data-review-block", "data-review-required", "data-block-type"):
        html = re.sub(rf'\s+{attr}="[^"]*"', "", html)
    return html


def _strip_review_elements(html: str) -> str:
    """レビュー専用の DOM 要素を除去する。

    byline: <div class="byline">...(span のみ)...</div>
    doc-status: <span class="doc-status ...">...</span>
    """
    html = re.sub(
        r'<div class="byline">.*?</div>', "", html, flags=re.DOTALL
    )
    html = re.sub(
        r'<span class="doc-status[^"]*">.*?</span>', "", html, flags=re.DOTALL
    )
    return html


def _embed_images(html: str, root: Path) -> str:
    """<img src="..."> の画像をファイルから読み取り base64 data URI に変換する。"""

    def _replace(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.startswith("data:"):
            return match.group(0)
        img_path = root / src
        if not img_path.is_file():
            return match.group(0)
        mime, _ = mimetypes.guess_type(str(img_path))
        if not mime:
            mime = "application/octet-stream"
        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{data}"'

    return re.sub(r'src="([^"]*)"', _replace, html)


def _inline_mermaid_script(source_html: str, article: str, root: Path) -> str:
    """Mermaid 図 bundle の Mermaid / zoom asset を standalone HTML に inline 化する。"""
    needs_mermaid = "assets/mermaid.min.js" in source_html or 'class="mermaid"' in article
    if not needs_mermaid:
        return ""
    mermaid_path = root / "assets" / "mermaid.min.js"
    zoom_path = root / "assets" / "diagram-zoom.js"
    if not mermaid_path.is_file():
        raise PublishError(f"assets/mermaid.min.js not found in {root}")
    if not zoom_path.is_file():
        zoom_path = DIAGRAM_ZOOM_JS_PATH
    if not zoom_path.is_file():
        raise PublishError(f"assets/diagram-zoom.js not found in {root}")
    script = mermaid_path.read_text(encoding="utf-8")
    zoom_script = zoom_path.read_text(encoding="utf-8")
    return (
        f"<script>\n{script}\n</script>\n"
        "<script>mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})</script>\n"
        f"<script>\n{zoom_script}\n</script>\n"
    )


def _extract_text(html: str, pattern: str) -> str:
    """regex でマッチしたタグの text content を返す。"""
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def _extract_description(article: str) -> str:
    """OG description 用のテキストを抽出する（最大 200 文字）。"""
    for pattern in [
        r'<section class="summary">.*?<p>(.*?)</p>',
        r'<div class="block-content"[^>]*>.*?<p[^>]*>(.*?)</p>',
    ]:
        text = _extract_text(article, pattern)
        if text:
            return text[:200]
    return ""


def _assemble(
    *,
    lang: str,
    density: str,
    title: str,
    description: str,
    css: str,
    article: str,
    is_focus: bool,
    mermaid_script: str = "",
) -> str:
    """公開用 standalone HTML を組み立てる。"""
    esc_title = escape(title)
    esc_desc = escape(description)
    focus_class = " is-focus" if is_focus else ""

    return (
        f'<!DOCTYPE html>\n<html lang="{escape(lang)}" data-density="{escape(density)}">\n'
        f"<head>\n<meta charset=\"utf-8\">\n"
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc_title}</title>\n"
        f'<meta property="og:title" content="{esc_title}">\n'
        f'<meta property="og:description" content="{esc_desc}">\n'
        f'<meta property="og:type" content="article">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{esc_title}">\n'
        f'<meta name="twitter:description" content="{esc_desc}">\n'
        f"<style>\n{css}\n"
        f"/* published export overrides */\n"
        f"{_PUBLISH_OVERRIDES}"
        f"{_DARK_OVERRIDES}\n"
        f"</style>\n"
        f"{mermaid_script}"
        f"</head>\n"
        f'<body class="is-published">\n'
        f'<main class="canvas{focus_class}">\n'
        f'<div class="doc-shell">\n<div class="doc-grid">\n'
        f"{article}\n"
        f"</div>\n</div>\n"
        f"</main>\n</body>\n</html>\n"
    )
