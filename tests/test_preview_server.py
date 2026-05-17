from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.preview_server import (
    PreviewConfigurationError,
    resolve_bind,
    start_preview,
)


class PreviewServerTest(unittest.TestCase):
    def test_auto_mode_falls_back_to_localhost_without_tailscale(self) -> None:
        bind, mode = resolve_bind("auto", tailscale_ip_getter=lambda: None)

        self.assertEqual(bind, "127.0.0.1")
        self.assertEqual(mode, "local")

    def test_tailscale_mode_rejects_unsafe_wildcard_bind(self) -> None:
        with self.assertRaisesRegex(PreviewConfigurationError, "0.0.0.0"):
            resolve_bind("tailscale", tailscale_ip_getter=lambda: "0.0.0.0")

    def test_auto_mode_rejects_invalid_injected_bind(self) -> None:
        with self.assertRaisesRegex(PreviewConfigurationError, "invalid IPv4"):
            resolve_bind("auto", tailscale_ip_getter=lambda: "The Tailscale CLI failed to start")

    def test_start_preview_returns_url_pid_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")

            session = start_preview(root, "local")
            try:
                self.assertEqual(session.bind, "127.0.0.1")
                self.assertEqual(session.mode, "local")
                self.assertGreater(session.pid, 0)
                self.assertTrue(session.url.startswith("http://127.0.0.1:"))
                self.assertIn("kill ", session.stop_command)

                manifest = json.loads(Path(session.manifest).read_text(encoding="utf-8"))
                self.assertEqual(manifest["schema_version"], "1.0")
                self.assertEqual(manifest["session_id"], session.session_id)
                self.assertEqual(manifest["root"], str(root.resolve()))
                self.assertEqual(manifest["bind"], "127.0.0.1")
                self.assertEqual(manifest["port"], session.port)
                self.assertEqual(manifest["url"], session.url)
                self.assertEqual(manifest["pid"], session.pid)
                self.assertEqual(manifest["status"], "running")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
