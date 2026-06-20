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
    PLAN_PREVIEW_SENTINEL_DIR_NAME,
    ROOT_PREFIX,
    PlanPreviewError,
    _remove_plan_preview_sentinel,
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
        self.assertIn("original-plan-text", block_ids)
        self.assertIn("plan-phases", block_ids)
        self.assertIn("key-changes", block_ids)
        self.assertIn("plan-section-1", block_ids)
        self.assertIn("plan-flow", block_ids)
        self.assertIn("test-plan", block_ids)
        self.assertIn("assumptions", block_ids)
        self.assertIn("supplemental-context", block_ids)
        original = next(block for block in model["blocks"] if block["id"] == "original-plan-text")
        self.assertEqual(original["type"], "code")
        self.assertIn("## 元の計画本文", original["content"])
        self.assertIn("CLIでは読み取りにくい依存関係もHTMLで補足する。", original["content"])
        section = next(block for block in model["blocks"] if block["id"] == "plan-section-1")
        self.assertIn("CLI本文だけでは表現しにくい詳細", section["content"])
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
            self.assertTrue((result.root / "renderer-manifest.json").exists())
            self.assertIn("plan-preview-stop", result.stop_command)

            with urllib.request.urlopen(result.url, timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Plan Preview Test", html)
            self.assertIn("CLIを追加する", html)
            self.assertIn("## 元の計画本文", html)
            self.assertIn("CLIでは読み取りにくい依存関係もHTMLで補足する。", html)
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

    def test_create_plan_preview_writes_claude_session_sentinel(self) -> None:
        old_session_id = os.environ.get("CLAUDE_SESSION_ID")
        session_id = f"test-plan-preview-{os.getpid()}"
        os.environ["CLAUDE_SESSION_ID"] = session_id
        _remove_plan_preview_sentinel()
        result = None

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            return SimpleNamespace(
                url="http://127.0.0.1:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        try:
            result = create_plan_preview(
                _payload(),
                ttl=60,
                mode="local",
                preview_starter=fake_start_preview,
                cleanup_starter=lambda root, pid, ttl: None,
            )
            sentinel = Path(tempfile.gettempdir()) / PLAN_PREVIEW_SENTINEL_DIR_NAME / session_id
            payload = json.loads(sentinel.read_text(encoding="utf-8"))
            self.assertEqual(payload["preview_id"], result.id)
            self.assertIsInstance(payload["created_at"], str)
            self.assertTrue(payload["created_at"])
        finally:
            _remove_plan_preview_sentinel()
            if old_session_id is None:
                os.environ.pop("CLAUDE_SESSION_ID", None)
            else:
                os.environ["CLAUDE_SESSION_ID"] = old_session_id
            if result is not None and result.root.exists():
                stop_plan_preview(result.root)

    def test_create_plan_preview_does_not_write_sentinel_without_claude_session_id(self) -> None:
        old_session_id = os.environ.pop("CLAUDE_SESSION_ID", None)
        sentinel_dir = Path(tempfile.gettempdir()) / PLAN_PREVIEW_SENTINEL_DIR_NAME
        before = set(sentinel_dir.iterdir()) if sentinel_dir.exists() else set()
        result = None

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            return SimpleNamespace(
                url="http://127.0.0.1:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        try:
            result = create_plan_preview(
                _payload(),
                ttl=60,
                mode="local",
                preview_starter=fake_start_preview,
                cleanup_starter=lambda root, pid, ttl: None,
            )
            after = set(sentinel_dir.iterdir()) if sentinel_dir.exists() else set()
            self.assertEqual(after, before)
        finally:
            if old_session_id is not None:
                os.environ["CLAUDE_SESSION_ID"] = old_session_id
            if result is not None and result.root.exists():
                stop_plan_preview(result.root)

    def test_create_plan_preview_validates_bundle_before_starting_preview(self) -> None:
        seen: dict[str, object] = {}

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            seen["started"] = True
            return SimpleNamespace(
                url="http://127.0.0.1:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        def fake_validate_bundle(root: Path) -> SimpleNamespace:
            seen["root"] = root
            return SimpleNamespace(ok=False, errors=["missing review blocks"], review_blocks=0)

        with self.assertRaisesRegex(PlanPreviewError, "bundle validation failed"):
            create_plan_preview(
                _payload(),
                ttl=60,
                mode="local",
                preview_starter=fake_start_preview,
                cleanup_starter=lambda root, pid, ttl: None,
                bundle_validator=fake_validate_bundle,
            )
        self.assertNotIn("started", seen)
        root = seen.get("root")
        self.assertIsInstance(root, Path)
        self.assertFalse(root.exists())

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
        "source_text": "\n".join(
            [
                "## 元の計画本文",
                "",
                "- 実装範囲: plan-preview CLIで全文を保持する。",
                "- 非範囲: 最終HTML成果物のrenderer flowへ流さない。",
                "- 検証: unit testとlocal previewで本文欠落を確認する。",
                "- 補足: CLIでは読み取りにくい依存関係もHTMLで補足する。",
            ]
        ),
        "phases": [
            {"title": "Phase 1", "detail": "CLIと一時previewを作る"},
            {"title": "Phase 2", "detail": "skill metadataを配布する"},
        ],
        "key_changes": [
            "CLIを追加する",
            "一時ディレクトリをTTLで消す",
        ],
        "sections": [
            {
                "title": "補助表示",
                "content": "CLI本文だけでは表現しにくい詳細を、HTML上では補助情報として増やす。",
                "items": [
                    "元本文の情報は削らない",
                    "構造化ビューは補助として使う",
                ],
            }
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
        "visual_notes": [
            "全文ブロックを先に置く",
            "図とリストで依存関係を追加表示する",
        ],
    }


if __name__ == "__main__":
    unittest.main()
