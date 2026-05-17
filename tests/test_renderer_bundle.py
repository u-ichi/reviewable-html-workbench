from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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

            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["document"]["id"], "minimal-design-doc")
            self.assertEqual(manifest["outputs"]["index"], "index.html")
            self.assertEqual(manifest["review_blocks"][0]["id"], "overview")
            self.assertRegex(manifest["input"]["sha256"], r"^[0-9a-f]{64}$")

    def test_validate_bundle_checks_manifest_and_review_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            render_bundle(ROOT / "tests/fixtures/minimal_document_model.json", output_dir)

            result = validate_bundle(output_dir)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.review_blocks, 1)


if __name__ == "__main__":
    unittest.main()
