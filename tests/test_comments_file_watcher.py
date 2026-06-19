"""preview server の comments.json ファイル変更検知テスト。"""

import tempfile
import threading
import time
from pathlib import Path
import unittest

from scripts.html_review_workbench.event_bus import EventBus


class TestCommentsFileWatcher(unittest.TestCase):
    def test_file_change_triggers_event(self):
        from scripts.html_review_workbench.preview_server import _start_comments_file_watcher

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            annotations = root / "annotations"
            annotations.mkdir()
            comments_path = annotations / "comments.json"
            comments_path.write_text("{}", encoding="utf-8")

            event_bus = EventBus()
            received = []

            def collector() -> None:
                for event in event_bus.subscribe(last_event_id=0):
                    if event.type == "comment_updated":
                        received.append(event)
                        break

            collector_thread = threading.Thread(target=collector, daemon=True)
            collector_thread.start()

            _start_comments_file_watcher(root, event_bus, interval=0.3)

            time.sleep(0.5)
            comments_path.write_text('{"updated": true}', encoding="utf-8")

            collector_thread.join(timeout=5.0)
            self.assertGreaterEqual(len(received), 1)
            self.assertEqual(received[0].type, "comment_updated")
            self.assertEqual(received[0].data["source"], "file_watcher")

    def test_no_event_without_file_change(self):
        from scripts.html_review_workbench.preview_server import _start_comments_file_watcher

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            annotations = root / "annotations"
            annotations.mkdir()
            comments_path = annotations / "comments.json"
            comments_path.write_text("{}", encoding="utf-8")

            event_bus = EventBus()
            _start_comments_file_watcher(root, event_bus, interval=0.3)

            time.sleep(1.0)
            self.assertEqual(event_bus.last_id, 0)


if __name__ == "__main__":
    unittest.main()
