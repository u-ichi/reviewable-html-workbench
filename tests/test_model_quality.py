from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.model_builder import build_model
from scripts.html_review_workbench.model_quality import check_model_quality


class ModelQualityTest(unittest.TestCase):
    def test_check_model_rejects_source_capture_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            model_path.write_text(json.dumps(build_model("raw input"), ensure_ascii=False), encoding="utf-8")

            result = check_model_quality(model_path)

            self.assertFalse(result.ok)
            self.assertIn("source-capture draft is not a final HTML document model", result.errors)

    def test_check_model_rejects_renderer_unsupported_types(self) -> None:
        result = check_model_quality(
            _write_model({"id": "table-block", "type": "table", "heading_level": 2, "content": "A | B"})
        )

        self.assertFalse(result.ok)
        self.assertIn("block table-block uses renderer-unsupported type: table", result.errors)

    def test_check_model_rejects_callout_html_content(self) -> None:
        result = check_model_quality(
            _write_model({"id": "callout", "type": "callout", "heading_level": 2, "content": "<strong>重要</strong>"})
        )

        self.assertFalse(result.ok)
        self.assertIn("callout block callout must use plain text content", result.errors)

    def test_check_model_rejects_html_without_structure(self) -> None:
        result = check_model_quality(
            _write_model({"id": "plain-html", "type": "html", "heading_level": 2, "content": "plain text"})
        )

        self.assertFalse(result.ok)
        self.assertIn("html block plain-html has no HTML structure", result.errors)

    def test_check_model_accepts_agent_designed_html_model(self) -> None:
        result = check_model_quality(
            _write_model(
                {
                    "id": "comparison",
                    "type": "html",
                    "heading_level": 2,
                    "content": "<table><tbody><tr><th>軸</th><td>値</td></tr></tbody></table>",
                }
            )
        )

        self.assertTrue(result.ok, result.errors)

    def test_check_model_accepts_mermaid_v11_diagram_prefixes(self) -> None:
        prefixes = [
            "flowchart",
            "graph",
            "sequenceDiagram",
            "stateDiagram",
            "classDiagram",
            "erDiagram",
            "gantt",
            "journey",
            "timeline",
            "mindmap",
            "quadrantChart",
            "C4Context",
            "pie",
            "gitGraph",
            "requirementDiagram",
            "sankey",
            "xychart",
            "architecture",
            "block",
            "packet",
            "kanban",
            "radar",
            "treemap",
            "zenuml",
        ]
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                result = check_model_quality(
                    _write_model(
                        {
                            "id": f"diagram-{prefix.lower()}",
                            "type": "diagram",
                            "heading_level": 2,
                            "content": f"{prefix}\n  A --> B",
                        }
                    )
                )
                self.assertTrue(result.ok, result.errors)
                self.assertEqual(result.warnings, [])


def _write_model(block: dict[str, object]) -> Path:
    tmp_dir = tempfile.TemporaryDirectory()
    path = Path(tmp_dir.name) / "model.json"
    payload = {
        "schema_version": "1.0",
        "document_id": "quality-test",
        "title": "Quality Test",
        "generated_at": "2026-05-17T00:00:00+09:00",
        "blocks": [block],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _TEMP_DIRS.append(tmp_dir)
    return path


_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []


if __name__ == "__main__":
    unittest.main()
