"""Tests for the resolution gate logic."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.resolution_gate import check_gate, GateResult


def _write_comments(root: Path, threads: list[dict]) -> None:
    path = root / "annotations" / "comments.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "1.0", "document_id": "doc", "comments": threads}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_thread(
    thread_id: str, comment: str, status: str = "needs_agent_review", replies: list | None = None,
) -> dict:
    return {
        "id": thread_id,
        "document_id": "doc",
        "block_id": "block-1",
        "selected_text": "some text",
        "comment": comment,
        "status": status,
        "created_at": "2026-01-01T00:00:00Z",
        "replies": replies or [],
    }


class CheckGateOpenTest(unittest.TestCase):
    def test_gate_open_when_no_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [])
            result = check_gate(root)
            self.assertEqual(result.gate, "open")
            self.assertEqual(result.blocking_threads, [])

    def test_gate_open_when_all_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "Is this correct?", status="resolved"),
                _make_thread("cmt-2", "Fix typo here", status="resolved"),
            ])
            result = check_gate(root)
            self.assertEqual(result.gate, "open")

    def test_gate_open_lists_resolved_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "Fix typo here", status="resolved"),
            ])
            state = {
                "classifications": [
                    {"comment_id": "cmt-1", "classification": "actionable"},
                ],
            }
            state_path = root / "annotations" / "review-cycle-state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            result = check_gate(root)
            self.assertEqual(result.gate, "open")
            self.assertEqual(len(result.resolved_actionable), 1)
            self.assertEqual(result.resolved_actionable[0]["thread_id"], "cmt-1")


class CheckGateBlockedTest(unittest.TestCase):
    def test_gate_blocked_by_unresolved_clarification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "What do you mean by this?", status="needs_user_reply"),
            ])
            result = check_gate(root)
            self.assertEqual(result.gate, "blocked")
            self.assertEqual(len(result.blocking_threads), 1)
            self.assertEqual(result.blocking_threads[0]["thread_id"], "cmt-1")

    def test_gate_blocked_mixed_threads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "Fix typo here", status="resolved"),
                _make_thread("cmt-2", "Should this be X or Y?", status="needs_agent_review"),
            ])
            state = {
                "classifications": [
                    {"comment_id": "cmt-1", "classification": "actionable"},
                    {"comment_id": "cmt-2", "classification": "needs_clarification"},
                ],
            }
            state_path = root / "annotations" / "review-cycle-state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            result = check_gate(root)
            self.assertEqual(result.gate, "blocked")
            self.assertEqual(len(result.blocking_threads), 1)
            self.assertEqual(result.blocking_threads[0]["thread_id"], "cmt-2")
            self.assertEqual(len(result.resolved_actionable), 1)

    def test_actionable_unresolved_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "Fix the typo in this sentence", status="needs_agent_review"),
            ])
            result = check_gate(root)
            self.assertEqual(result.gate, "open")


class CheckGateWithStateTest(unittest.TestCase):
    def test_uses_state_file_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "ambiguous wording", status="needs_user_reply"),
            ])
            state = {
                "classifications": [
                    {"comment_id": "cmt-1", "classification": "needs_clarification"},
                ],
            }
            state_path = root / "annotations" / "review-cycle-state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            result = check_gate(root)
            self.assertEqual(result.gate, "blocked")

    def test_missing_state_file_falls_back_to_classify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "Is this right?", status="needs_agent_review"),
            ])
            result = check_gate(root)
            self.assertEqual(result.gate, "blocked")


class GateResultPayloadTest(unittest.TestCase):
    def test_payload_omits_empty_lists(self) -> None:
        result = GateResult(gate="open", blocking_threads=[], resolved_actionable=[])
        payload = result.to_payload()
        self.assertEqual(payload, {"gate": "open"})

    def test_payload_includes_non_empty_lists(self) -> None:
        result = GateResult(
            gate="blocked",
            blocking_threads=[{"thread_id": "cmt-1", "status": "needs_user_reply"}],
            resolved_actionable=[],
        )
        payload = result.to_payload()
        self.assertIn("blocking_threads", payload)
        self.assertNotIn("resolved_actionable", payload)


if __name__ == "__main__":
    unittest.main()
