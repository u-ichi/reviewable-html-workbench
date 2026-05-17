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
            self.assertIn('data-review-block="overview"', html)
            self.assertIn("assets/style.css", html)
            self.assertIn("assets/review-comments.js", html)

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
            self.assertIn("assets/diagrams/system-flow.mmd", html)
            self.assertEqual(manifest["outputs"]["diagrams"], ["assets/diagrams/system-flow.mmd"])
            self.assertEqual(manifest["review_blocks"][1]["diagram_kind"], "flow")
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


if __name__ == "__main__":
    unittest.main()
