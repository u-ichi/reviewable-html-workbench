from __future__ import annotations

import json
import tempfile
import unittest
from html import escape
from pathlib import Path

from scripts.html_review_workbench.diagram_planner import plan_diagrams
from scripts.html_review_workbench.render import _render_toc, render_bundle
from scripts.html_review_workbench.validate_bundle import validate_bundle


ROOT = Path(__file__).resolve().parents[1]


class RendererBundleTest(unittest.TestCase):
    def test_render_bundle_creates_reviewable_html_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            index_path = render_bundle(ROOT / "tests/fixtures/minimal_document_model.json", output_dir)

            self.assertTrue(index_path.exists())
            html = index_path.read_text(encoding="utf-8")
            css = (output_dir / "assets/style.css").read_text(encoding="utf-8")
            self.assertIn('data-review-block="overview"', html)
            self.assertIn("assets/style.css", html)
            self.assertIn("assets/publish-export.js", html)
            self.assertIn("assets/review-comments.js", html)
            self.assertIn('<section class="review-block" id="overview"', html)
            self.assertNotIn("review-block-section", html)
            self.assertIn('<section class="summary">', html)
            self.assertIn('Smallest document model used to exercise renderer fixtures.', html)
            self.assertIn('<a href="#overview">Overview</a>', html)
            self.assertIn(".code-body", css)
            self.assertIn(".prose code:not(pre code)", css)
            self.assertIn("h1.doc-title", css)
            self.assertIn("word-break: keep-all", css)
            self.assertIn("overflow-wrap: break-word", css)
            self.assertIn("--code-ink:    #d7d3c8", css)
            self.assertIn("max-width: none", css)
            self.assertIn(".table-scroll { overflow-x: auto; }", css)
            self.assertIn("table.cmp { border-collapse: separate; border-spacing: 0; width: 100%;", css)
            self.assertIn("overflow-wrap: anywhere", css)

            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["document"]["id"], "minimal-design-doc")
            self.assertEqual(manifest["outputs"]["index"], "index.html")
            self.assertIn("assets/review-comments.js", manifest["outputs"]["assets"])
            self.assertIn("assets/publish-overrides.css", manifest["outputs"]["assets"])
            self.assertIn("assets/publish-export.js", manifest["outputs"]["assets"])
            self.assertEqual(manifest["review_blocks"][0]["id"], "document-header")
            self.assertEqual(manifest["review_blocks"][1]["id"], "overview")
            self.assertRegex(manifest["input"]["sha256"], r"^[0-9a-f]{64}$")

    def test_render_bundle_includes_publish_elements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            index_path = render_bundle(ROOT / "tests/fixtures/minimal_document_model.json", output_dir)

            html = index_path.read_text(encoding="utf-8")
            css = (output_dir / "assets/style.css").read_text(encoding="utf-8")

            for marker in [
                'id="publishToggle"',
                'id="pubDownloadBtn"',
                'id="pubExitBtn"',
            ]:
                self.assertIn(marker, html)
            self.assertTrue('id="pubExit"' in html or 'class="pub-exit"' in html)

            for marker in [".is-published", ".pub-exit", ".pub-toast"]:
                self.assertIn(marker, css)
            self.assertTrue((output_dir / "assets" / "publish-overrides.css").is_file())
            self.assertTrue((output_dir / "assets" / "publish-export.js").is_file())

    def test_render_toc_uses_block_titles(self) -> None:
        toc = _render_toc(
            [
                {"id": "overview", "title": "Overview", "heading_level": 3},
                {"id": "details", "title": "Details & Risks", "heading_level": 3},
                {"id": "untitled", "content": "No title", "heading_level": 3},
            ]
        )

        self.assertEqual(
            toc,
            '<ol>\n<li><a href="#overview">Overview</a></li>\n<li><a href="#details">Details &amp; Risks</a></li>\n</ol>',
        )

    def test_validate_bundle_checks_manifest_and_review_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            render_bundle(ROOT / "tests/fixtures/minimal_document_model.json", output_dir)

            result = validate_bundle(output_dir)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.review_blocks, 2)

    def test_render_bundle_saves_diagram_source_and_emits_mermaid_pre(self) -> None:
        source = "flowchart TD\n  A[Input] --> B[Output]"
        model = {
            "schema_version": "1.0",
            "document_id": "diagram-doc",
            "title": "Diagram Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "system-flow",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "System Flow",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            diagram_path = output_dir / "assets/diagrams/system-flow.mmd"
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))

            self.assertTrue(diagram_path.exists())
            self.assertEqual(diagram_path.read_text(encoding="utf-8").strip(), model["blocks"][0]["content"])
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn('data-role="reviewable-mermaid-init"', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertNotIn("DIAGRAM FALLBACK", html)
            self.assertNotIn('class="diagram-source"', html)
            self.assertTrue((output_dir / "assets" / "mermaid.min.js").is_file())
            self.assertIn("assets/mermaid.min.js", manifest["outputs"]["assets"])
            self.assertEqual(manifest["outputs"]["diagrams"], ["assets/diagrams/system-flow.mmd"])
            self.assertEqual(manifest["review_blocks"][1]["diagram_kind"], "flow")
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_render_bundle_state_diagram_emits_mermaid_pre(self) -> None:
        source = "stateDiagram-v2\n  [*] --> Idle\n  Idle --> Processing : start\n  Processing --> Done : finish\n  Done --> [*]"
        model = {
            "schema_version": "1.0",
            "document_id": "state-doc",
            "title": "State Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "lifecycle",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "Lifecycle",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertNotIn("state-diagram", html)
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_render_bundle_uses_updated_callout_markup(self) -> None:
        model = {
            "schema_version": "1.0",
            "document_id": "callout-doc",
            "title": "Callout Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "callout",
                    "type": "callout",
                    "heading_level": 2,
                    "title": "Note",
                    "content": "Use <plain> text.",
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<div class="callout info" role="doc-note">', html)
            self.assertIn('<div class="co-ico">i</div>', html)
            self.assertIn('<div><div class="co-body"><p>Use &lt;plain&gt; text.</p></div></div>', html)

    def test_render_bundle_uses_generated_image_for_diagram_when_available(self) -> None:
        model = {
            "schema_version": "1.0",
            "document_id": "diagram-image-doc",
            "title": "Diagram Image Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "system-flow",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "System Flow",
                    "content": "flowchart TD\n  A[Input] --> B[Output]",
                    "diagram_source": "flowchart TD\n  A[Input] --> B[Output]",
                    "image": {
                        "prompt": "Generate a clean business diagram.",
                        "alt": "System Flow diagram",
                        "caption": "System Flow",
                        "generation_status": "generated",
                        "source_path": "generated-diagram.png",
                    },
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            output_dir = tmp_dir / "bundle"
            model_path = tmp_dir / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            (tmp_dir / "generated-diagram.png").write_bytes(_minimal_png_bytes())

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))

            self.assertIn('<figure class="figure generated-image">', html)
            self.assertIn('src="assets/images/generated-diagram.png"', html)
            self.assertNotIn("diagram-preview", html)
            self.assertEqual(manifest["outputs"]["diagrams"], ["assets/diagrams/system-flow.mmd"])
            self.assertEqual(manifest["outputs"]["images"], ["assets/images/generated-diagram.png"])
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_plan_diagrams_classifies_supported_kinds(self) -> None:
        blocks = [
            {"id": "flow", "type": "diagram", "content": "flowchart LR\nA-->B"},
            {"id": "seq", "type": "diagram", "content": "sequenceDiagram\n  A->>B: Hello"},
            {"id": "arch", "type": "diagram", "content": "C4Context\nPerson(user, User)"},
            {"id": "er", "type": "diagram", "content": "erDiagram\n  USER ||--o{ ORDER : places"},
            {"id": "matrix", "type": "diagram", "content": "quadrantChart\nx-axis Low --> High"},
            {"id": "timeline", "type": "diagram", "content": "gantt\ndateFormat YYYY-MM-DD"},
            {"id": "concept", "type": "diagram", "content": "mindmap\n  root"},
            {"id": "state", "type": "diagram", "content": "stateDiagram-v2\n  Idle --> Active"},
        ]

        plans = plan_diagrams(blocks)

        self.assertEqual(plans["flow"].kind, "flow")
        self.assertEqual(plans["seq"].kind, "sequence")
        self.assertEqual(plans["arch"].kind, "architecture")
        self.assertEqual(plans["er"].kind, "er")
        self.assertEqual(plans["matrix"].kind, "matrix")
        self.assertEqual(plans["timeline"].kind, "timeline")
        self.assertEqual(plans["concept"].kind, "concept")
        self.assertEqual(plans["state"].kind, "state")

    def test_render_bundle_sequence_diagram_emits_mermaid_pre(self) -> None:
        source = "sequenceDiagram\n  participant C as Client\n  participant S as Server\n  C->>S: Login\n  S-->>C: Token"
        model = {
            "schema_version": "1.0",
            "document_id": "seq-doc",
            "title": "Seq Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "auth-flow",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "Auth Flow",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertNotIn("seq-diagram", html)
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_render_bundle_architecture_diagram_emits_mermaid_pre(self) -> None:
        source = "classDiagram\n  class User\n  class Order\n  User --> Order"
        model = {
            "schema_version": "1.0",
            "document_id": "arch-doc",
            "title": "Arch Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "er-model",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "Class Model",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertNotIn("arch-diagram", html)
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_plan_diagrams_classifies_erdiagram_as_er(self) -> None:
        plans = plan_diagrams(
            [
                {
                    "id": "er-model",
                    "type": "diagram",
                    "content": "erDiagram\n  CUSTOMER ||--o{ ORDER : places",
                }
            ]
        )

        self.assertEqual(plans["er-model"].kind, "er")

    def test_render_bundle_er_emits_mermaid_pre(self) -> None:
        model = _er_model()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">erDiagram', html)
            self.assertIn("CUSTOMER ||--o{ ORDER : places", html)
            self.assertIn("string customer_id FK", html)
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_render_bundle_includes_mermaid_asset(self) -> None:
        model = _er_model()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertIn('src="assets/mermaid.min.js?', html)
            self.assertIn("mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})", html)
            self.assertTrue((output_dir / "assets" / "mermaid.min.js").is_file())
            self.assertIn("assets/mermaid.min.js", manifest["outputs"]["assets"])

    def test_render_bundle_skips_mermaid_asset_when_no_diagram(self) -> None:
        model = {
            "schema_version": "1.0",
            "document_id": "plain-doc",
            "title": "Plain Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "plain",
                    "type": "html",
                    "heading_level": 2,
                    "title": "Plain",
                    "content": "<p>No ER diagram</p>",
                    "review_required": False,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("mermaid.min.js", html)
            self.assertFalse((output_dir / "assets" / "mermaid.min.js").exists())
            self.assertNotIn("assets/mermaid.min.js", manifest["outputs"]["assets"])

    def test_render_bundle_er_skips_diagram_fallback_wrapper(self) -> None:
        model = _er_model()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertNotIn('data-diagram-kind="er"', html)
            self.assertNotIn("DIAGRAM FALLBACK", html)
            self.assertNotIn('class="diagram-source"', html)

    def test_render_bundle_timeline_diagram_emits_mermaid_pre(self) -> None:
        source = "gantt\n  dateFormat YYYY-MM-DD\n  section Phase1\n  Design : 2026-01-01, 30d\n  section Phase2\n  Develop : 2026-02-01, 60d"
        model = {
            "schema_version": "1.0",
            "document_id": "tl-doc",
            "title": "Timeline Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "project-plan",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "Project Plan",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertNotIn("tl-diagram", html)
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_render_bundle_matrix_diagram_emits_mermaid_pre(self) -> None:
        source = "quadrantChart\n  title Priority\n  x-axis Low --> High\n  y-axis Low --> High\n  Alpha: [0.8, 0.9]\n  Beta: [0.2, 0.3]"
        model = {
            "schema_version": "1.0",
            "document_id": "mx-doc",
            "title": "Matrix Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "priority-matrix",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "Priority Matrix",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertNotIn("mx-diagram", html)
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_render_bundle_concept_diagram_emits_mermaid_pre(self) -> None:
        source = "mindmap\n  root((Workbench))\n    Render\n    Review"
        model = {
            "schema_version": "1.0",
            "document_id": "concept-doc",
            "title": "Concept Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "concept-map",
                    "type": "diagram",
                    "heading_level": 2,
                    "title": "Concept Map",
                    "content": source,
                    "review_required": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "bundle"
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', html)
            self.assertIn(escape(source), html)
            self.assertNotIn("diagram-fallback", html)
            self.assertTrue(validate_bundle(output_dir).ok)


def _minimal_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe"
        b"\xdc\xccY\xe7"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _er_model() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "document_id": "er-doc",
        "title": "ER Doc",
        "generated_at": "2026-05-17T00:00:00+09:00",
        "blocks": [
            {
                "id": "customer-order",
                "type": "diagram",
                "heading_level": 2,
                "title": "Customer Order ER",
                "content": (
                    "erDiagram\n"
                    "  CUSTOMER ||--o{ ORDER : places\n"
                    "  ORDER }o..o| INVOICE : bills\n"
                    "  CUSTOMER {\n"
                    "    string id PK\n"
                    "    string name\n"
                    "  }\n"
                    "  ORDER {\n"
                    "    string id PK\n"
                    "    string customer_id FK\n"
                    "  }\n"
                    "  INVOICE {\n"
                    "    string id PK\n"
                    "    string order_id FK\n"
                    "  }\n"
                ),
                "review_required": True,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
