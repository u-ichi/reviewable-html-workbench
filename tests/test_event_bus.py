"""Tests for the EventBus and SSE formatting."""

from __future__ import annotations

import json
import threading
import time
import unittest

from scripts.html_review_workbench.event_bus import EventBus, ServerEvent, format_sse


class EventBusPublishTest(unittest.TestCase):
    def test_publish_returns_event_with_incrementing_id(self) -> None:
        bus = EventBus()
        e1 = bus.publish("a", {"x": 1})
        e2 = bus.publish("b", {"y": 2})
        self.assertEqual(e1.id, 1)
        self.assertEqual(e2.id, 2)
        self.assertEqual(e1.type, "a")
        self.assertEqual(e2.type, "b")

    def test_publish_with_no_data(self) -> None:
        bus = EventBus()
        event = bus.publish("ping")
        self.assertEqual(event.data, {})

    def test_last_id_tracks_latest(self) -> None:
        bus = EventBus()
        self.assertEqual(bus.last_id, 0)
        bus.publish("a")
        self.assertEqual(bus.last_id, 1)
        bus.publish("b")
        self.assertEqual(bus.last_id, 2)


class EventBusSubscribeTest(unittest.TestCase):
    def test_subscribe_yields_new_events(self) -> None:
        bus = EventBus()
        bus.publish("first", {"n": 1})
        bus.publish("second", {"n": 2})

        events = []
        for event in bus.subscribe(last_event_id=0, heartbeat_interval=0.1):
            events.append(event)
            if len(events) >= 2:
                break
        self.assertEqual([e.type for e in events], ["first", "second"])

    def test_subscribe_filters_by_last_event_id(self) -> None:
        bus = EventBus()
        bus.publish("old")
        bus.publish("new")

        events = []
        for event in bus.subscribe(last_event_id=1, heartbeat_interval=0.1):
            events.append(event)
            if event.type != "heartbeat":
                break
        self.assertEqual(events[0].type, "new")
        self.assertEqual(events[0].id, 2)

    def test_subscribe_emits_heartbeat_when_idle(self) -> None:
        bus = EventBus()
        events = []
        for event in bus.subscribe(last_event_id=0, heartbeat_interval=0.05):
            events.append(event)
            if event.type == "heartbeat":
                break
        self.assertEqual(events[0].type, "heartbeat")

    def test_subscribe_receives_concurrent_publish(self) -> None:
        bus = EventBus()
        received = []

        def subscriber() -> None:
            for event in bus.subscribe(last_event_id=0, heartbeat_interval=5.0):
                received.append(event)
                if event.type == "done":
                    break

        thread = threading.Thread(target=subscriber)
        thread.start()
        time.sleep(0.05)
        bus.publish("hello")
        bus.publish("done")
        thread.join(timeout=2.0)
        types = [e.type for e in received]
        self.assertIn("hello", types)
        self.assertIn("done", types)


class EventBusBoundedDequeTest(unittest.TestCase):
    def test_old_events_evicted_when_maxlen_exceeded(self) -> None:
        bus = EventBus(maxlen=3)
        for i in range(5):
            bus.publish("e", {"i": i})
        self.assertEqual(bus.last_id, 5)
        events = []
        for event in bus.subscribe(last_event_id=0, heartbeat_interval=0.05):
            if event.type == "heartbeat":
                break
            events.append(event)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].id, 3)


class FormatSseTest(unittest.TestCase):
    def test_format_produces_valid_sse_block(self) -> None:
        event = ServerEvent(id=42, type="comment_updated", data={"source": "browser"})
        result = format_sse(event)
        text = result.decode("utf-8")
        self.assertIn("id: 42\n", text)
        self.assertIn("event: comment_updated\n", text)
        self.assertIn("data: ", text)
        self.assertTrue(text.endswith("\n\n"))
        data_line = [line for line in text.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[6:])
        self.assertEqual(parsed["source"], "browser")


if __name__ == "__main__":
    unittest.main()
