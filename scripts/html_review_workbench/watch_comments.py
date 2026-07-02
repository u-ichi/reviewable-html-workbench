"""SSE client for streaming comment change events from the preview server."""

from __future__ import annotations

import http.client
import json
import signal
import sys
from pathlib import Path
from urllib.parse import urlparse


def _check_gate_status(root: Path) -> dict[str, object] | None:
    """Return gate payload or None on error."""
    from scripts.html_review_workbench.resolution_gate import try_check_gate

    result = try_check_gate(root)
    if result is None:
        return None
    return result.to_payload()


def run_watch(server_url: str, root: Path | None = None) -> int:
    """Connect to the preview server SSE endpoint and print events to stdout."""
    parsed = urlparse(server_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    last_event_id = "0"

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    while True:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=90)
            conn.request(
                "GET",
                "/events",
                headers={"Accept": "text/event-stream", "Last-Event-ID": last_event_id},
            )
            resp = conn.getresponse()
            if resp.status != 200:
                print(
                    json.dumps({"status": "failed", "error": f"SSE endpoint returned {resp.status}"}),
                    flush=True,
                )
                return 2

            event_type = ""
            event_data = ""
            event_id = ""

            while True:
                line_bytes = resp.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8").rstrip("\n")

                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    event_data = line[6:]
                elif line.startswith("id: "):
                    event_id = line[4:]
                elif line == "":
                    if event_type and event_type != "heartbeat":
                        try:
                            data = json.loads(event_data)
                        except json.JSONDecodeError:
                            data = {"raw": event_data}
                        if data.get("source") != "agent":
                            output = {"event": event_type, "id": event_id, "data": data}
                            if root is not None:
                                gate_info = _check_gate_status(root)
                                if gate_info is not None:
                                    output["gate"] = gate_info
                            print(json.dumps(output, ensure_ascii=False), flush=True)
                    if event_id:
                        last_event_id = event_id
                    event_type = ""
                    event_data = ""
                    event_id = ""

        except (ConnectionRefusedError, ConnectionResetError, OSError):
            return 1
        except KeyboardInterrupt:
            return 0
        finally:
            try:
                conn.close()
            except Exception:
                pass


def send_notify(server_url: str, message: str = "") -> int:
    """POST a document_updated event to the preview server."""
    try:
        result = post_event(server_url, "document_updated", {"message": message})
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 2
    except (ConnectionRefusedError, ConnectionResetError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2


def post_event(server_url: str, event_type: str, data: dict[str, object] | None = None) -> dict[str, object]:
    """POST an event payload to the preview server and return the JSON response."""
    parsed = urlparse(server_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80

    payload = {"type": event_type}
    if data:
        payload.update(data)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    conn: http.client.HTTPConnection | None = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.request(
            "POST",
            "/events",
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        resp = conn.getresponse()
        return json.loads(resp.read().decode("utf-8"))
    finally:
        if conn is not None:
            conn.close()
