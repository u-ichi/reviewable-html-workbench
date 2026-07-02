"""Runtime HTTP serving primitives for preview sessions."""

from __future__ import annotations

import json
import sys
import threading
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from scripts.html_review_workbench.comment_store import CommentStore, CommentStoreError
from scripts.html_review_workbench.common import pid_is_alive
from scripts.html_review_workbench.event_bus import EventBus, format_sse

DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS = 24 * 60 * 60


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
    idle_timeout: float = DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    owner_grace: float = 300.0,
) -> None:
    from scripts.html_review_workbench.preview_server import PreviewConfigurationError, _validate_bind

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
        if idle_timeout > 0:
            handler_class.touch_activity()
            _start_idle_watchdog(server, handler_class, idle_timeout)
        if owner_pid and owner_pid > 1:
            _start_owner_watchdog(
                server,
                owner_pid,
                handler_class,
                grace_seconds=owner_grace,
                idle_timeout=idle_timeout,
            )
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
    idle_timeout: float = DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    interval_seconds: float = 2.0,
) -> None:
    def watch() -> None:
        while True:
            if not pid_is_alive(owner_pid):
                if idle_timeout > 0 and grace_seconds > 0:
                    time.sleep(grace_seconds)
                    return
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
