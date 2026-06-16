from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AddReplyCliTest(unittest.TestCase):
    def test_add_reply_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-1")])

            result = _run_cli("add-reply", "--root", str(root), "--thread-id", "cmt-1", "--body", "Applied this change.")

            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "ok")
            self.assertEqual(output["thread_id"], "cmt-1")
            self.assertEqual(output["thread_status"], "needs_user_reply")
            self.assertTrue(output["reply_id"].startswith("reply_"))

            thread = _read_comments(root)["comments"][0]
            self.assertEqual(thread["status"], "needs_user_reply")
            self.assertEqual(len(thread["replies"]), 1)
            self.assertEqual(thread["replies"][0]["role"], "agent")
            self.assertEqual(thread["replies"][0]["kind"], "answer")
            self.assertEqual(thread["replies"][0]["body"], "Applied this change.")

    def test_add_reply_reports_thread_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-1")])

            result = _run_cli(
                "add-reply",
                "--root",
                str(root),
                "--thread-id",
                "missing-thread",
                "--body",
                "This should not be written.",
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "failed")
            self.assertIn("comment thread not found: missing-thread", output["error"])

            thread = _read_comments(root)["comments"][0]
            self.assertEqual(thread["replies"], [])

    def test_add_reply_accepts_custom_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-1")])

            _run_cli(
                "add-reply",
                "--root",
                str(root),
                "--thread-id",
                "cmt-1",
                "--kind",
                "implementation_note",
                "--body",
                "Implemented by updating the renderer.",
            )

            reply = _read_comments(root)["comments"][0]["replies"][0]
            self.assertEqual(reply["kind"], "implementation_note")
            self.assertEqual(reply["body"], "Implemented by updating the renderer.")

    def test_add_reply_coexists_with_ingest_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-clarify", comment="Which audience should this target?")])

            _run_cli(
                "add-reply",
                "--root",
                str(root),
                "--thread-id",
                "cmt-clarify",
                "--kind",
                "clarification_request",
                "--body",
                "Please specify the target audience.",
            )
            _run_cli("ingest-review", "--root", str(root))

            comments = _read_comments(root)
            self.assertEqual(len(comments["comments"][0]["replies"]), 1)
            self.assertEqual(comments["comments"][0]["status"], "needs_user_reply")

            state = json.loads((root / "annotations/review-cycle-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["summary"]["total"], 1)
            self.assertEqual(state["summary"]["already_addressed"], 1)
            self.assertEqual(state["summary"]["replies_added"], 0)


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scripts.html_review_workbench.cli", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def _write_comments(root: Path, threads: list[dict[str, object]]) -> None:
    annotations = root / "annotations"
    annotations.mkdir(parents=True)
    payload = {"schema_version": "1.0", "document_id": "doc-1", "comments": threads}
    (annotations / "comments.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_comments(root: Path) -> dict[str, object]:
    return json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))


def _thread(thread_id: str, *, comment: str = "Please update this section.") -> dict[str, object]:
    return {
        "id": thread_id,
        "document_id": "doc-1",
        "block_id": "overview",
        "selected_text": "selected text",
        "prefix": "",
        "suffix": "",
        "comment": comment,
        "status": "needs_agent_review",
        "created_at": "2026-05-17T00:00:00+00:00",
        "replies": [],
    }


if __name__ == "__main__":
    unittest.main()
