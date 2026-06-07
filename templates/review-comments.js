(function () {
  "use strict";

  const COMMENTS_URL = "annotations/comments.json";
  const STORAGE_PREFIX = "reviewable-html-comments:";
  const COMMENT_STATUS = Object.freeze({
    needsAgentReview: "needs_agent_review",
    needsUserReply: "needs_user_reply",
    resolved: "resolved",
  });
  const STATUS_VALUES = [
    COMMENT_STATUS.needsAgentReview,
    COMMENT_STATUS.needsUserReply,
    COMMENT_STATUS.resolved,
  ];

  const documentId = document.querySelector("[data-document-id]")?.dataset.documentId || "document";
  const storageKey = STORAGE_PREFIX + documentId;
  const state = {
    comments: { schema_version: "1.0", document_id: documentId, comments: [] },
    selected: null,
    selectionRect: null,
    serverWritable: false,
    ignoreSelectionChange: false,
    threadPinned: false,
  };

  const ui = createUi();
  document.body.appendChild(ui.root);

  document.addEventListener("selectionchange", scheduleSelectionCapture);
  document.addEventListener("keyup", scheduleSelectionCapture);
  document.addEventListener("mouseup", scheduleSelectionCapture);
  document.addEventListener("pointerup", scheduleSelectionCapture);
  document.addEventListener("scroll", hideFloatingUi, true);
  document.addEventListener("click", handleDocumentClick);
  ui.toolbar.addEventListener("mousedown", preserveDocumentSelection);
  ui.commentButton.addEventListener("mousedown", preserveDocumentSelection);
  ui.commentButton.addEventListener("click", openComposerForSelection);
  ui.cancelButton.addEventListener("click", closeComposer);
  ui.saveButton.addEventListener("click", addCommentFromComposer);
  ui.commentBody.addEventListener("keydown", async (event) => {
    if (isSubmitShortcut(event)) {
      event.preventDefault();
      await addCommentFromComposer();
    }
  });
  ui.threadClose.addEventListener("click", closeThreadPopover);
  ui.exportButton.addEventListener("click", exportComments);
  ui.importInput.addEventListener("change", importComments);

  loadComments();

  function createUi() {
    const root = document.createElement("div");
    root.className = "review-comments-root";
    root.innerHTML = [
      '<div class="review-comments-toolbar" data-comments-toolbar hidden>',
      '  <button type="button" data-comment-button>Comment</button>',
      "</div>",
      '<section class="review-comments-composer" data-comments-composer hidden>',
      '  <textarea data-comment-body rows="3" placeholder="Add a comment"></textarea>',
      '  <div class="review-comments-composer-actions">',
      '    <button type="button" data-cancel-comment>Cancel</button>',
      '    <button type="button" data-save-comment>Comment</button>',
      "  </div>",
      "</section>",
      '<section class="review-comments-thread-popover" data-thread-popover hidden>',
      '  <div class="review-comments-thread-header">',
      '    <span data-thread-location></span>',
      '    <button type="button" data-thread-close aria-label="Close">x</button>',
      "  </div>",
      '  <div data-thread-body></div>',
      "</section>",
      '<div class="review-comments-utility">',
      '  <span class="review-comments-status" data-comments-status>standalone</span>',
      '  <button type="button" data-export-comments>Export</button>',
      '  <label class="review-comments-import">Import<input type="file" accept="application/json" data-import-comments></label>',
      "</div>",
    ].join("");
    return {
      root,
      toolbar: root.querySelector("[data-comments-toolbar]"),
      commentButton: root.querySelector("[data-comment-button]"),
      composer: root.querySelector("[data-comments-composer]"),
      commentBody: root.querySelector("[data-comment-body]"),
      cancelButton: root.querySelector("[data-cancel-comment]"),
      saveButton: root.querySelector("[data-save-comment]"),
      threadPopover: root.querySelector("[data-thread-popover]"),
      threadLocation: root.querySelector("[data-thread-location]"),
      threadBody: root.querySelector("[data-thread-body]"),
      threadClose: root.querySelector("[data-thread-close]"),
      exportButton: root.querySelector("[data-export-comments]"),
      importInput: root.querySelector("[data-import-comments]"),
      status: root.querySelector("[data-comments-status]"),
    };
  }

  async function loadComments() {
    const local = readLocalComments();
    try {
      const response = await fetch(COMMENTS_URL, { cache: "no-store" });
      if (response.ok) {
        state.comments = normalizeComments(await response.json());
        state.serverWritable = true;
      } else {
        state.comments = local;
      }
    } catch (_error) {
      state.comments = local;
    }
    writeLocalComments();
    renderComments();
  }

  async function saveComments() {
    writeLocalComments();
    try {
      const response = await fetch(COMMENTS_URL, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state.comments, null, 2),
      });
      state.serverWritable = response.ok;
      setStatus(response.ok ? "comments.json" : "standalone");
      return response.ok;
    } catch (_error) {
      state.serverWritable = false;
      setStatus("standalone");
      return true;
    }
  }

  function scheduleSelectionCapture(event) {
    if (shouldIgnoreSelectionCaptureEvent(event)) {
      return;
    }
    window.setTimeout(captureSelection, 0);
  }

  function shouldIgnoreSelectionCaptureEvent(event) {
    if (!event?.target) {
      return false;
    }
    if (ui.root.contains(event.target)) {
      return true;
    }
    return Boolean(event.target.closest?.("mark[data-comment-highlight], [data-comment-badge]"));
  }

  function captureSelection() {
    if (state.ignoreSelectionChange) {
      return;
    }
    if (ui.root.contains(document.activeElement)) {
      return;
    }
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      setSelected(null);
      return;
    }
    const text = selection.toString().trim();
    if (!text) {
      setSelected(null);
      return;
    }
    const range = selection.getRangeAt(0);
    if (closestCommentHighlight(range.commonAncestorContainer)) {
      ui.toolbar.hidden = true;
      return;
    }
    const block = reviewBlockForRange(range);
    if (!block) {
      setSelected(null);
      return;
    }
    const blockText = block.textContent || "";
    const offset = blockText.indexOf(text);
    const anchor = selectionAnchorInBlock(block, range);
    setSelected(
      {
        blockId: block.dataset.reviewBlock,
        selectedText: text,
        prefix: offset >= 0 ? blockText.slice(Math.max(0, offset - 48), offset) : "",
        suffix: offset >= 0 ? blockText.slice(offset + text.length, offset + text.length + 48) : "",
        anchor,
      },
      getRangeRect(range),
    );
  }

  function openComposerForSelection(event) {
    event.preventDefault();
    event.stopPropagation();
    if (!state.selected || !state.selectionRect) {
      return;
    }
    ui.toolbar.hidden = true;
    showComposerAt(state.selectionRect);
    ui.commentBody.value = "";
    ui.commentBody.focus();
  }

  async function addCommentFromComposer() {
    if (!state.selected) {
      return;
    }
    const comment = ui.commentBody.value;
    if (!comment || !comment.trim()) {
      return;
    }
    state.comments.comments.push({
      id: "cmt_" + Date.now().toString(36),
      document_id: documentId,
      block_id: state.selected.blockId,
      selected_text: state.selected.selectedText,
      prefix: state.selected.prefix,
      suffix: state.selected.suffix,
      anchor: state.selected.anchor,
      comment: comment.trim(),
      status: COMMENT_STATUS.needsAgentReview,
      created_at: new Date().toISOString(),
      replies: [],
    });
    await saveComments();
    renderComments();
    closeComposer();
    window.getSelection()?.removeAllRanges();
  }

  function renderComments() {
    clearReviewHighlights();
    clearBlockCommentBadges();
    for (const block of document.querySelectorAll("[data-review-block]")) {
      block.classList.remove("has-review-comments");
      block.classList.remove("has-review-replies");
    }
    for (const thread of state.comments.comments) {
      const block = document.querySelector(`[data-review-block="${cssEscape(thread.block_id)}"]`);
      if (block && !isResolvedThread(thread)) {
        block.classList.add("has-review-comments");
      }
      if (block && isNeedsUserReply(thread)) {
        block.classList.add("has-review-replies");
      }
      if (block) {
        const highlighted = highlightThreadSelection(block, thread);
        if (!highlighted) {
          addBlockCommentBadge(block, thread);
        }
      }
    }
    setStatus(state.serverWritable ? "comments.json" : "standalone");
  }

  function clearReviewHighlights() {
    for (const mark of document.querySelectorAll("mark[data-comment-highlight]")) {
      const parent = mark.parentNode;
      if (!parent) {
        continue;
      }
      while (mark.firstChild) {
        parent.insertBefore(mark.firstChild, mark);
      }
      parent.removeChild(mark);
      parent.normalize();
    }
  }

  function clearBlockCommentBadges() {
    for (const badge of document.querySelectorAll("[data-comment-badge]")) {
      badge.remove();
    }
  }

  function addBlockCommentBadge(block, thread) {
    const badge = document.createElement("button");
    badge.type = "button";
    badge.className = "review-comment-badge";
    applyThreadMarkerClasses(badge, thread);
    badge.dataset.commentBadge = thread.id || "";
    badge.textContent = "Comment";
    badge.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openThreadPopover(thread, badge.getBoundingClientRect(), { focusReply: true });
    });
    block.appendChild(badge);
  }

  function highlightThreadSelection(block, thread) {
    if (thread.anchor && Number.isInteger(thread.anchor.start) && Number.isInteger(thread.anchor.end)) {
      return highlightByOffsets(block, thread, thread.anchor.start, thread.anchor.end);
    }
    const selectedText = typeof thread.selected_text === "string" ? thread.selected_text.trim() : "";
    if (!selectedText) {
      return false;
    }
    const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.includes(selectedText)) {
          return NodeFilter.FILTER_REJECT;
        }
        if (isSvgTextNode(node)) {
          return NodeFilter.FILTER_REJECT;
        }
        if (node.parentElement?.closest("mark[data-comment-highlight]")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const node = walker.nextNode();
    if (!node) {
      return false;
    }
    const start = node.nodeValue.indexOf(selectedText);
    const range = document.createRange();
    range.setStart(node, start);
    range.setEnd(node, start + selectedText.length);

    const mark = createHighlightMark(thread);
    range.surroundContents(mark);
    return true;
  }

  function highlightByOffsets(block, thread, start, end) {
    if (end <= start) {
      return false;
    }
    const textNodes = textNodesIn(block);
    let position = 0;
    let highlighted = false;
    for (const node of textNodes) {
      const text = node.nodeValue || "";
      const nodeStart = position;
      const nodeEnd = position + text.length;
      const overlapStart = Math.max(start, nodeStart);
      const overlapEnd = Math.min(end, nodeEnd);
      position = nodeEnd;
      if (overlapStart >= overlapEnd) {
        continue;
      }
      if (isSvgTextNode(node)) {
        continue;
      }
      highlighted = wrapTextNodeSlice(node, overlapStart - nodeStart, overlapEnd - nodeStart, thread) || highlighted;
    }
    return highlighted;
  }

  function wrapTextNodeSlice(node, start, end, thread) {
    if (start < 0 || end > node.nodeValue.length || start >= end) {
      return false;
    }
    const range = document.createRange();
    range.setStart(node, start);
    range.setEnd(node, end);
    const mark = createHighlightMark(thread);
    range.surroundContents(mark);
    return true;
  }

  function createHighlightMark(thread) {
    const mark = document.createElement("mark");
    mark.className = "review-comment-highlight";
    applyThreadMarkerClasses(mark, thread);
    mark.dataset.commentHighlight = thread.id || "";
    mark.setAttribute("aria-label", thread.comment || "Review comment");
    mark.tabIndex = 0;
    mark.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openThreadPopover(thread, mark.getBoundingClientRect(), { focusReply: true });
    });
    mark.addEventListener("mouseenter", () => {
      if (!state.threadPinned) {
        openThreadPopover(thread, mark.getBoundingClientRect());
      }
    });
    mark.addEventListener("focus", () => {
      if (!state.threadPinned) {
        openThreadPopover(thread, mark.getBoundingClientRect());
      }
    });
    return mark;
  }

  function applyThreadMarkerClasses(element, thread) {
    element.classList.toggle("has-review-replies", isNeedsUserReply(thread));
    element.classList.toggle("is-review-resolved", isResolvedThread(thread));
  }

  function renderStatus(thread) {
    const options = STATUS_VALUES.map((status) => {
      const selected = status === thread.status ? " selected" : "";
      return `<option value="${status}"${selected}>${status}</option>`;
    }).join("");
    return `<select aria-label="Comment status">${options}</select>`;
  }

  function renderReplies(thread) {
    if (!Array.isArray(thread.replies) || thread.replies.length === 0) {
      return "";
    }
    const replies = thread.replies.map((reply) => {
      return [
        '<li class="review-comment-reply">',
        `  <div class="review-comment-author">${escapeHtml(replyAuthor(reply))}</div>`,
        `  <div class="review-comment-body">${escapeHtml(reply.body)}</div>`,
        "</li>",
      ].join("");
    }).join("");
    return `<ul class="review-comment-replies">${replies}</ul>`;
  }

  function openThreadPopover(thread, rect, options = {}) {
    const focusReply = Boolean(options.focusReply);
    state.selected = null;
    state.selectionRect = null;
    state.threadPinned = focusReply || state.threadPinned;
    clearDocumentSelectionWithoutClosingPopover();
    ui.threadLocation.textContent = thread.block_id;
    ui.threadBody.innerHTML = [
      `<blockquote>${escapeHtml(thread.selected_text)}</blockquote>`,
      '<div class="review-comment-author">You</div>',
      `<div class="review-comment-body review-comment-main-body" data-thread-comment-display tabindex="0">${escapeHtml(thread.comment)}</div>`,
      `<textarea data-thread-comment-editor rows="3" hidden>${escapeHtml(thread.comment)}</textarea>`,
      `<div class="review-comment-status-row">${renderStatus(thread)}</div>`,
      renderReplies(thread),
      '<textarea data-thread-reply rows="1" placeholder="Reply..."></textarea>',
      '<div class="review-comments-thread-actions">',
      '  <button type="button" data-thread-delete>Delete</button>',
      "</div>",
    ].join("");
    ui.threadBody.querySelector("select")?.addEventListener("change", async (event) => {
      thread.status = event.target.value;
      await saveComments();
      renderComments();
      openThreadPopover(thread, rect);
    });
    const commentDisplay = ui.threadBody.querySelector("[data-thread-comment-display]");
    const commentEditor = ui.threadBody.querySelector("[data-thread-comment-editor]");
    commentDisplay?.addEventListener("click", () => {
      enterCommentEditMode(commentDisplay, commentEditor);
    });
    commentEditor?.addEventListener("keydown", async (event) => {
      if (isSubmitShortcut(event)) {
        event.preventDefault();
        await saveEditedComment(thread, rect, commentEditor);
      }
    });
    commentEditor?.addEventListener("blur", async () => {
      await saveEditedComment(thread, rect, commentEditor);
    });
    ui.threadBody.querySelector("[data-thread-delete]")?.addEventListener("click", async () => {
      state.comments.comments = state.comments.comments.filter((item) => item.id !== thread.id);
      await saveComments();
      renderComments();
      closeThreadPopover();
    });
    ui.threadBody.querySelector("[data-thread-reply]")?.addEventListener("keydown", async (event) => {
      if (isReplySubmitShortcut(event)) {
        event.preventDefault();
        await addReplyFromEditor(thread, rect, event.target);
      }
    });
    positionPopover(ui.threadPopover, rect, "below");
    ui.threadPopover.hidden = false;
    ui.composer.hidden = true;
    ui.toolbar.hidden = true;
    if (focusReply) {
      window.setTimeout(() => {
        const replyEditor = ui.threadBody.querySelector("[data-thread-reply]");
        if (replyEditor instanceof HTMLTextAreaElement) {
          replyEditor.focus();
        }
      }, 0);
    }
  }

  function enterCommentEditMode(display, editor) {
    display.hidden = true;
    editor.hidden = false;
    editor.focus();
    editor.setSelectionRange(editor.value.length, editor.value.length);
  }

  async function saveEditedComment(thread, rect, editor) {
    const body = editor.value.trim();
    if (!body || body === thread.comment) {
      openThreadPopover(thread, rect);
      return;
    }
    thread.comment = body;
    await saveComments();
    renderComments();
    openThreadPopover(thread, rect);
  }

  async function addReplyFromEditor(thread, rect, editor) {
    const body = editor.value.trim();
    if (!body) {
      return;
    }
    thread.replies = Array.isArray(thread.replies) ? thread.replies : [];
    const reply = {
      id: "reply_" + Date.now().toString(36),
      author: "user",
      role: "user",
      kind: "note",
      body,
      created_at: new Date().toISOString(),
    };
    thread.replies.push(reply);
    thread.status = COMMENT_STATUS.needsAgentReview;
    await saveComments();
    renderComments();
    openThreadPopover(thread, rect);
    const replyEditor = ui.threadBody.querySelector("[data-thread-reply]");
    if (replyEditor instanceof HTMLTextAreaElement) {
      replyEditor.focus();
    }
  }

  function isSubmitShortcut(event) {
    return event.key === "Enter" && (event.metaKey || event.ctrlKey);
  }

  function isReplySubmitShortcut(event) {
    if (event.isComposing || event.shiftKey) {
      return false;
    }
    return event.key === "Enter";
  }

  function replyAuthor(reply) {
    if (reply.role === "agent") {
      return reply.author || "Codex";
    }
    if (reply.role === "system") {
      return "System";
    }
    return "You";
  }

  function isNeedsUserReply(thread) {
    return thread.status === COMMENT_STATUS.needsUserReply;
  }

  function isResolvedThread(thread) {
    return thread.status === COMMENT_STATUS.resolved;
  }

  function handleDocumentClick(event) {
    if (ui.root.contains(event.target)) {
      return;
    }
    if (event.target.closest?.("mark[data-comment-highlight]")) {
      return;
    }
    if (captureImageBlockClick(event)) {
      return;
    }
    closeComposer();
    closeThreadPopover();
  }

  function captureImageBlockClick(event) {
    const image = event.target.closest?.(".generated-image img");
    if (!image) {
      return false;
    }
    const block = image.closest("[data-review-block]");
    if (!block) {
      return false;
    }
    event.preventDefault();
    event.stopPropagation();
    clearDocumentSelectionForNonTextTarget();
    const title = block.querySelector("h2")?.textContent?.trim();
    const caption = block.querySelector("figcaption")?.textContent?.trim();
    setSelected(
      {
        blockId: block.dataset.reviewBlock,
        selectedText: image.getAttribute("alt") || title || caption || "Image",
        prefix: "",
        suffix: caption || "",
        anchor: null,
      },
      image.getBoundingClientRect(),
    );
    return true;
  }

  function preserveDocumentSelection(event) {
    event.preventDefault();
  }

  function closeComposer() {
    ui.composer.hidden = true;
    ui.commentBody.value = "";
  }

  function closeThreadPopover() {
    ui.threadPopover.hidden = true;
    state.threadPinned = false;
  }

  function clearDocumentSelectionWithoutClosingPopover() {
    clearDocumentSelectionForNonTextTarget();
  }

  function clearDocumentSelectionForNonTextTarget() {
    state.ignoreSelectionChange = true;
    window.getSelection()?.removeAllRanges();
    window.setTimeout(() => {
      state.ignoreSelectionChange = false;
    }, 0);
  }

  function hideFloatingUi() {
    ui.toolbar.hidden = true;
    closeComposer();
    closeThreadPopover();
  }

  function exportComments() {
    const blob = new Blob([JSON.stringify(state.comments, null, 2) + "\n"], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "comments.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function importComments(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.addEventListener("load", async () => {
      state.comments = normalizeComments(JSON.parse(String(reader.result)));
      await saveComments();
      renderComments();
    });
    reader.readAsText(file);
    event.target.value = "";
  }

  function readLocalComments() {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return { schema_version: "1.0", document_id: documentId, comments: [] };
    }
    try {
      return normalizeComments(JSON.parse(raw));
    } catch (_error) {
      return { schema_version: "1.0", document_id: documentId, comments: [] };
    }
  }

  function writeLocalComments() {
    window.localStorage.setItem(storageKey, JSON.stringify(state.comments));
  }

  function normalizeComments(payload) {
    return {
      schema_version: "1.0",
      document_id: typeof payload.document_id === "string" && payload.document_id ? payload.document_id : documentId,
      comments: Array.isArray(payload.comments) ? payload.comments.map(normalizeThread) : [],
    };
  }

  function normalizeThread(thread) {
    return {
      ...thread,
      status: normalizeThreadStatus(thread?.status),
      replies: Array.isArray(thread?.replies) ? thread.replies : [],
    };
  }

  function normalizeThreadStatus(status) {
    return STATUS_VALUES.includes(status) ? status : COMMENT_STATUS.needsAgentReview;
  }

  function setSelected(selection, rect = null) {
    state.selected = selection;
    state.selectionRect = rect;
    closeComposer();
    closeThreadPopover();
    if (!selection || !rect) {
      ui.toolbar.hidden = true;
      return;
    }
    positionPopover(ui.toolbar, rect, "above");
    ui.toolbar.hidden = false;
  }

  function showComposerAt(rect) {
    ui.composer.hidden = false;
    positionPopover(ui.composer, rect, "below");
  }

  function setStatus(label) {
    ui.status.textContent = label;
  }

  function closestReviewBlock(node) {
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    return element?.closest("[data-review-block]");
  }

  function reviewBlockForRange(range) {
    const commonBlock = closestReviewBlock(range.commonAncestorContainer);
    if (commonBlock) {
      return commonBlock;
    }
    const startBlock = closestReviewBlock(range.startContainer);
    const endBlock = closestReviewBlock(range.endContainer);
    if (startBlock && startBlock === endBlock) {
      return startBlock;
    }
    return startBlock || endBlock;
  }

  function closestCommentHighlight(node) {
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    return element?.closest("mark[data-comment-highlight]");
  }

  function getRangeRect(range) {
    const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0);
    return rects[0] || range.getBoundingClientRect();
  }

  function selectionAnchorInBlock(block, range) {
    const textNodes = textNodesIn(block);
    let position = 0;
    let start = null;
    let end = null;
    for (const node of textNodes) {
      const length = (node.nodeValue || "").length;
      if (node === range.startContainer) {
        start = position + range.startOffset;
      }
      if (node === range.endContainer) {
        end = position + range.endOffset;
      }
      position += length;
    }
    if (start === null || end === null || end <= start) {
      return null;
    }
    return { start, end };
  }

  function textNodesIn(root) {
    const nodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue) {
          return NodeFilter.FILTER_REJECT;
        }
        if (node.parentElement?.closest("mark[data-comment-highlight]")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    let node = walker.nextNode();
    while (node) {
      nodes.push(node);
      node = walker.nextNode();
    }
    return nodes;
  }

  function isSvgTextNode(node) {
    return Boolean(node.parentElement?.closest("svg"));
  }

  function positionPopover(element, rect, placement) {
    element.hidden = false;
    element.style.visibility = "hidden";
    const margin = 8;
    const width = element.offsetWidth || 280;
    const height = element.offsetHeight || 40;
    const viewportTop = window.scrollY + 8;
    const viewportBottom = window.scrollY + window.innerHeight - 16;
    const belowTop = window.scrollY + rect.bottom + margin;
    const aboveTop = window.scrollY + rect.top - height - margin;
    const fitsBelow = belowTop + height <= viewportBottom;
    const fitsAbove = aboveTop >= viewportTop;
    let rawTop = placement === "above" ? aboveTop : belowTop;
    if (placement === "below" && !fitsBelow && (fitsAbove || aboveTop > viewportTop)) {
      rawTop = aboveTop;
    } else if (placement === "above" && !fitsAbove && fitsBelow) {
      rawTop = belowTop;
    }
    const rawLeft = window.scrollX + rect.left + rect.width / 2 - width / 2;
    const left = Math.min(window.scrollX + window.innerWidth - width - 16, Math.max(window.scrollX + 16, rawLeft));
    const top = Math.min(viewportBottom - height, Math.max(viewportTop, rawTop));
    element.style.top = `${top}px`;
    element.style.left = `${left}px`;
    element.style.visibility = "";
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return String(value).replace(/"/g, '\\"');
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
