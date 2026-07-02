"""Session-scoped preview server for generated HTML bundles."""

from __future__ import annotations

import json
import argparse
import os
import socket
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from scripts.html_review_workbench.common import now_iso, pid_is_alive, write_json
from scripts.html_review_workbench.preview_host_resolve import detect_tailscale_ipv4
from scripts.html_review_workbench.preview_runtime import (
    ReviewPreviewHandler,
    _content_length,
    _run_grace_period,
    _start_comments_file_watcher,
    _start_idle_watchdog,
    _start_owner_watchdog,
    serve,
)


PreviewMode = Literal["auto", "tailscale", "local"]
ResolvedMode = Literal["tailscale", "local"]
DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS = 24 * 60 * 60


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
    idle_timeout: float = DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    owner_grace: float = 300.0,
) -> PreviewSession:
    root = root.resolve()
    if not root.is_dir():
        raise PreviewConfigurationError(f"preview root does not exist: {root}")

    bind, resolved_mode = resolve_bind(mode)
    session_id = uuid.uuid4().hex
    owner_session = owner_session or current_owner_session() or "unknown"
    created_at = now_iso()

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
    write_json(path, session.manifest_payload(), ensure_parent=True)


def _validate_bind(bind: str) -> str:
    if bind == "0.0.0.0":
        raise PreviewConfigurationError("0.0.0.0 bind is not allowed for preview runtime")
    try:
        socket.inet_aton(bind)
    except OSError as exc:
        raise PreviewConfigurationError(f"invalid IPv4 bind address: {bind}") from exc
    return bind


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
        if isinstance(pid, int) and pid_is_alive(pid):
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
    parser.add_argument("--idle-timeout", type=float, default=DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS)
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
