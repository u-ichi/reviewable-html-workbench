from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import urllib.request
from types import SimpleNamespace
from pathlib import Path

from scripts.html_review_workbench.plan_preview import (
    MARKER_FILE,
    ROOT_PREFIX,
    PlanPreviewError,
    build_plan_preview_model,
    create_plan_preview,
    read_payload,
    stop_plan_preview,
)


class PlanPreviewTest(unittest.TestCase):
    def test_build_plan_preview_model_maps_plan_fields_to_blocks(self) -> None:
        model = build_plan_preview_model(_payload(), "abc123")

        self.assertEqual(model["document_id"], "plan-preview-abc123")
        self.assertEqual(model["title"], "Plan Preview Test")
        block_ids = [block["id"] for block in model["blocks"]]
        self.assertIn("plan-summary", block_ids)
        self.assertIn("plan-phases", block_ids)
        self.assertIn("key-changes", block_ids)
        self.assertIn("plan-flow", block_ids)
        self.assertIn("test-plan", block_ids)
        self.assertIn("assumptions", block_ids)
        flow = next(block for block in model["blocks"] if block["id"] == "plan-flow")
        self.assertIn("flowchart TD", flow["content"])
        self.assertIn("CLI", flow["content"])

    def test_create_plan_preview_local_mode_returns_localhost_temp_url_and_cleans_up(self) -> None:
        result = create_plan_preview(_payload(), ttl=60, mode="local")
        try:
            self.assertTrue(result.url.startswith("http://127.0.0.1:"), result.url)
            self.assertTrue(result.root.name.startswith(ROOT_PREFIX), result.root)
            self.assertEqual(result.root.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue((result.root / MARKER_FILE).exists())
            self.assertTrue((result.root / "document-model.json").exists())
            self.assertIn("plan-preview-stop", result.stop_command)

            with urllib.request.urlopen(result.url, timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Plan Preview Test", html)
            self.assertIn("CLIを追加する", html)
        finally:
            if result.root.exists():
                stop_plan_preview(result.root, result.pid, result.process, result.cleanup_process)
        self.assertFalse(result.root.exists())

    def test_create_plan_preview_auto_mode_can_return_tailscale_url(self) -> None:
        seen: dict[str, object] = {}

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            seen["root"] = root
            seen["mode"] = mode
            seen["idle_timeout"] = idle_timeout
            return SimpleNamespace(
                url="http://100.64.12.34:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        result = create_plan_preview(
            _payload(),
            ttl=60,
            mode="auto",
            preview_starter=fake_start_preview,
            cleanup_starter=lambda root, pid, ttl: None,
        )
        try:
            self.assertEqual(result.url, "http://100.64.12.34:54321/index.html")
            self.assertEqual(seen["mode"], "auto")
            self.assertEqual(seen["idle_timeout"], 60)
        finally:
            if result.root.exists():
                stop_plan_preview(result.root)

    def test_read_payload_rejects_remote_assets(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
            json.dump({"title": "bad", "remote_asset_urls": ["https://example.com/a.png"]}, tmp)
            tmp_path = Path(tmp.name)
        try:
            with self.assertRaisesRegex(PlanPreviewError, "remote_asset_urls"):
                read_payload(str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_stop_refuses_unmarked_temp_root(self) -> None:
        root = Path(tempfile.mkdtemp(prefix=ROOT_PREFIX)).resolve()
        try:
            with self.assertRaisesRegex(PlanPreviewError, "refusing to clean unmarked"):
                stop_plan_preview(root)
            self.assertTrue(root.exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_create_plan_preview_rejects_non_positive_ttl(self) -> None:
        with self.assertRaisesRegex(PlanPreviewError, "ttl must be positive"):
            create_plan_preview(_payload(), ttl=0)


def _payload() -> dict[str, object]:
    return {
        "title": "Plan Preview Test",
        "summary": "Plan ModeでURLを自然に入れる。",
        "phases": [
            {"title": "Phase 1", "detail": "CLIと一時previewを作る"},
            {"title": "Phase 2", "detail": "skill metadataを配布する"},
        ],
        "key_changes": [
            "CLIを追加する",
            "一時ディレクトリをTTLで消す",
        ],
        "flow": [
            {"from": "Plan Mode", "to": "CLI", "label": "payload"},
            {"from": "CLI", "to": "HTML preview", "label": "localhost"},
        ],
        "test_plan": [
            "unit test",
            "CLI smoke",
        ],
        "assumptions": [
            "初期版ではhookを追加しない",
        ],
    }


if __name__ == "__main__":
    unittest.main()
