"""Resolve the preferred preview host for Tailscale-backed local previews."""

from __future__ import annotations

import os
import socket
import subprocess
from collections.abc import Callable, Iterable, Mapping


ENV_TAILSCALE_IP = "HTML_REVIEW_WORKBENCH_TAILSCALE_IP"
ENV_TAILSCALE_BIN = "HTML_REVIEW_WORKBENCH_TAILSCALE_BIN"


def detect_tailscale_ipv4(
    *,
    environ: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout: float = 2,
) -> str | None:
    """Return the first safe Tailscale IPv4 from env override or the CLI."""

    env = os.environ if environ is None else environ
    explicit_ip = _first_valid_ipv4((env.get(ENV_TAILSCALE_IP, ""),))
    if explicit_ip is not None:
        return explicit_ip

    tailscale_bin = env.get(ENV_TAILSCALE_BIN, "tailscale").strip()
    if not tailscale_bin:
        return None

    try:
        result = runner(
            [tailscale_bin, "ip", "-4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return _first_valid_ipv4(result.stdout.splitlines())


def _first_valid_ipv4(lines: Iterable[str]) -> str | None:
    for line in lines:
        candidate = line.strip()
        if _is_safe_ipv4(candidate):
            return candidate
    return None


def _is_safe_ipv4(candidate: str) -> bool:
    if not candidate or candidate == "0.0.0.0":
        return False
    try:
        socket.inet_aton(candidate)
    except OSError:
        return False
    return candidate.count(".") == 3


def main() -> int:
    ip_address = detect_tailscale_ipv4()
    if ip_address is not None:
        print(ip_address)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
