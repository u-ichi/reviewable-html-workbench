from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.render import render_bundle

DIAGRAM_ZOOM_JS = Path(__file__).resolve().parents[1] / "templates" / "assets" / "diagram-zoom.js"


def _diagram_model() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "document_id": "zoom-doc",
        "title": "Zoom Doc",
        "generated_at": "2026-05-17T00:00:00+09:00",
        "blocks": [
            {
                "id": "customer-order",
                "type": "diagram",
                "heading_level": 2,
                "title": "Customer Order",
                "content": "erDiagram\n  CUSTOMER ||--o{ ORDER : places",
                "review_required": True,
            }
        ],
    }


def _generated_image_diagram_model() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "document_id": "generated-diagram-doc",
        "title": "Generated Diagram Doc",
        "generated_at": "2026-05-17T00:00:00+09:00",
        "blocks": [
            {
                "id": "generated-flow",
                "type": "diagram",
                "heading_level": 2,
                "title": "Generated Flow",
                "content": "flowchart TD\n  A --> B",
                "image": {
                    "prompt": "Generate a flow diagram.",
                    "alt": "Generated flow diagram",
                    "caption": "Generated Flow",
                    "generation_status": "generated",
                    "source_path": "generated-flow.png",
                },
                "review_required": True,
            }
        ],
    }


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


class RenderDiagramZoomTest(unittest.TestCase):
    def test_rendered_mermaid_diagram_gets_zoom_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "bundle"
            model_path = root / "model.json"
            model_path.write_text(json.dumps(_diagram_model()), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<figure class="diagram-wrap">', html)
            self.assertIn('class="diagram-zoom-btn"', html)
            self.assertIn('<pre class="mermaid">erDiagram', html)

    def test_rendered_mermaid_diagram_copies_zoom_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "bundle"
            model_path = root / "model.json"
            model_path.write_text(json.dumps(_diagram_model()), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertIn('src="assets/diagram-zoom.js?', html)
            self.assertTrue((output_dir / "assets" / "diagram-zoom.js").is_file())
            self.assertIn("assets/diagram-zoom.js", manifest["outputs"]["assets"])

    def test_generated_image_diagram_does_not_copy_zoom_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "bundle"
            model_path = root / "model.json"
            model_path.write_text(json.dumps(_generated_image_diagram_model()), encoding="utf-8")
            (root / "generated-flow.png").write_bytes(_minimal_png_bytes())

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn('<figure class="diagram-wrap">', html)
            self.assertNotIn("diagram-zoom.js", html)
            self.assertFalse((output_dir / "assets" / "diagram-zoom.js").exists())
            self.assertNotIn("assets/diagram-zoom.js", manifest["outputs"]["assets"])

    def test_diagram_zoom_sets_absolute_svg_size_and_restores_attributes(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("sourceSvg.viewBox?.baseVal", script)
        self.assertIn('sourceSvg.setAttribute("width", String(svgBox.width))', script)
        self.assertIn('sourceSvg.setAttribute("height", String(svgBox.height))', script)
        self.assertIn('restoreAttribute(sourceSvg, "width", originalSvgAttrs.width)', script)
        self.assertIn('restoreAttribute(sourceSvg, "height", originalSvgAttrs.height)', script)
        self.assertIn("node.removeAttribute(name)", script)
        self.assertIn("node.setAttribute(name, value)", script)

    def test_diagram_zoom_overlay_capture_does_not_block_drag_handlers(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertNotIn('overlay.addEventListener("pointerup", stopGlobalEvent, true)', script)
        self.assertNotIn('overlay.addEventListener("mousedown", stopGlobalEvent, true)', script)
        self.assertIn('viewport.addEventListener("pointerleave", cancelDrag)', script)

    def test_diagram_zoom_distinguishes_click_drag_pan_and_zoom(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn('if (activeDragType) {', script)
        self.assertIn("if (!dragging && Math.abs(dx) + Math.abs(dy) <= 2)", script)
        self.assertIn("dragging = true;", script)
        self.assertIn("suppressNextClick = event.target !== viewport && event.target !== overlay", script)
        self.assertIn("panBy(event.deltaX, event.deltaY)", script)
        self.assertIn("if (event.ctrlKey || event.metaKey)", script)


if __name__ == "__main__":
    unittest.main()
