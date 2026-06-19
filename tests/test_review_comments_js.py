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
            "initPublishToggle",
            "setPublished",
            "buildPublishedDoc",
            "downloadPublishedDoc",
            "threadCardState",
            "normalizeThreadStatus",
            "showSaveError",
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

    def test_filter_visibility_keeps_highlight_text_visible(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        filter_block = script[script.index("function applyFilterVisibility") : script.index("function shouldShowThreadByFilter")]

        self.assertIn('highlight.querySelectorAll(".cx-num").forEach((badge) => {', filter_block)
        self.assertIn("badge.hidden = !visible;", filter_block)
        self.assertNotIn("highlight.hidden = !visible;", filter_block)

    def test_review_comments_js_does_not_mix_ingestion_classification_into_ui_status(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        status_block = script[script.index("const COMMENT_STATUS") : script.index("const STATUS_VALUES")]

        for classification in ["actionable", "needs_clarification", "blocked", "already_addressed"]:
            self.assertNotIn(classification, status_block)

    def test_publish_preview_exports_clean_html_without_review_runtime(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn("initPublishToggle();", script)
        self.assertIn('document.body.classList.contains("is-published")', script)
        self.assertIn('document.querySelector("#canvas .doc-shell")', script)
        self.assertIn('clone.querySelectorAll(".toc, .cmt-rail, .doc-status, .byline, .cx-num")', script)
        self.assertIn('clone.querySelectorAll(".cx")', script)
        self.assertIn('clone.querySelectorAll(".review-comment-highlight")', script)
        self.assertIn('clone.querySelectorAll(".review-comment-badge")', script)
        self.assertIn('"<body class=\\"is-published\\">\\n"', script)
        self.assertIn("const css = await collectCSS();", script)
        self.assertIn("toast(t.publishToast);", script)

    def test_published_i18n_keys_exist(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        ja_block = script[script.index("ja: {") : script.index("},\n    en: {")]
        en_block = script[script.index("en: {") : script.index("},\n  });")]

        for key in [
            "publishLabel",
            "publishActive",
            "publishTitle",
            "publishStandard",
            "publishMax",
            "publishDownload",
            "publishExit",
            "publishExitLabel",
            "publishToast",
        ]:
            self.assertIn(f"{key}:", ja_block)
            self.assertIn(f"{key}:", en_block)

    def test_published_escape_handler(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        start = script.index("function initPublishToggle()")
        publish_block = script[start : script.index("function setPublished", start)]

        self.assertIn('event.key === "Escape"', publish_block)
        self.assertIn("is-published", publish_block)

    def test_sse_functions_exist(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        for function_name in [
            "initEventSource",
            "fetchAndMergeComments",
            "mergeRemoteComments",
            "showUpdateBanner",
        ]:
            self.assertIn(f"function {function_name}", script)

    def test_sse_i18n_keys_exist(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        ja_block = script[script.index("ja: {") : script.index("},\n    en: {")]
        en_block = script[script.index("en: {") : script.index("},\n  });")]

        for key in ["agentReplied", "docUpdated", "reloadBtn", "closeBtn"]:
            self.assertIn(f"{key}:", ja_block, f"Missing ja i18n key: {key}")
            self.assertIn(f"{key}:", en_block, f"Missing en i18n key: {key}")

    def test_save_comments_surfaces_server_errors(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        save_block = script[script.index("async function saveComments") : script.index("function scheduleSelectionCapture")]
        ja_block = script[script.index("ja: {") : script.index("},\n    en: {")]
        en_block = script[script.index("en: {") : script.index("},\n  });")]

        self.assertIn("function showSaveError", script)
        self.assertIn("var body = await response.json();", save_block)
        self.assertIn("showSaveError(errorMessage);", save_block)
        self.assertIn("saveError:", ja_block)
        self.assertIn("saveError:", en_block)

    def test_event_source_initialized_after_load(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        load_block = script[script.index("loadComments().then") : script.index("function createUi")]

        self.assertIn("loadComments().then(function ()", load_block)
        self.assertIn("schedulePositionCards();", load_block)
        self.assertIn("initEventSource();", script)

    def test_event_source_opens_events_endpoint(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        init_block = script[script.index("function initEventSource()") : script.index("function fetchAndMergeComments")]

        self.assertIn('if (typeof EventSource === "undefined")', init_block)
        self.assertIn('var es = new EventSource("/events");', init_block)
        self.assertIn('es.addEventListener("comment_updated"', init_block)
        self.assertIn('es.addEventListener("document_updated"', init_block)

    def test_comment_updated_refreshes_remote_comments_except_browser_source(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        init_block = script[script.index("function initEventSource()") : script.index("function fetchAndMergeComments")]
        fetch_block = script[script.index("async function fetchAndMergeComments()") : script.index("function mergeRemoteComments")]

        self.assertIn("var data = JSON.parse(event.data);", init_block)
        self.assertIn('if (data.source === "browser")', init_block)
        self.assertIn("return;", init_block)
        self.assertIn("fetchAndMergeComments();", init_block)
        self.assertIn('fetch(COMMENTS_URL, { cache: "no-store" })', fetch_block)
        self.assertIn("mergeRemoteComments(payload);", fetch_block)

    def test_status_buttons_refresh_thread_without_full_document_rerender(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        resolve_block = script[
            script.index('card.querySelector("[data-thread-resolve]")') :
            script.index('card.querySelector("[data-thread-delete]")')
        ]
        status_block = script[script.index("async function updateThreadStatus") : script.index("function renderReplies")]

        self.assertIn("await updateThreadStatus(thread, COMMENT_STATUS.resolved);", resolve_block)
        self.assertIn("await updateThreadStatus(thread, COMMENT_STATUS.needsAgentReview);", resolve_block)
        self.assertNotIn("renderComments();", resolve_block)
        self.assertIn("await saveComments();", status_block)
        self.assertIn("refreshThreadDisplay(thread);", status_block)
        self.assertIn("function replaceCommentCard(thread)", status_block)
        self.assertIn("current.replaceWith(createCommentCard(thread, index + 1));", status_block)
        self.assertIn("function updateThreadAnchors(thread)", status_block)
        self.assertIn("element.dataset.state = threadCardState(thread);", status_block)
        self.assertIn("function updateBlockCommentState(blockId)", status_block)
        self.assertIn('block.classList.toggle("has-review-comments"', status_block)
        self.assertIn('block.classList.toggle("has-review-replies"', status_block)

    def test_remote_comment_merge_refreshes_existing_threads_without_full_document_rerender(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        merge_block = script[script.index("function mergeRemoteComments") : script.index("function showUpdateBanner")]

        self.assertIn("state.comments.comments.push(newThread);", merge_block)
        self.assertIn("old.replies = newThread.replies;", merge_block)
        self.assertIn("old.status = newThread.status;", merge_block)
        self.assertIn("var hasNewThread = false;", merge_block)
        self.assertIn("var changedExistingThreads = [];", merge_block)
        self.assertIn("var hasAgent = addedReplies.some", merge_block)
        self.assertIn("changed = true;", merge_block)
        self.assertIn("if (hasNewThread) {", merge_block)
        self.assertIn("renderComments();", merge_block)
        self.assertIn("changedExistingThreads.forEach(refreshThreadDisplay);", merge_block)
        self.assertIn("toast(t.agentReplied);", merge_block)
        self.assertNotIn("updateCardStatus(old.id, newThread)", merge_block)

    def test_document_updated_banner_requires_manual_reload(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        document_event_block = script[
            script.index('es.addEventListener("document_updated"') : script.index('es.addEventListener("error"')
        ]
        banner_block = script[script.index("function showUpdateBanner") :]

        self.assertIn("showUpdateBanner(message);", document_event_block)
        self.assertNotIn("window.location.reload()", document_event_block)
        self.assertIn('class="rub-reload"', banner_block)
        self.assertIn('banner.querySelector(".rub-reload").addEventListener("click"', banner_block)
        self.assertIn("window.location.reload();", banner_block)


if __name__ == "__main__":
    unittest.main()
