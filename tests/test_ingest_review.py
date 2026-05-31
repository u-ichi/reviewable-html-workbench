from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.ingest_review import (
    COMMENT_STATUS_VALUES,
    INGESTION_CLASSIFICATIONS,
    ingest_review,
)


ROOT = Path(__file__).resolve().parents[1]


class IngestReviewTest(unittest.TestCase):
    def test_ingest_review_classifies_threads_adds_reply_and_writes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(
                root,
                [
                    _thread("cmt-action", "overview", "minimal section", 'Replace "minimal section" with "short section".'),
                    _thread("cmt-clarify", "overview", "future renderer tests", "Should this become a card?"),
                    _thread("cmt-blocked", "overview", "future renderer tests", "Blocked: source is missing."),
                    _thread("cmt-done", "overview", "future renderer tests", "Already fixed.", status="resolved"),
                ],
            )

            result = ingest_review(root)

            self.assertEqual(result.payload["summary"]["total"], 4)
            self.assertEqual(result.payload["summary"]["actionable"], 1)
            self.assertEqual(result.payload["summary"]["needs_clarification"], 1)
            self.assertEqual(result.payload["summary"]["blocked"], 1)
            self.assertEqual(result.payload["summary"]["already_addressed"], 1)
            self.assertEqual(result.payload["summary"]["replies_added"], 1)

            comments = json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))
            clarify = _find_thread(comments, "cmt-clarify")
            self.assertEqual(clarify["status"], "needs_user_reply")
            self.assertEqual(clarify["replies"][0]["role"], "agent")
            self.assertEqual(clarify["replies"][0]["kind"], "clarification_request")

            state = json.loads((root / "annotations/review-cycle-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["actionable_comment_ids"], ["cmt-action"])
            self.assertEqual(state["blocked_comment_ids"], ["cmt-blocked"])
            self.assertEqual(state["needs_clarification_comment_ids"], ["cmt-clarify"])

    def test_ingestion_classification_is_separate_from_comment_status(self) -> None:
        self.assertEqual(set(COMMENT_STATUS_VALUES), {"needs_agent_review", "needs_user_reply", "resolved"})
        self.assertEqual(
            set(INGESTION_CLASSIFICATIONS),
            {"actionable", "needs_clarification", "blocked", "already_addressed"},
        )
        self.assertTrue(set(COMMENT_STATUS_VALUES).isdisjoint(INGESTION_CLASSIFICATIONS))

        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        status_block = script[script.index("const COMMENT_STATUS") : script.index("const STATUS_VALUES")]
        for classification in INGESTION_CLASSIFICATIONS:
            self.assertNotIn(classification, status_block)

    def test_apply_model_uses_limited_exact_replacement_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "document-model.json"
            model_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "document_id": "minimal-design-doc",
                        "title": "Minimal Design Doc",
                        "generated_at": "2026-05-17T00:00:00+09:00",
                        "blocks": [
                            {
                                "id": "overview",
                                "type": "section",
                                "content": "A minimal section for future renderer tests.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            _write_comments(
                root,
                [
                    _thread(
                        "cmt-replace",
                        "overview",
                        "future renderer tests",
                        'Replace "future renderer tests" with "review workflow checks".',
                    )
                ],
            )

            result = ingest_review(root, model_path=model_path, apply_model=True)

            model = json.loads(model_path.read_text(encoding="utf-8"))
            self.assertEqual(model["blocks"][0]["content"], "A minimal section for review workflow checks.")
            self.assertEqual(result.payload["model_updates"]["applied"], 1)
            self.assertEqual(result.payload["summary"]["replies_added"], 1)
            comments = json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))
            applied = _find_thread(comments, "cmt-replace")
            self.assertEqual(applied["status"], "resolved")
            self.assertEqual(applied["replies"][0]["role"], "agent")
            self.assertEqual(applied["replies"][0]["kind"], "implementation_note")
            state = json.loads((root / "annotations/review-cycle-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["summary"]["model_updates_applied"], 1)
            self.assertEqual(state["classifications"][0]["status_after"], "resolved")


def _write_comments(root: Path, threads: list[dict[str, object]]) -> None:
    annotations = root / "annotations"
    annotations.mkdir(parents=True)
    payload = {"schema_version": "1.0", "document_id": "minimal-design-doc", "comments": threads}
    (annotations / "comments.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _thread(
    thread_id: str,
    block_id: str,
    selected_text: str,
    comment: str,
    *,
    status: str = "needs_agent_review",
) -> dict[str, object]:
    return {
        "id": thread_id,
        "document_id": "minimal-design-doc",
        "block_id": block_id,
        "selected_text": selected_text,
        "prefix": "",
        "suffix": "",
        "comment": comment,
        "status": status,
        "created_at": "2026-05-17T00:00:00+00:00",
        "replies": [],
    }


def _find_thread(payload: dict[str, object], thread_id: str) -> dict[str, object]:
    for thread in payload["comments"]:
        if isinstance(thread, dict) and thread["id"] == thread_id:
            return thread
    raise AssertionError(f"missing thread: {thread_id}")


if __name__ == "__main__":
    unittest.main()
