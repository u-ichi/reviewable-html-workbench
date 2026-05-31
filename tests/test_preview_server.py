from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scripts.html_review_workbench.preview_server import (
    PreviewConfigurationError,
    resolve_bind,
    start_preview,
)
from scripts.html_review_workbench.preview_host_resolve import (
    ENV_TAILSCALE_BIN,
    ENV_TAILSCALE_IP,
    detect_tailscale_ipv4,
)


class PreviewServerTest(unittest.TestCase):
    def test_auto_mode_falls_back_to_localhost_without_tailscale(self) -> None:
        bind, mode = resolve_bind("auto", tailscale_ip_getter=lambda: None)

        self.assertEqual(bind, "127.0.0.1")
        self.assertEqual(mode, "local")

    def test_auto_mode_uses_tailscale_ip_from_environment(self) -> None:
        bind, mode = resolve_bind(
            "auto",
            tailscale_ip_getter=lambda: detect_tailscale_ipv4(environ={ENV_TAILSCALE_IP: "100.64.12.34"}),
        )

        self.assertEqual(bind, "100.64.12.34")
        self.assertEqual(mode, "tailscale")

    def test_tailscale_detector_uses_configured_binary(self) -> None:
        def fake_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            self.assertEqual(args, ["/tmp/fake-tailscale", "ip", "-4"])
            return subprocess.CompletedProcess(args, 0, stdout="100.64.55.66\n", stderr="")

        self.assertEqual(
            detect_tailscale_ipv4(environ={ENV_TAILSCALE_BIN: "/tmp/fake-tailscale"}, runner=fake_runner),
            "100.64.55.66",
        )

    def test_tailscale_detector_ignores_invalid_environment_ip(self) -> None:
        def fake_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="100.64.55.66\n", stderr="")

        self.assertEqual(
            detect_tailscale_ipv4(
                environ={ENV_TAILSCALE_IP: "0.0.0.0", ENV_TAILSCALE_BIN: "/tmp/fake-tailscale"},
                runner=fake_runner,
            ),
            "100.64.55.66",
        )

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
                self.assertEqual(session.owner_pid, os.getppid())
                self.assertTrue(session.url.startswith("http://127.0.0.1:"))
                self.assertEqual(session.stop_command, f"bin/kill-review-preview.sh {session.pid}")
                self.assertEqual(Path(session.manifest).parent, (root / "annotations").resolve())

                manifest = json.loads(Path(session.manifest).read_text(encoding="utf-8"))
                self.assertEqual(manifest["schema_version"], "1.0")
                self.assertEqual(manifest["session_id"], session.session_id)
                self.assertEqual(manifest["root"], str(root.resolve()))
                self.assertEqual(manifest["bind"], "127.0.0.1")
                self.assertEqual(manifest["port"], session.port)
                self.assertEqual(manifest["url"], session.url)
                self.assertEqual(manifest["pid"], session.pid)
                self.assertEqual(manifest["owner_pid"], os.getppid())
                self.assertEqual(manifest["owner_session"], session.owner_session)
                self.assertEqual(manifest["status"], "running")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_preview_server_exits_when_owner_pid_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            session = start_preview(root, "local", owner_pid=owner.pid)
            try:
                _wait_until_preview_ready(session.url)
                owner.terminate()
                owner.wait(timeout=5)
                self.assertIsNotNone(session.process)
                session.process.wait(timeout=7)
            finally:
                if owner.poll() is None:
                    owner.terminate()
                    owner.wait(timeout=5)
                if session.process is not None and session.process.poll() is None:
                    session.process.terminate()
                    session.process.wait(timeout=5)

    def test_preview_server_reads_and_writes_comments_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            (root / "renderer-manifest.json").write_text(
                json.dumps({"document": {"id": "doc-preview"}}),
                encoding="utf-8",
            )

            session = start_preview(root, "local")
            try:
                _wait_until_preview_ready(session.url)
                comments_url = session.url.replace("/index.html", "/annotations/comments.json")
                initial = _read_json_url(comments_url)
                self.assertEqual(initial["document_id"], "doc-preview")
                self.assertEqual(initial["comments"], [])

                payload = {
                    "schema_version": "1.0",
                    "document_id": "doc-preview",
                    "comments": [
                        {
                            "id": "cmt-1",
                            "document_id": "doc-preview",
                            "block_id": "overview",
                            "selected_text": "text",
                            "prefix": "",
                            "suffix": "",
                            "comment": "Comment body",
                            "status": "needs_agent_review",
                            "created_at": "2026-05-17T00:00:00+00:00",
                            "replies": [],
                        }
                    ],
                }
                request = urllib.request.Request(
                    comments_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)

                written = json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))
                self.assertEqual(written["comments"][0]["id"], "cmt-1")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)


def _read_json_url(url: str) -> object:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_until_preview_ready(url: str) -> None:
    deadline = time.monotonic() + 5
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except urllib.error.URLError as exc:
            last_error = exc
        time.sleep(0.05)
    raise AssertionError(f"preview server did not become ready: {last_error}")


if __name__ == "__main__":
    unittest.main()
