from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.comment_store import (
    CommentStore,
    CommentStoreError,
    empty_comments,
    resolve_comments_path,
)


class CommentStoreTest(unittest.TestCase):
    def test_comment_store_writes_threads_replies_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CommentStore(Path(tmp))

            thread = store.add_thread(
                document_id="doc-1",
                block_id="overview",
                selected_text="selected text",
                prefix="before ",
                suffix=" after",
                comment="Please clarify this.",
                created_at="2026-05-17T00:00:00+00:00",
            )
            reply = store.add_reply(
                document_id="doc-1",
                thread_id=thread["id"],
                author="codex",
                role="agent",
                kind="clarification_request",
                body="Which audience should this target?",
                created_at="2026-05-17T00:01:00+00:00",
            )
            agent_reply_payload = store.read("doc-1")
            self.assertEqual(agent_reply_payload["comments"][0]["status"], "needs_user_reply")
            store.add_reply(
                document_id="doc-1",
                thread_id=thread["id"],
                author="user",
                role="user",
                kind="note",
                body="Target product reviewers.",
                created_at="2026-05-17T00:02:00+00:00",
            )
            user_reply_payload = store.read("doc-1")
            self.assertEqual(user_reply_payload["comments"][0]["status"], "needs_agent_review")
            updated = store.update_status(document_id="doc-1", thread_id=thread["id"], status="needs_user_reply")

            payload = store.read("doc-1")

            self.assertEqual(payload["document_id"], "doc-1")
            self.assertEqual(payload["comments"][0]["id"], thread["id"])
            self.assertEqual(payload["comments"][0]["replies"][0]["id"], reply["id"])
            self.assertEqual(len(payload["comments"][0]["replies"]), 2)
            self.assertEqual(updated["status"], "needs_user_reply")

    def test_comment_store_rejects_paths_outside_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(CommentStoreError, "relative"):
                resolve_comments_path(root, str(root / "comments.json"))
            with self.assertRaisesRegex(CommentStoreError, "parent traversal"):
                resolve_comments_path(root, "../comments.json")

    def test_comment_store_validates_payload_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CommentStore(Path(tmp))
            payload = empty_comments("doc-1")
            payload["comments"].append(
                {
                    "id": "cmt-invalid",
                    "document_id": "doc-1",
                    "block_id": "overview",
                    "selected_text": "selection",
                    "comment": "body",
                    "status": "waiting",
                    "created_at": "2026-05-17T00:00:00+00:00",
                    "replies": [],
                }
            )

            with self.assertRaisesRegex(CommentStoreError, "status"):
                store.write(payload)


if __name__ == "__main__":
    unittest.main()
