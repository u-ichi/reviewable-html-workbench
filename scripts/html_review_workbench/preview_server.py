"""Session-scoped preview server for generated HTML bundles."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal


ROOT = Path(__file__).resolve().parents[2]
SESSION_MANIFEST_DIR = ROOT / "output" / "tmp" / "html-preview-sessions"
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
    created_at: str
    mode: ResolvedMode
    status: str
    manifest: str
    stop_command: str
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
            "created_at": self.created_at,
            "mode": self.mode,
            "status": self.status,
            "manifest": self.manifest,
            "stop_command": self.stop_command,
        }

    def manifest_payload(self) -> dict[str, object]:
        payload = self.to_payload()
        payload.pop("manifest")
        payload.pop("stop_command")
        return payload


def start_preview(root: Path, mode: PreviewMode = "auto") -> PreviewSession:
    root = root.resolve()
    if not root.is_dir():
        raise PreviewConfigurationError(f"preview root does not exist: {root}")

    bind, resolved_mode = resolve_bind(mode)
    port = pick_free_port(bind)
    session_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            bind,
            "--directory",
            str(root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    url = f"http://{bind}:{port}/index.html"
    manifest_path = SESSION_MANIFEST_DIR / f"{session_id}.json"
    session = PreviewSession(
        schema_version="1.0",
        session_id=session_id,
        root=str(root),
        bind=bind,
        port=port,
        url=url,
        pid=process.pid,
        created_at=created_at,
        mode=resolved_mode,
        status="running",
        manifest=str(manifest_path),
        stop_command=f"kill {process.pid}",
        process=process,
    )
    write_session_manifest(manifest_path, session)
    return session


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


def detect_tailscale_ipv4() -> str | None:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate:
            try:
                return _validate_bind(candidate)
            except PreviewConfigurationError:
                continue
    return None


def pick_free_port(bind: str) -> int:
    bind = _validate_bind(bind)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((bind, 0))
        return int(sock.getsockname()[1])


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
