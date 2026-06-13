from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewCommentsJavaScriptTest(unittest.TestCase):
    def test_review_comments_js_keeps_hardening_boundaries_visible(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        for function_name in [
            "loadComments",
            "saveComments",
            "scheduleSelectionCapture",
            "shouldIgnoreSelectionCaptureEvent",
            "selectionAnchorInBlock",
            "captureImageBlockClick",
            "clearDocumentSelectionForNonTextTarget",
            "reviewBlockForRange",
            "renderCommentCards",
            "positionCards",
            "activate",
            "threadCardState",
            "normalizeThreadStatus",
        ]:
            self.assertIn(f"function {function_name}", script)

    def test_line_selection_uses_deferred_capture_and_range_endpoint_fallback(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn('document.addEventListener("pointerup", scheduleSelectionCapture)', script)
        self.assertIn("shouldIgnoreSelectionCaptureEvent(event)", script)
        self.assertIn("ui.root.contains(event.target)", script)
        self.assertIn('.cx[data-comment], [data-comment-badge]', script)
        self.assertIn("window.setTimeout(captureSelection, 0)", script)
        self.assertIn("closestReviewBlock(range.startContainer)", script)
        self.assertIn("closestReviewBlock(range.endContainer)", script)

    def test_image_block_click_creates_commentable_selection(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn('event.target.closest?.(".generated-image img")', script)
        self.assertIn("clearDocumentSelectionForNonTextTarget()", script)
        self.assertIn('selectedText: image.getAttribute("alt")', script)
        self.assertIn("image.getBoundingClientRect()", script)

    def test_comment_click_links_highlight_and_margin_card(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn('className = "cx"', script)
        self.assertIn('highlight.dataset.comment = thread.id || ""', script)
        self.assertIn('highlight.dataset.state = threadCardState(thread)', script)
        self.assertIn('card.className = "cmt"', script)
        self.assertIn('card.dataset.cstate = cardState', script)
        self.assertIn('card.dataset.for = thread.id || ""', script)
        self.assertIn('document.querySelectorAll(".cx.is-active, .cmt.is-active")', script)
        self.assertIn("card.scrollIntoView({ behavior: \"smooth\", block: \"nearest\" })", script)

    def test_review_comments_js_does_not_mix_ingestion_classification_into_ui_status(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        status_block = script[script.index("const COMMENT_STATUS") : script.index("const STATUS_VALUES")]

        for classification in ["actionable", "needs_clarification", "blocked", "already_addressed"]:
            self.assertNotIn(classification, status_block)


if __name__ == "__main__":
    unittest.main()
