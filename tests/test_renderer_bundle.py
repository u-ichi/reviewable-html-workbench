from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.diagram_planner import plan_diagrams
from scripts.html_review_workbench.render import render_bundle
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
            self.assertIn("assets/review-comments.js", html)
            self.assertIn(".block-content pre code", css)
            self.assertIn("color: #f8fafc", css)
            self.assertIn("max-width: none", css)
            self.assertIn("table-layout: fixed", css)
            self.assertIn("overflow-wrap: anywhere", css)

            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["document"]["id"], "minimal-design-doc")
            self.assertEqual(manifest["outputs"]["index"], "index.html")
            self.assertIn("assets/review-comments.js", manifest["outputs"]["assets"])
            self.assertEqual(manifest["review_blocks"][0]["id"], "document-header")
            self.assertEqual(manifest["review_blocks"][1]["id"], "overview")
            self.assertRegex(manifest["input"]["sha256"], r"^[0-9a-f]{64}$")

    def test_validate_bundle_checks_manifest_and_review_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            render_bundle(ROOT / "tests/fixtures/minimal_document_model.json", output_dir)

            result = validate_bundle(output_dir)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.review_blocks, 2)

    def test_render_bundle_saves_diagram_source_and_fallback(self) -> None:
        model = {
            "schema_version": "1.0",
            "document_id": "diagram-doc",
            "title": "Diagram Doc",
            "generated_at": "2026-05-17T00:00:00+09:00",
            "blocks": [
                {
                    "id": "system-flow",
                    "type": "diagram",
                    "title": "System Flow",
                    "content": "flowchart TD\n  A[Input] --> B[Output]",
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
            self.assertIn('data-diagram-kind="flow"', html)
            self.assertIn("diagram-preview", html)
            self.assertIn("assets/diagrams/system-flow.mmd", html)
            self.assertEqual(manifest["outputs"]["diagrams"], ["assets/diagrams/system-flow.mmd"])
            self.assertEqual(manifest["review_blocks"][1]["diagram_kind"], "flow")
            self.assertTrue(validate_bundle(output_dir).ok)

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

            self.assertIn('<figure class="block-content generated-image">', html)
            self.assertIn('src="assets/images/generated-diagram.png"', html)
            self.assertNotIn("diagram-preview", html)
            self.assertEqual(manifest["outputs"]["diagrams"], ["assets/diagrams/system-flow.mmd"])
            self.assertEqual(manifest["outputs"]["images"], ["assets/images/generated-diagram.png"])
            self.assertTrue(validate_bundle(output_dir).ok)

    def test_plan_diagrams_classifies_supported_kinds(self) -> None:
        blocks = [
            {"id": "flow", "type": "diagram", "content": "flowchart LR\nA-->B"},
            {"id": "arch", "type": "diagram", "content": "C4Context\nPerson(user, User)"},
            {"id": "matrix", "type": "diagram", "content": "quadrantChart\nx-axis Low --> High"},
            {"id": "timeline", "type": "diagram", "content": "gantt\ndateFormat YYYY-MM-DD"},
            {"id": "concept", "type": "diagram", "content": "mindmap\n  root"},
        ]

        plans = plan_diagrams(blocks)

        self.assertEqual(plans["flow"].kind, "flow")
        self.assertEqual(plans["arch"].kind, "architecture")
        self.assertEqual(plans["matrix"].kind, "matrix")
        self.assertEqual(plans["timeline"].kind, "timeline")
        self.assertEqual(plans["concept"].kind, "concept")


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


if __name__ == "__main__":
    unittest.main()
