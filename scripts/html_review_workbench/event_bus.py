"""Thread-safe event bus for preview server SSE."""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Iterator

from scripts.html_review_workbench.common import now_iso


@dataclass(frozen=True)
class ServerEvent:
    id: int
    type: str
    data: dict[str, object]
    timestamp: str = field(default_factory=now_iso)


class EventBus:
    """Publish/subscribe event bus with bounded history and heartbeat support."""

    def __init__(self, maxlen: int = 200) -> None:
        self._events: deque[ServerEvent] = deque(maxlen=maxlen)
        self._next_id: int = 1
        self._condition = threading.Condition()

    def publish(self, event_type: str, data: dict[str, object] | None = None) -> ServerEvent:
        with self._condition:
            event = ServerEvent(
                id=self._next_id,
                type=event_type,
                data=data or {},
            )
            self._next_id += 1
            self._events.append(event)
            self._condition.notify_all()
            return event

    def subscribe(
        self,
        last_event_id: int = 0,
        heartbeat_interval: float = 30.0,
    ) -> Iterator[ServerEvent]:
        """Yield events starting after *last_event_id*.

        Blocks when caught up; yields a heartbeat event if nothing arrives
        within *heartbeat_interval* seconds.
        """
        cursor = last_event_id
        while True:
            with self._condition:
                pending = [e for e in self._events if e.id > cursor]
                if not pending:
                    self._condition.wait(timeout=heartbeat_interval)
                    pending = [e for e in self._events if e.id > cursor]

            if pending:
                for event in pending:
                    yield event
                    cursor = event.id
            else:
                yield ServerEvent(id=cursor, type="heartbeat", data={})

    @property
    def last_id(self) -> int:
        with self._condition:
            return self._events[-1].id if self._events else 0


def format_sse(event: ServerEvent) -> bytes:
    """Format a ServerEvent as an SSE text block."""
    lines = [f"id: {event.id}", f"event: {event.type}"]
    lines.append(f"data: {json.dumps(event.data, ensure_ascii=False)}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")
