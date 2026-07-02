"""publish_bundle のテスト。外部依存なし（stdlib のみ）。"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.publish import PublishError, publish_bundle

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"


def _create_minimal_bundle(bundle_dir: Path) -> None:
    """render 済みバンドルの最小構成を作成する。"""
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    css_src = TEMPLATE_DIR / "style.css"
    shutil.copyfile(css_src, assets_dir / "style.css")

    html = (
        '<!doctype html>\n'
        '<html lang="ja" data-theme="light" data-density="compact">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>Test</title>\n"
        '  <link rel="stylesheet" href="assets/style.css?v=test">\n'
        "</head>\n"
        "<body>\n"
        '  <div class="app" data-document-id="test-doc">\n'
        '    <header class="topbar">\n'
        '      <div class="toolset">\n'
        '        <select id="filterSelect"><option value="all">All</option></select>\n'
        '        <button id="focusToggle" type="button">Focus</button>\n'
        '        <button id="publishToggle" type="button">Publish</button>\n'
        '        <button id="themeToggle" type="button">Theme</button>\n'
        "      </div>\n"
        "    </header>\n"
        '    <main class="canvas" id="canvas">\n'
        '      <div class="doc-shell">\n'
        '        <div class="doc-grid">\n'
        '          <nav class="toc"><p class="toc-h">Contents</p></nav>\n'
        '          <article class="doc-main">\n'
        '            <div class="paper">\n'
        '              <header class="doc-headrow document-header"'
        ' data-review-block="document-header"'
        ' data-block-type="header" data-review-required="false">\n'
        '                <h1 class="doc-title">Test Document</h1>\n'
        '                <span class="doc-status draft">Draft</span>\n'
        "              </header>\n"
        '              <div class="byline">'
        '<span class="byline-agent">Agent: test</span></div>\n'
        '              <div class="prose document-content" id="content">\n'
        '                <section data-review-block="block-1" data-block-type="html"'
        ' data-review-required="true">\n'
        "                  <h2>Section 1</h2>\n"
        "                  <p>Hello world</p>\n"
        "                </section>\n"
        "              </div>\n"
        "            </div>\n"
        "          </article>\n"
        '          <aside class="cmt-rail">\n'
        '            <div class="cmt-rail-h"><span>Comments</span></div>\n'
        '            <div class="cmt-layer" id="cmtLayer"></div>\n'
        "          </aside>\n"
        "        </div>\n"
        "      </div>\n"
        "    </main>\n"
        '    <div class="pub-exit" id="pubExit" role="status">\n'
        "      <span>Publish mode</span>\n"
        "    </div>\n"
        "  </div>\n"
        '  <script src="assets/review-comments.js?v=test"></script>\n'
        "</body>\n"
        "</html>\n"
    )
    (bundle_dir / "index.html").write_text(html, encoding="utf-8")


class TestPublishBundleErrors(unittest.TestCase):
    def test_missing_index_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "empty"
            root.mkdir()
            output = Path(tmpdir) / "out"
            with self.assertRaises(PublishError):
                publish_bundle(root, output)

    def test_missing_style_css(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "no-css"
            root.mkdir()
            (root / "index.html").write_text("<html></html>")
            output = Path(tmpdir) / "out"
            with self.assertRaises(PublishError):
                publish_bundle(root, output)


class TestPublishBundle(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.bundle_dir = Path(self._tmpdir) / "bundle"
        self.output_dir = Path(self._tmpdir) / "published"
        _create_minimal_bundle(self.bundle_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_publish_produces_standalone_html(self) -> None:
        result = publish_bundle(self.bundle_dir, self.output_dir)
        self.assertEqual(result["status"], "ok")

        output_html = self.output_dir / "index.html"
        self.assertTrue(output_html.is_file())
        content = output_html.read_text(encoding="utf-8")

        body_start = content.find("<body")
        self.assertGreater(body_start, 0)
        body_content = content[body_start:]

        # レビュー UI の DOM 要素が除去されていること
        self.assertNotIn('class="cmt-rail"', body_content)
        self.assertNotIn('class="pub-exit"', body_content)
        self.assertNotIn("focusToggle", body_content)
        self.assertNotIn("filterSelect", body_content)
        self.assertNotIn("data-review-block", body_content)
        self.assertNotIn("data-review-required", body_content)
        self.assertNotIn("data-block-type", body_content)

        # レビュー専用要素が除去されていること
        self.assertNotIn('class="byline"', body_content)
        self.assertNotIn('class="doc-status', body_content)

        # コンテンツが保持されていること
        self.assertIn("Section 1", body_content)
        self.assertIn("Hello world", body_content)

        # CSS がインライン化されていること
        self.assertIn("<style>", content)
        self.assertNotIn('<link rel="stylesheet"', content)

        # script タグがないこと
        self.assertNotIn("<script", body_content)

    def test_output_is_single_file(self) -> None:
        publish_bundle(self.bundle_dir, self.output_dir)
        files = list(self.output_dir.iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "index.html")

    def test_meta_tags(self) -> None:
        publish_bundle(self.bundle_dir, self.output_dir)
        content = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn('<title>Test Document</title>', content)
        self.assertIn('og:title', content)
        self.assertIn('data-density="compact"', content)
        self.assertIn('lang="ja"', content)

    def test_dark_mode_overrides(self) -> None:
        publish_bundle(self.bundle_dir, self.output_dir)
        content = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("prefers-color-scheme:dark", content)

    def test_published_body_class(self) -> None:
        publish_bundle(self.bundle_dir, self.output_dir)
        content = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="is-published"', content)

    def test_publish_inlines_mermaid_script(self) -> None:
        mermaid_asset = self.bundle_dir / "assets" / "mermaid.min.js"
        zoom_asset = self.bundle_dir / "assets" / "diagram-zoom.js"
        mermaid_asset.write_text("/*! Mermaid test */\nwindow.mermaid = { initialize() {} };\n", encoding="utf-8")
        zoom_asset.write_text("/*! Diagram zoom test */\nwindow.initDiagramZoom = function() {};\n", encoding="utf-8")
        index_path = self.bundle_dir / "index.html"
        html = index_path.read_text(encoding="utf-8")
        html = html.replace(
            '  <link rel="stylesheet" href="assets/style.css?v=test">\n',
            '  <link rel="stylesheet" href="assets/style.css?v=test">\n'
            '  <script src="assets/mermaid.min.js?v=test"></script>\n'
            "  <script>mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})</script>\n"
            '  <script src="assets/diagram-zoom.js?v=test" defer></script>\n',
        )
        html = html.replace(
            "                  <p>Hello world</p>\n",
            '                  <pre class="mermaid">erDiagram\n'
            "  CUSTOMER ||--o{ ORDER : places</pre>\n",
        )
        index_path.write_text(html, encoding="utf-8")

        publish_bundle(self.bundle_dir, self.output_dir)

        content = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("/*! Mermaid test */", content)
        self.assertIn("/*! Diagram zoom test */", content)
        self.assertIn("mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})", content)
        self.assertIn('<pre class="mermaid">erDiagram', content)
        self.assertNotIn('<script src="assets/mermaid.min.js', content)
        self.assertNotIn('<script src="assets/diagram-zoom.js', content)

    def test_publish_does_not_inline_diagram_zoom_without_mermaid(self) -> None:
        zoom_asset = self.bundle_dir / "assets" / "diagram-zoom.js"
        zoom_asset.write_text("/*! Diagram zoom test */\nwindow.initDiagramZoom = function() {};\n", encoding="utf-8")

        publish_bundle(self.bundle_dir, self.output_dir)

        content = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("/*! Diagram zoom test */", content)


if __name__ == "__main__":
    unittest.main()
