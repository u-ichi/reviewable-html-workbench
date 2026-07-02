from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.common import (
    MERMAID_INIT_JS,
    pid_is_alive,
    resolve_bundle_json_path,
    unique_path,
    write_json,
)


class CommonHelpersTest(unittest.TestCase):
    # write_json call-site mkdir behavior:
    # mkdirあり: comment_store.py:44-48, model_builder.py:39-40,
    # ingest_review.py:134-135, image_assets.py:53-54,
    # preview_server.py:244-246, plan_preview.py:427-435
    # mkdirなし: render.py:105-108, ingest_review.py:274-276,
    # plan_preview.py:96-104

    def test_write_json_preserves_default_no_parent_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "payload.json"

            with self.assertRaises(FileNotFoundError):
                write_json(path, {"status": "ok"})

    def test_write_json_can_create_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "payload.json"

            write_json(path, {"status": "ok"}, ensure_parent=True)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"status": "ok"})

    def test_write_json_can_preserve_compact_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"

            write_json(path, {"status": "ok"}, indent=None)

            self.assertEqual(path.read_text(encoding="utf-8"), '{"status": "ok"}\n')

    def test_unique_path_chooses_numbered_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset.png"
            path.write_text("one", encoding="utf-8")

            result = unique_path(path, on_exhausted=lambda p: ValueError(f"exhausted: {p}"))

            self.assertEqual(result.name, "asset-2.png")

    def test_resolve_bundle_json_path_preserves_label_in_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "state path must be relative"):
                resolve_bundle_json_path(root, str(root / "state.json"), label="state", error=ValueError)
            with self.assertRaisesRegex(ValueError, "comments path must be a JSON file"):
                resolve_bundle_json_path(root, "comments.txt", label="comments", error=ValueError)

    def test_pid_is_alive_accepts_current_process(self) -> None:
        self.assertTrue(pid_is_alive(os.getpid()))

    def test_mermaid_init_js_matches_existing_inline_script(self) -> None:
        self.assertEqual(
            MERMAID_INIT_JS,
            "mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})",
        )


if __name__ == "__main__":
    unittest.main()
