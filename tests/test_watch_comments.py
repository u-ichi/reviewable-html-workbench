"""watch-comments のゲート付与テスト。"""

from pathlib import Path
from unittest.mock import patch
import unittest


class TestCheckGateStatus(unittest.TestCase):
    def test_returns_gate_payload(self):
        from scripts.html_review_workbench.resolution_gate import GateResult
        from scripts.html_review_workbench.watch_comments import _check_gate_status

        result = GateResult(gate="open", blocking_threads=[], resolved_actionable=[])
        with patch("scripts.html_review_workbench.resolution_gate.check_gate", return_value=result):
            payload = _check_gate_status(Path("/tmp/test"))
        self.assertIsNotNone(payload)
        self.assertEqual(payload["gate"], "open")

    def test_returns_none_on_error(self):
        from scripts.html_review_workbench.watch_comments import _check_gate_status

        with patch("scripts.html_review_workbench.resolution_gate.check_gate", side_effect=FileNotFoundError):
            payload = _check_gate_status(Path("/tmp/nonexistent"))
        self.assertIsNone(payload)

    def test_returns_blocking_threads_when_blocked(self):
        from scripts.html_review_workbench.resolution_gate import GateResult
        from scripts.html_review_workbench.watch_comments import _check_gate_status

        result = GateResult(
            gate="blocked",
            blocking_threads=[{"thread_id": "cmt_1", "status": "needs_user_reply"}],
            resolved_actionable=[],
        )
        with patch("scripts.html_review_workbench.resolution_gate.check_gate", return_value=result):
            payload = _check_gate_status(Path("/tmp/test"))
        self.assertEqual(payload["gate"], "blocked")
        self.assertEqual(len(payload["blocking_threads"]), 1)


if __name__ == "__main__":
    unittest.main()
