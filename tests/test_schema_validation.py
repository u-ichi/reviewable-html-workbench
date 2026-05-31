from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.html_review_workbench.schema_validation import validate


ROOT = Path(__file__).resolve().parents[1]


class SchemaValidationTest(unittest.TestCase):
    def test_minimal_fixtures_match_schemas(self) -> None:
        cases = [
            ("schemas/document-model.schema.json", "tests/fixtures/minimal_document_model.json"),
            ("schemas/comments.schema.json", "tests/fixtures/minimal_comments.json"),
            ("schemas/preview-session.schema.json", "tests/fixtures/minimal_preview_session.json"),
        ]
        for schema_path, fixture_path in cases:
            with self.subTest(schema=schema_path):
                schema = _read_json(ROOT / schema_path)
                fixture = _read_json(ROOT / fixture_path)
                errors = validate(fixture, schema)
                self.assertEqual(errors, [])

    def test_missing_required_field_is_reported(self) -> None:
        schema = _read_json(ROOT / "schemas/document-model.schema.json")
        fixture = _read_json(ROOT / "tests/fixtures/minimal_document_model.json")
        del fixture["document_id"]

        errors = validate(fixture, schema)

        self.assertIn("$.document_id", {error.path for error in errors})

    def test_comment_status_is_limited_to_contract_values(self) -> None:
        schema = _read_json(ROOT / "schemas/comments.schema.json")
        fixture = _read_json(ROOT / "tests/fixtures/minimal_comments.json")
        fixture["comments"][0]["status"] = "waiting"

        errors = validate(fixture, schema)

        self.assertIn("$.comments[0].status", {error.path for error in errors})

    def test_preview_session_rejects_wildcard_bind(self) -> None:
        schema = _read_json(ROOT / "schemas/preview-session.schema.json")
        fixture = _read_json(ROOT / "tests/fixtures/minimal_preview_session.json")
        fixture["bind"] = "0.0.0.0"

        errors = validate(fixture, schema)

        self.assertIn("$.bind", {error.path for error in errors})

    def test_numeric_bounds_validate_without_runtime_type_errors(self) -> None:
        schema = {"type": "object", "properties": {"start": {"type": "integer", "minimum": 0}}}

        errors = validate({"start": 2}, schema)

        self.assertEqual(errors, [])


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
