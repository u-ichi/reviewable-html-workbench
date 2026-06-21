"""Session-scoped preview server for generated HTML bundles."""

from __future__ import annotations

import json
import argparse
import os
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlparse

from scripts.html_review_workbench.comment_store import CommentStore, CommentStoreError, empty_comments
from scripts.html_review_workbench.event_bus import EventBus, format_sse
from scripts.html_review_workbench.preview_host_resolve import detect_tailscale_ipv4


ROOT = Path(__file__).resolve().parents[2]
PreviewMode = Literal["auto", "tailscale", "local"]
ResolvedMode = Literal["tailscale", "local"]


class PreviewConfigurationError(ValueError):
    """Raised when a preview server would use an unsafe or invalid configuration."""


@dataclass(frozen=True)
class PreviewSession:
    schema_version: str
    session_id: str
    root: str
    bind: str
    port: int
    url: str
    pid: int
    owner_pid: int | None
    created_at: str
    mode: ResolvedMode
    status: str
    owner_session: str
    manifest: str
    stop_command: str
    idle_timeout: float
    process: subprocess.Popen[bytes] | None

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "root": self.root,
            "bind": self.bind,
            "port": self.port,
            "url": self.url,
            "pid": self.pid,
            "owner_pid": self.owner_pid,
            "created_at": self.created_at,
            "mode": self.mode,
            "status": self.status,
            "owner_session": self.owner_session,
            "manifest": self.manifest,
            "stop_command": self.stop_command,
            "idle_timeout": self.idle_timeout,
        }

    def manifest_payload(self) -> dict[str, object]:
        payload = self.to_payload()
        payload.pop("manifest")
        payload.pop("stop_command")
        return payload


def _wait_for_ready_signal(
    process: subprocess.Popen[bytes], timeout: float = 5.0
) -> int:
    """サーバーの ready シグナルを読み、実ポートを返す。

    子プロセスの stdout から ready 行（ポート情報の JSON）を timeout 付きで読む。
    パイプに対する ``select()`` は POSIX 専用で Windows では ``OSError``
    (WinError 10038) になるため、クロスプラットフォームなブロッキング
    ``readline()`` をワーカースレッドで実行し、``join(timeout)`` で待機する。
    """
    result: dict[str, object] = {}

    def _read_ready_line() -> None:
        try:
            result["line"] = process.stdout.readline()
        except Exception as exc:  # pragma: no cover - defensive
            result["error"] = exc

    reader = threading.Thread(target=_read_ready_line, daemon=True)
    reader.start()
    reader.join(timeout)
    try:
        if reader.is_alive():
            raise PreviewConfigurationError(
                "preview server did not become ready within timeout"
            )
        if "error" in result:
            raise PreviewConfigurationError(
                "preview server failed before becoming ready"
            ) from result["error"]  # type: ignore[misc]
        line = result.get("line") or b""
        if not line:
            raise PreviewConfigurationError(
                "preview server exited before becoming ready"
            )
        signal = json.loads(line)
        return int(signal["port"])
    finally:
        # Only close stdout once the reader thread has finished. Closing a
        # BufferedReader while another thread is blocked inside readline()
        # deadlocks on the buffer lock. On timeout the caller terminates the
        # process, which releases the pipe and lets the daemon thread exit.
        if not reader.is_alive() and process.stdout:
            process.stdout.close()


def start_preview(
    root: Path,
    mode: PreviewMode = "auto",
    owner_session: str | None = None,
    owner_pid: int | None = None,
    idle_timeout: float = 3600.0,
    owner_grace: float = 300.0,
) -> PreviewSession:
    root = root.resolve()
    if not root.is_dir():
        raise PreviewConfigurationError(f"preview root does not exist: {root}")

    bind, resolved_mode = resolve_bind(mode)
    session_id = uuid.uuid4().hex
    owner_session = owner_session or current_owner_session() or "unknown"
    created_at = datetime.now(timezone.utc).isoformat()

    command = [
        sys.executable,
        "-m",
        "scripts.html_review_workbench.preview_server",
        "--serve",
        "0",
        "--bind",
        bind,
        "--owner-session",
        owner_session,
        "--idle-timeout",
        str(idle_timeout),
        "--owner-grace",
        str(owner_grace),
    ]
    if owner_pid:
        command.extend(["--owner-pid", str(owner_pid)])
    command.append(str(root))

    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        port = _wait_for_ready_signal(process)
    except Exception:
        _terminate_preview_process(process)
        raise
    url = f"http://{bind}:{port}/index.html"
    manifest_path = root / "annotations" / f"preview-session-{session_id}.json"
    session = PreviewSession(
        schema_version="1.0",
        session_id=session_id,
        root=str(root),
        bind=bind,
        port=port,
        url=url,
        pid=process.pid,
        owner_pid=owner_pid,
        created_at=created_at,
        mode=resolved_mode,
        status="running",
        owner_session=owner_session,
        manifest=str(manifest_path),
        stop_command=f"bin/kill-review-preview.sh {process.pid}",
        idle_timeout=idle_timeout,
        process=process,
    )
    write_session_manifest(manifest_path, session)
    return session


def _terminate_preview_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def current_owner_session(environ: dict[str, str] | None = None) -> str | None:
    if environ is None:
        environ = os.environ
    for key in ("CODEX_THREAD_ID", "CLAUDE_SESSION_ID", "CODEX_COMPANION_SESSION_ID", "SESSION_ID"):
        value = environ.get(key)
        if value:
            return value
    return None


def resolve_bind(
    mode: PreviewMode,
    tailscale_ip_getter: Callable[[], str | None] | None = None,
) -> tuple[str, ResolvedMode]:
    if tailscale_ip_getter is None:
        tailscale_ip_getter = detect_tailscale_ipv4

    if mode == "local":
        return "127.0.0.1", "local"
    if mode == "tailscale":
        tailscale_ip = tailscale_ip_getter()
        if tailscale_ip is None:
            raise PreviewConfigurationError("tailscale mode requested but no Tailscale IPv4 was detected")
        return _validate_bind(tailscale_ip), "tailscale"
    if mode == "auto":
        tailscale_ip = tailscale_ip_getter()
        if tailscale_ip is not None:
            return _validate_bind(tailscale_ip), "tailscale"
        return "127.0.0.1", "local"
    raise PreviewConfigurationError(f"unsupported preview mode: {mode}")


def write_session_manifest(path: Path, session: PreviewSession) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.manifest_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_bind(bind: str) -> str:
    if bind == "0.0.0.0":
        raise PreviewConfigurationError("0.0.0.0 bind is not allowed for preview runtime")
    try:
        socket.inet_aton(bind)
    except OSError as exc:
        raise PreviewConfigurationError(f"invalid IPv4 bind address: {bind}") from exc
    return bind


class ReviewPreviewHandler(SimpleHTTPRequestHandler):
    comments_route = "/annotations/comments.json"
    events_route = "/events"
    _last_activity: float = 0.0
    _lock = threading.Lock()

    @classmethod
    def touch_activity(cls) -> None:
        with cls._lock:
            cls._last_activity = time.monotonic()

    @classmethod
    def seconds_since_last_activity(cls) -> float:
        with cls._lock:
            if cls._last_activity == 0.0:
                return 0.0
            return time.monotonic() - cls._last_activity

    def __init__(self, *args: object, root: Path, event_bus: EventBus, **kwargs: object) -> None:
        self.root = root.resolve()
        self.store = CommentStore(self.root)
        self.event_bus = event_bus
        super().__init__(*args, directory=str(self.root), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        self.touch_activity()
        path = self._path()
        if path == self.comments_route:
            self._send_json(self.store.read(self._document_id()))
            return
        if path == self.events_route:
            self._handle_sse()
            return
        super().do_GET()

    def do_PUT(self) -> None:
        self.touch_activity()
        if self._path() != self.comments_route:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = json.loads(self.rfile.read(_content_length(self)).decode("utf-8"))
            self.store.write(payload)
        except (json.JSONDecodeError, CommentStoreError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        source = self.headers.get("X-Comment-Source", "browser")
        self.event_bus.publish("comment_updated", {"source": source})
        self._send_json({"ok": True, "path": "annotations/comments.json"})

    def do_POST(self) -> None:
        self.touch_activity()
        if self._path() != self.events_route:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            body = json.loads(self.rfile.read(_content_length(self)).decode("utf-8"))
        except (json.JSONDecodeError, CommentStoreError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        event_type = body.get("type", "custom")
        data = {k: v for k, v in body.items() if k != "type"}
        self.event_bus.publish(event_type, data)
        self._send_json({"ok": True, "event_type": event_type})

    def _handle_sse(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_id_str = self.headers.get("Last-Event-ID", "0")
        try:
            last_id = int(last_id_str)
        except ValueError:
            last_id = 0

        try:
            for event in self.event_bus.subscribe(last_event_id=last_id):
                self.wfile.write(format_sse(event))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _document_id(self) -> str:
        manifest_path = self.root / "renderer-manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                document = manifest.get("document", {})
                if isinstance(document, dict) and isinstance(document.get("id"), str):
                    return document["id"]
            except json.JSONDecodeError:
                pass
        return "document"

    def _path(self) -> str:
        return urlparse(self.path).path


def serve(
    root: Path,
    bind: str,
    port: int,
    owner_pid: int | None = None,
    idle_timeout: float = 3600.0,
    owner_grace: float = 300.0,
) -> None:
    bind = _validate_bind(bind)
    root = root.resolve()
    if not root.is_dir():
        raise PreviewConfigurationError(f"preview root does not exist: {root}")
    handler_class = ReviewPreviewHandler
    event_bus = EventBus()
    handler = partial(handler_class, root=root, event_bus=event_bus)
    with ThreadingHTTPServer((bind, port), handler) as server:
        server.event_bus = event_bus
        actual_port = server.server_address[1]
        sys.stdout.buffer.write(
            json.dumps({"ready": True, "port": actual_port}).encode() + b"\n"
        )
        sys.stdout.buffer.flush()
        if owner_pid and owner_pid > 1:
            _start_owner_watchdog(server, owner_pid, handler_class, grace_seconds=owner_grace)
        if idle_timeout > 0:
            _start_idle_watchdog(server, handler_class, idle_timeout)
        _start_comments_file_watcher(root, event_bus)
        server.serve_forever()


def _content_length(handler: SimpleHTTPRequestHandler) -> int:
    header = handler.headers.get("Content-Length")
    try:
        length = int(header or "0")
    except ValueError as exc:
        raise CommentStoreError("Content-Length must be an integer") from exc
    if length <= 0:
        raise CommentStoreError("request body is required")
    return length


def _start_owner_watchdog(
    server: ThreadingHTTPServer,
    owner_pid: int,
    handler_class: type[ReviewPreviewHandler],
    grace_seconds: float = 300.0,
    interval_seconds: float = 2.0,
) -> None:
    def watch() -> None:
        while True:
            if not _pid_is_alive(owner_pid):
                _run_grace_period(server, handler_class, grace_seconds, interval_seconds)
                return
            time.sleep(interval_seconds)

    thread = threading.Thread(target=watch, name="preview-owner-watchdog", daemon=True)
    thread.start()


def _run_grace_period(
    server: ThreadingHTTPServer,
    handler_class: type[ReviewPreviewHandler],
    grace_seconds: float,
    check_interval: float,
) -> None:
    if grace_seconds <= 0:
        server.shutdown()
        return

    grace_start = time.monotonic()
    effective_interval = min(check_interval, max(grace_seconds / 2, 0.1))
    while True:
        time.sleep(effective_interval)
        elapsed = time.monotonic() - grace_start
        idle = handler_class.seconds_since_last_activity()
        if handler_class._last_activity > 0 and idle >= grace_seconds:
            server.shutdown()
            return
        if handler_class._last_activity == 0.0 and elapsed >= grace_seconds:
            server.shutdown()
            return


def _start_idle_watchdog(
    server: ThreadingHTTPServer,
    handler_class: type[ReviewPreviewHandler],
    timeout: float,
    check_interval: float = 30.0,
) -> None:
    effective_interval = min(check_interval, max(timeout / 2, 0.1))

    def watch() -> None:
        while True:
            time.sleep(effective_interval)
            idle = handler_class.seconds_since_last_activity()
            if handler_class._last_activity > 0 and idle >= timeout:
                server.shutdown()
                return

    thread = threading.Thread(target=watch, name="preview-idle-watchdog", daemon=True)
    thread.start()


def _start_comments_file_watcher(
    root: Path,
    event_bus: EventBus,
    interval: float = 2.0,
) -> None:
    comments_path = root / "annotations" / "comments.json"

    def watch() -> None:
        last_mtime = 0.0
        try:
            last_mtime = comments_path.stat().st_mtime
        except OSError:
            pass
        while True:
            time.sleep(interval)
            try:
                current_mtime = comments_path.stat().st_mtime
            except OSError:
                continue
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                event_bus.publish("comment_updated", {"source": "file_watcher"})

    thread = threading.Thread(target=watch, name="comments-file-watcher", daemon=True)
    thread.start()


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def find_active_session(root: Path) -> dict[str, object] | None:
    """Return the manifest of the most recently created running preview session under *root*, or None."""
    annotations = root / "annotations"
    if not annotations.is_dir():
        return None
    newest: dict[str, object] | None = None
    newest_ts = ""
    for manifest_path in annotations.glob("preview-session-*.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        pid = manifest.get("pid")
        if isinstance(pid, int) and _pid_is_alive(pid):
            ts = str(manifest.get("created_at", ""))
            if ts > newest_ts:
                newest_ts = ts
                newest = manifest
    return newest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="preview_server")
    parser.add_argument("--serve", type=int, metavar="PORT")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--owner-session", default="unknown")
    parser.add_argument("--owner-pid", type=int)
    parser.add_argument("--idle-timeout", type=float, default=3600.0)
    parser.add_argument("--owner-grace", type=float, default=300.0)
    parser.add_argument("root", nargs="?")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.serve is None or args.root is None:
        parser.error("--serve PORT and root are required")
    serve(
        Path(args.root),
        args.bind,
        args.serve,
        owner_pid=args.owner_pid,
        idle_timeout=args.idle_timeout,
        owner_grace=args.owner_grace,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
