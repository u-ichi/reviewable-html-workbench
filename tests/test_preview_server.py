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
from unittest.mock import patch

from scripts.html_review_workbench.preview_server import (
    DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
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
            if args == ["ifconfig"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            self.assertEqual(args, ["/tmp/fake-tailscale", "ip", "-4"])
            return subprocess.CompletedProcess(args, 0, stdout="100.64.55.66\n", stderr="")

        self.assertEqual(
            detect_tailscale_ipv4(environ={ENV_TAILSCALE_BIN: "/tmp/fake-tailscale"}, runner=fake_runner),
            "100.64.55.66",
        )

    def test_tailscale_detector_prefers_ifconfig_before_cli(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            if args == ["ifconfig"]:
                return subprocess.CompletedProcess(
                    args,
                    0,
                    stdout="\n".join(
                        [
                            "en0: flags=8863<UP>",
                            "\tinet 192.168.1.8 netmask 0xffffff00 broadcast 192.168.1.255",
                            "utun8: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST>",
                            "\tinet 100.92.198.57 --> 100.92.198.57 netmask 0xffffffff",
                        ]
                    ),
                    stderr="",
                )
            return subprocess.CompletedProcess(args, 0, stdout="100.64.55.66\n", stderr="")

        self.assertEqual(detect_tailscale_ipv4(runner=fake_runner), "100.92.198.57")
        self.assertEqual(calls, [["ifconfig"]])

    def test_tailscale_detector_ignores_invalid_environment_ip(self) -> None:
        def fake_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if args == ["ifconfig"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
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

            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                self.assertEqual(session.bind, "127.0.0.1")
                self.assertEqual(session.mode, "local")
                self.assertGreater(session.pid, 0)
                self.assertEqual(session.owner_pid, os.getpid())
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
                self.assertEqual(manifest["owner_pid"], os.getpid())
                self.assertEqual(manifest["owner_session"], session.owner_session)
                self.assertEqual(manifest["status"], "running")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_preview_default_idle_timeout_is_24_hours(self) -> None:
        from scripts.html_review_workbench.cli import build_parser

        args = build_parser().parse_args(["preview", "--root", "/tmp/out", "--mode", "local"])
        self.assertEqual(DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS, 24 * 60 * 60)
        self.assertEqual(args.idle_timeout, DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS)

    def test_wait_for_ready_signal_reads_from_non_socket_pipe(self) -> None:
        # Regression: the ready-signal wait must not select() on the child
        # stdout pipe. select() on a pipe is POSIX-only and raises
        # OSError WinError 10038 on Windows. os.pipe() yields non-socket FDs,
        # reproducing that path on every platform.
        from scripts.html_review_workbench.preview_server import _wait_for_ready_signal

        read_fd, write_fd = os.pipe()
        reader = os.fdopen(read_fd, "rb", buffering=0)
        with os.fdopen(write_fd, "wb", buffering=0) as writer:
            writer.write(b'{"port": 51234}\n')

        class _FakeProcess:
            def __init__(self, stdout: object) -> None:
                self.stdout = stdout

        port = _wait_for_ready_signal(_FakeProcess(reader), timeout=5.0)
        self.assertEqual(port, 51234)

    def test_wait_for_ready_signal_times_out_without_blocking(self) -> None:
        # A hung child must raise instead of blocking the parent forever.
        from scripts.html_review_workbench.preview_server import _wait_for_ready_signal

        read_fd, write_fd = os.pipe()
        reader = os.fdopen(read_fd, "rb", buffering=0)

        class _FakeProcess:
            def __init__(self, stdout: object) -> None:
                self.stdout = stdout

        try:
            with self.assertRaises(PreviewConfigurationError):
                _wait_for_ready_signal(_FakeProcess(reader), timeout=0.2)
        finally:
            os.close(write_fd)
            reader.close()

    def test_start_preview_terminates_process_when_ready_signal_fails(self) -> None:
        class _FakeProcess:
            pid = 51234
            stdout = None
            terminated = False
            killed = False
            waited = False

            def poll(self) -> int | None:
                return None if not self.terminated else -15

            def terminate(self) -> None:
                self.terminated = True

            def wait(self, timeout: float | None = None) -> int:
                self.waited = True
                return -15

            def kill(self) -> None:
                self.killed = True

        fake_process = _FakeProcess()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            with patch("scripts.html_review_workbench.preview_server.subprocess.Popen", return_value=fake_process):
                with patch(
                    "scripts.html_review_workbench.preview_server._wait_for_ready_signal",
                    side_effect=PreviewConfigurationError("ready timeout"),
                ):
                    with self.assertRaisesRegex(PreviewConfigurationError, "ready timeout"):
                        start_preview(root, "local")

        self.assertTrue(fake_process.terminated)
        self.assertTrue(fake_process.waited)
        self.assertFalse(fake_process.killed)

    def test_preview_server_exits_when_owner_pid_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            session = start_preview(root, "local", owner_pid=owner.pid, idle_timeout=0, owner_grace=0)
            try:
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

    def test_owner_pid_death_with_grace_keeps_server_alive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            session = start_preview(root, "local", owner_pid=owner.pid, idle_timeout=0, owner_grace=10)
            try:
                owner.terminate()
                owner.wait(timeout=5)
                time.sleep(1)
                with urllib.request.urlopen(session.url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                self.assertIsNotNone(session.process)
                self.assertIsNone(session.process.poll())
            finally:
                if owner.poll() is None:
                    owner.terminate()
                    owner.wait(timeout=5)
                if session.process is not None and session.process.poll() is None:
                    session.process.terminate()
                    session.process.wait(timeout=5)

    def test_owner_pid_death_grace_expires_without_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            session = start_preview(root, "local", owner_pid=owner.pid, idle_timeout=0, owner_grace=3)
            try:
                with urllib.request.urlopen(session.url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                owner.terminate()
                owner.wait(timeout=5)
                self.assertIsNotNone(session.process)
                session.process.wait(timeout=8)
                self.assertIsNotNone(session.process.poll())
            finally:
                if owner.poll() is None:
                    owner.terminate()
                    owner.wait(timeout=5)
                if session.process is not None and session.process.poll() is None:
                    session.process.terminate()
                    session.process.wait(timeout=5)

    def test_owner_pid_death_uses_idle_timeout_after_grace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            session = start_preview(root, "local", owner_pid=owner.pid, idle_timeout=8, owner_grace=1)
            try:
                with urllib.request.urlopen(session.url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                owner.terminate()
                owner.wait(timeout=5)
                time.sleep(4)
                with urllib.request.urlopen(session.url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
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

            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
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

                event = _read_sse_event(session.url.replace("/index.html", "/events"))
                self.assertEqual(event["event"], "comment_updated")
                self.assertEqual(event["data"]["source"], "browser")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_preview_server_posts_custom_events_to_sse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")

            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                events_url = session.url.replace("/index.html", "/events")
                request = urllib.request.Request(
                    events_url,
                    data=json.dumps(
                        {
                            "type": "document_updated",
                            "message": "Rendered new document model.",
                            "source": "agent",
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    result = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(result["event_type"], "document_updated")

                event = _read_sse_event(events_url)
                self.assertEqual(event["event"], "document_updated")
                self.assertEqual(event["data"]["source"], "agent")
                self.assertEqual(event["data"]["message"], "Rendered new document model.")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_preview_server_starts_without_owner_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")

            session = start_preview(root, "local", idle_timeout=0)
            try:
                with urllib.request.urlopen(session.url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_preview_server_idle_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")

            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=3)
            try:
                with urllib.request.urlopen(session.url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                time.sleep(5)
                self.assertIsNotNone(session.process)
                session.process.wait(timeout=5)
                self.assertIsNotNone(session.process.poll())
            finally:
                if session.process is not None and session.process.poll() is None:
                    session.process.terminate()
                    session.process.wait(timeout=5)

    def test_preview_server_without_owner_pid_exits_after_idle_timeout_before_first_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")

            session = start_preview(root, "local", idle_timeout=1)
            try:
                self.assertIsNone(session.owner_pid)
                self.assertIsNotNone(session.process)
                session.process.wait(timeout=5)
                self.assertIsNotNone(session.process.poll())
            finally:
                if session.process is not None and session.process.poll() is None:
                    session.process.terminate()
                    session.process.wait(timeout=5)


def _read_json_url(url: str) -> object:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_sse_event(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=5) as response:
        event: dict[str, object] = {}
        data = ""
        while True:
            line = response.readline().decode("utf-8").strip()
            if line == "":
                break
            if line.startswith("id: "):
                event["id"] = line[4:]
            elif line.startswith("event: "):
                event["event"] = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        event["data"] = json.loads(data)
        return event


if __name__ == "__main__":
    unittest.main()
