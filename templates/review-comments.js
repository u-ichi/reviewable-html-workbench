(function () {
  "use strict";

  const I18N = Object.freeze({
    ja: {
      cardState: { open: "未対応", reply: "返信あり", resolved: "解決済み" },
      railLabel: "レビューコメント",
      railHeader: "レビュー",
      resolvedBanner: "解決済みにしました",
      replyPlaceholder: "返信を入力…",
      replyLabel: "返信",
      submitBtn: "送信",
      resolveBtn: "解決",
      reopenBtn: "再オープン",
      deleteBtn: "削除",
      commentCount: function (u, t) { return u + " 件未解決 / " + t + " 件"; },
      focusLabel: "最大化",
      normalLabel: "標準表示",
      filterAll: "すべて",
      filterHideResolved: "未解決のみ",
      filterOnlyOpen: "未対応のみ",
      filterLabel: "レビューフィルタ",
      focusTitle: "最大化モード",
      themeTitle: "テーマ切替",
      tocLabel: "目次",
      tocHeader: "目次",
      publishLabel: "公開プレビュー",
      publishActive: "プレビュー中",
      publishTitle: "公開プレビュー",
      publishStandard: "標準",
      publishMax: "最大化",
      publishDownload: "公開用HTMLを書き出し",
      publishExit: "編集に戻る",
      publishExitLabel: "公開プレビュー",
      publishToast: "公開用HTMLを書き出しました",
      agentReplied: "エージェントが返信しました",
      docUpdated: "ドキュメントが更新されました。リロードして最新版を確認できます",
      saveError: "コメント保存エラー: ",
      reloadBtn: "リロード",
      closeBtn: "閉じる",
    },
    en: {
      cardState: { open: "Open", reply: "Has reply", resolved: "Resolved" },
      railLabel: "Review comments",
      railHeader: "Review",
      resolvedBanner: "Marked as resolved",
      replyPlaceholder: "Write a reply…",
      replyLabel: "Reply",
      submitBtn: "Send",
      resolveBtn: "Resolve",
      reopenBtn: "Reopen",
      deleteBtn: "Delete",
      commentCount: function (u, t) { return u + " unresolved / " + t + " total"; },
      focusLabel: "Maximize",
      normalLabel: "Normal",
      filterAll: "All",
      filterHideResolved: "Unresolved only",
      filterOnlyOpen: "Open only",
      filterLabel: "Review filter",
      focusTitle: "Maximize mode",
      themeTitle: "Toggle theme",
      tocLabel: "Table of contents",
      tocHeader: "Contents",
      publishLabel: "Publish preview",
      publishActive: "Previewing",
      publishTitle: "Publish preview",
      publishStandard: "Standard",
      publishMax: "Maximize",
      publishDownload: "Export published HTML",
      publishExit: "Back to edit",
      publishExitLabel: "Published preview",
      publishToast: "Published HTML exported",
      agentReplied: "Agent replied",
      docUpdated: "Document has been updated. Reload to see the latest version.",
      saveError: "Comment save error: ",
      reloadBtn: "Reload",
      closeBtn: "Close",
    },
  });

  const lang = document.documentElement.lang === "ja" ? "ja" : "en";
  const t = I18N[lang];

  const COMMENTS_URL = "annotations/comments.json";
  const STORAGE_PREFIX = "reviewable-html-comments:";
  const THEME_STORAGE_KEY = "reviewable-theme";
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
    activeCommentId: null,
    filter: "all",
    positionFrame: 0,
  };

  initI18nLabels();

  const ui = createUi();
  document.body.appendChild(ui.root);

  initThemeToggle();
  initFilter();
  initFocusToggle();
  initPublishToggle();
  initTocScrollSpy();

  document.addEventListener("selectionchange", scheduleSelectionCapture);
  document.addEventListener("keyup", scheduleSelectionCapture);
  document.addEventListener("mouseup", scheduleSelectionCapture);
  document.addEventListener("pointerup", scheduleSelectionCapture);
  document.addEventListener("scroll", hideFloatingUi, true);
  document.addEventListener("click", handleDocumentClick);
  window.addEventListener("resize", schedulePositionCards);
  window.addEventListener("load", schedulePositionCards);
  document.fonts?.ready?.then(schedulePositionCards);
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
  ui.exportButton.addEventListener("click", exportComments);
  ui.importInput.addEventListener("change", importComments);

  loadComments().then(function () {
    schedulePositionCards();
    initEventSource();
  });

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
      '<div class="review-comments-utility">',
      '  <span class="review-comments-status" data-comments-status>standalone</span>',
      '  <button type="button" data-export-comments>Export</button>',
      '  <label class="review-comments-import">Import<input type="file" accept="application/json" data-import-comments></label>',
      "</div>",
    ].join("");
    const commentRail = ensureCommentRail();
    return {
      root,
      toolbar: root.querySelector("[data-comments-toolbar]"),
      commentButton: root.querySelector("[data-comment-button]"),
      composer: root.querySelector("[data-comments-composer]"),
      commentBody: root.querySelector("[data-comment-body]"),
      cancelButton: root.querySelector("[data-cancel-comment]"),
      saveButton: root.querySelector("[data-save-comment]"),
      exportButton: root.querySelector("[data-export-comments]"),
      importInput: root.querySelector("[data-import-comments]"),
      status: root.querySelector("[data-comments-status]"),
      commentRail,
      commentLayer: commentRail.querySelector("#cmtLayer"),
      commentCount: commentRail.querySelector("#cmtCount"),
    };
  }

  function ensureCommentRail() {
    const existingLayer = document.getElementById("cmtLayer");
    if (existingLayer) {
      return existingLayer.closest(".cmt-rail") || existingLayer.parentElement;
    }
    const rail = document.createElement("aside");
    rail.className = "cmt-rail review-comments-margin-rail";
    rail.setAttribute("aria-label", t.railLabel);
    rail.innerHTML = [
      '<div class="cmt-rail-h">',
      "  <span>" + t.railHeader + "</span>",
      '  <span class="cmt-rail-count" id="cmtCount">—</span>',
      "</div>",
      '<div class="cmt-layer" id="cmtLayer"></div>',
    ].join("");
    document.body.appendChild(rail);
    return rail;
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
      if (response.ok) {
        state.serverWritable = true;
        setStatus("comments.json");
      } else {
        var errorMessage = "";
        try {
          var body = await response.json();
          errorMessage = body.error || "";
        } catch (_parseErr) { /* ignore */ }
        state.serverWritable = false;
        setStatus("standalone");
        showSaveError(errorMessage);
      }
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
    if (ui.root.contains(event.target) || ui.commentRail?.contains(event.target)) {
      return true;
    }
    return Boolean(event.target.closest?.(".cx[data-comment], [data-comment-badge]"));
  }

  function captureSelection() {
    if (document.body.classList.contains("is-published")) {
      return;
    }
    if (state.ignoreSelectionChange) {
      return;
    }
    if (ui.root.contains(document.activeElement) || ui.commentRail?.contains(document.activeElement)) {
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
    const thread = {
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
    };
    state.comments.comments.push(thread);
    await saveComments();
    renderComments();
    activate(thread.id, true);
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
    state.comments.comments.forEach((thread, index) => {
      const block = document.querySelector(`[data-review-block="${cssEscape(thread.block_id)}"]`);
      if (block && !isResolvedThread(thread)) {
        block.classList.add("has-review-comments");
      }
      if (block && isNeedsUserReply(thread)) {
        block.classList.add("has-review-replies");
      }
      if (block) {
        const highlighted = highlightThreadSelection(block, thread, index + 1);
        if (!highlighted) {
          addBlockCommentBadge(block, thread, index + 1);
        }
      }
    });
    renderCommentCards();
    applyFilterVisibility();
    setStatus(state.serverWritable ? "comments.json" : "standalone");
    schedulePositionCards();
  }

  function clearReviewHighlights() {
    for (const highlight of document.querySelectorAll(".cx[data-comment]:not([data-comment-badge])")) {
      const parent = highlight.parentNode;
      if (!parent) {
        continue;
      }
      highlight.querySelectorAll(".cx-num").forEach((badge) => badge.remove());
      while (highlight.firstChild) {
        parent.insertBefore(highlight.firstChild, highlight);
      }
      parent.removeChild(highlight);
      parent.normalize();
    }
  }

  function clearBlockCommentBadges() {
    for (const badge of document.querySelectorAll("[data-comment-badge]")) {
      badge.remove();
    }
  }

  function addBlockCommentBadge(block, thread, number) {
    const badge = document.createElement("button");
    badge.type = "button";
    badge.className = "cx review-comment-badge";
    badge.dataset.comment = thread.id || "";
    badge.dataset.commentBadge = thread.id || "";
    badge.dataset.state = threadCardState(thread);
    badge.textContent = `Comment ${number}`;
    badge.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      activate(thread.id, true);
    });
    block.appendChild(badge);
  }

  function highlightThreadSelection(block, thread, number) {
    if (thread.anchor && Number.isInteger(thread.anchor.start) && Number.isInteger(thread.anchor.end)) {
      return highlightByOffsets(block, thread, thread.anchor.start, thread.anchor.end, number);
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
        if (node.parentElement?.closest(".cx[data-comment]")) {
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
    const highlight = createHighlightElement(thread);
    range.surroundContents(highlight);
    appendHighlightNumber(highlight, number);
    return true;
  }

  function highlightByOffsets(block, thread, start, end, number) {
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
      const includeNumber = !highlighted;
      highlighted = wrapTextNodeSlice(node, overlapStart - nodeStart, overlapEnd - nodeStart, thread, includeNumber ? number : null) || highlighted;
    }
    return highlighted;
  }

  function wrapTextNodeSlice(node, start, end, thread, number) {
    if (start < 0 || end > node.nodeValue.length || start >= end) {
      return false;
    }
    const range = document.createRange();
    range.setStart(node, start);
    range.setEnd(node, end);
    const highlight = createHighlightElement(thread);
    range.surroundContents(highlight);
    if (number) {
      appendHighlightNumber(highlight, number);
    }
    return true;
  }

  function createHighlightElement(thread) {
    const highlight = document.createElement("span");
    highlight.className = "cx";
    highlight.dataset.comment = thread.id || "";
    highlight.dataset.state = threadCardState(thread);
    highlight.setAttribute("aria-label", thread.comment || "Review comment");
    highlight.tabIndex = 0;
    highlight.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      activate(thread.id, true);
    });
    highlight.addEventListener("focus", () => activate(thread.id, false));
    return highlight;
  }

  function appendHighlightNumber(highlight, number) {
    const badge = document.createElement("span");
    badge.className = "cx-num";
    badge.textContent = String(number);
    highlight.appendChild(badge);
  }

  function renderCommentCards() {
    if (!ui.commentLayer) {
      return;
    }
    ui.commentLayer.innerHTML = "";
    state.comments.comments.forEach((thread, index) => {
      ui.commentLayer.appendChild(createCommentCard(thread, index + 1));
    });
    updateCommentCount();
    if (state.activeCommentId) {
      setActiveClasses(state.activeCommentId);
    }
  }

  function createCommentCard(thread, number) {
    const card = document.createElement("aside");
    const cardState = threadCardState(thread);
    card.className = "cmt";
    card.dataset.cstate = cardState;
    card.dataset.for = thread.id || "";
    card.id = cardId(thread.id);
    card.tabIndex = 0;
    card.innerHTML = cardInner(thread, number);
    bindCommentCard(card, thread);
    return card;
  }

  function cardInner(thread, number) {
    const cardState = threadCardState(thread);
    const replies = renderReplies(thread);
    const resolvedBanner = cardState === "resolved"
      ? '<div class="cmt-resolved-by">' + t.resolvedBanner + '</div>'
      : "";
    const replyInput = cardState === "resolved"
      ? ""
      : [
          '<div class="cmt-foot">',
          '  <textarea class="cmt-input" data-thread-reply rows="2" placeholder="' + t.replyPlaceholder + '" aria-label="' + t.replyLabel + '"></textarea>',
          '  <button type="button" class="btn primary" data-thread-reply-submit>' + t.submitBtn + '</button>',
          "</div>",
        ].join("");
    const statusAction = cardState === "resolved"
      ? '<button type="button" class="btn reopen" data-thread-reopen>' + t.reopenBtn + '</button>'
      : '<button type="button" class="btn resolve" data-thread-resolve>' + t.resolveBtn + '</button>';
    return [
      '<div class="cmt-head">',
      '  <div class="cmt-author"><span class="av">You</span> <span>Reviewer</span></div>',
      `  <span class="cmt-state">${escapeHtml(t.cardState[cardState])}</span>`,
      "</div>",
      `<blockquote class="cmt-quote">${escapeHtml(thread.selected_text || thread.block_id || `Comment ${number}`)}</blockquote>`,
      `<div class="cmt-body review-comment-main-body" data-thread-comment-display tabindex="0">${escapeHtml(thread.comment || "")}</div>`,
      `<textarea data-thread-comment-editor rows="3" hidden>${escapeHtml(thread.comment || "")}</textarea>`,
      replies,
      resolvedBanner,
      replyInput,
      '<div class="cmt-foot">',
      `  ${statusAction}`,
      '  <button type="button" class="btn ghost" data-thread-delete>' + t.deleteBtn + '</button>',
      "</div>",
    ].join("");
  }

  function bindCommentCard(card, thread) {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button, textarea, select")) {
        return;
      }
      activate(thread.id, false);
    });
    card.addEventListener("focus", () => activate(thread.id, false));
    card.querySelector("[data-thread-comment-display]")?.addEventListener("click", (event) => {
      event.stopPropagation();
      const display = event.currentTarget;
      const editor = card.querySelector("[data-thread-comment-editor]");
      enterCommentEditMode(display, editor);
    });
    const commentEditor = card.querySelector("[data-thread-comment-editor]");
    commentEditor?.addEventListener("keydown", async (event) => {
      if (isSubmitShortcut(event)) {
        event.preventDefault();
        await saveEditedComment(thread, commentEditor);
      }
    });
    commentEditor?.addEventListener("blur", async () => {
      await saveEditedComment(thread, commentEditor);
    });
    card.querySelector("[data-thread-reply-submit]")?.addEventListener("click", async () => {
      const replyEditor = card.querySelector("[data-thread-reply]");
      await addReplyFromEditor(thread, replyEditor);
    });
    card.querySelector("[data-thread-reply]")?.addEventListener("keydown", async (event) => {
      if (isReplySubmitShortcut(event)) {
        event.preventDefault();
        await addReplyFromEditor(thread, event.target);
      }
    });
    card.querySelector("[data-thread-resolve]")?.addEventListener("click", async () => {
      await updateThreadStatus(thread, COMMENT_STATUS.resolved);
    });
    card.querySelector("[data-thread-reopen]")?.addEventListener("click", async () => {
      await updateThreadStatus(thread, COMMENT_STATUS.needsAgentReview);
    });
    card.querySelector("[data-thread-delete]")?.addEventListener("click", async () => {
      state.comments.comments = state.comments.comments.filter((item) => item.id !== thread.id);
      if (state.activeCommentId === thread.id) {
        state.activeCommentId = null;
      }
      await saveComments();
      renderComments();
    });
  }

  async function updateThreadStatus(thread, status) {
    if (!thread || thread.status === status) {
      return;
    }
    thread.status = status;
    await saveComments();
    refreshThreadDisplay(thread);
    activate(thread.id, false);
  }

  function refreshThreadDisplay(thread) {
    replaceCommentCard(thread);
    updateThreadAnchors(thread);
    updateBlockCommentState(thread.block_id);
    updateCommentCount();
    applyFilterVisibility();
    setStatus(state.serverWritable ? "comments.json" : "standalone");
    schedulePositionCards();
  }

  function replaceCommentCard(thread) {
    const index = state.comments.comments.findIndex((item) => item.id === thread.id);
    const current = document.getElementById(cardId(thread.id));
    if (!current || index < 0) {
      return;
    }
    current.replaceWith(createCommentCard(thread, index + 1));
  }

  function updateThreadAnchors(thread) {
    document.querySelectorAll(commentSelector(thread.id)).forEach((element) => {
      element.dataset.state = threadCardState(thread);
    });
  }

  function updateBlockCommentState(blockId) {
    const block = document.querySelector(`[data-review-block="${cssEscape(blockId)}"]`);
    if (!block) {
      return;
    }
    const blockThreads = state.comments.comments.filter((thread) => thread.block_id === blockId);
    block.classList.toggle("has-review-comments", blockThreads.some((thread) => !isResolvedThread(thread)));
    block.classList.toggle("has-review-replies", blockThreads.some(isNeedsUserReply));
  }

  function renderReplies(thread) {
    if (!Array.isArray(thread.replies) || thread.replies.length === 0) {
      return '<div class="cmt-thread"></div>';
    }
    const replies = thread.replies.map((reply) => {
      const agentClass = reply.role === "agent" ? " from-agent" : "";
      return [
        `<div class="reply${agentClass}">`,
        `  <div class="av">${escapeHtml(replyInitials(reply))}</div>`,
        "  <div>",
        `    <div class="reply-name">${escapeHtml(replyAuthor(reply))}<span class="reply-time">${escapeHtml(formatDateTime(reply.created_at))}</span></div>`,
        `    <div class="reply-body">${escapeHtml(reply.body)}</div>`,
        "  </div>",
        "</div>",
      ].join("");
    }).join("");
    return `<div class="cmt-thread">${replies}</div>`;
  }

  function enterCommentEditMode(display, editor) {
    if (!(editor instanceof HTMLTextAreaElement)) {
      return;
    }
    display.hidden = true;
    editor.hidden = false;
    editor.focus();
    editor.setSelectionRange(editor.value.length, editor.value.length);
  }

  async function saveEditedComment(thread, editor) {
    if (!(editor instanceof HTMLTextAreaElement) || editor.hidden) {
      return;
    }
    const body = editor.value.trim();
    if (!body) {
      renderComments();
      activate(thread.id, false);
      return;
    }
    if (body !== thread.comment) {
      thread.comment = body;
      await saveComments();
    }
    renderComments();
    activate(thread.id, false);
  }

  async function addReplyFromEditor(thread, editor) {
    if (!(editor instanceof HTMLTextAreaElement)) {
      return;
    }
    const body = editor.value.trim();
    if (!body) {
      editor.focus();
      return;
    }
    thread.replies = Array.isArray(thread.replies) ? thread.replies : [];
    thread.replies.push({
      id: "reply_" + Date.now().toString(36),
      author: "user",
      role: "user",
      kind: "note",
      body,
      created_at: new Date().toISOString(),
    });
    thread.status = COMMENT_STATUS.needsAgentReview;
    await saveComments();
    renderComments();
    activate(thread.id, false);
    window.setTimeout(() => {
      const nextEditor = document.querySelector(`#${cardId(thread.id)} [data-thread-reply]`);
      if (nextEditor instanceof HTMLTextAreaElement) {
        nextEditor.focus();
      }
    }, 0);
  }

  function positionCards() {
    const layer = document.getElementById("cmtLayer");
    if (!layer) {
      return;
    }
    const cards = Array.from(layer.querySelectorAll(".cmt"));
    if (!isDesktopRail()) {
      for (const card of cards) {
        card.style.position = "";
        card.style.top = "";
      }
      return;
    }
    const layerRect = layer.getBoundingClientRect();
    cards.sort((a, b) => {
      const aAnchor = document.querySelector(commentSelector(a.dataset.for));
      const bAnchor = document.querySelector(commentSelector(b.dataset.for));
      const aTop = aAnchor ? aAnchor.getBoundingClientRect().top : 0;
      const bTop = bAnchor ? bAnchor.getBoundingClientRect().top : 0;
      return aTop - bTop;
    });
    let cursor = 0;
    for (const card of cards) {
      if (card.hidden || card.style.display === "none") {
        continue;
      }
      const anchor = document.querySelector(commentSelector(card.dataset.for));
      const ideal = anchor ? anchor.getBoundingClientRect().top - layerRect.top + layer.scrollTop : cursor;
      const top = Math.max(ideal, cursor);
      card.style.position = "absolute";
      card.style.top = `${top}px`;
      cursor = top + card.offsetHeight + 14;
    }
  }

  function schedulePositionCards() {
    if (state.positionFrame) {
      return;
    }
    state.positionFrame = window.requestAnimationFrame(() => {
      state.positionFrame = 0;
      positionCards();
    });
  }

  function isDesktopRail() {
    const viewDoc = document.getElementById("viewDoc");
    return window.matchMedia("(min-width: 901px)").matches && (!viewDoc || viewDoc.classList.contains("active"));
  }

  function activate(commentId, scrollCard = true) {
    if (!commentId) {
      return;
    }
    state.activeCommentId = commentId;
    setActiveClasses(commentId);
    schedulePositionCards();
    if (scrollCard) {
      window.requestAnimationFrame(() => {
        const card = document.getElementById(cardId(commentId));
        if (card) {
          card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      });
    }
  }

  function setActiveClasses(commentId) {
    document.querySelectorAll(".cx.is-active, .cmt.is-active").forEach((element) => {
      element.classList.remove("is-active");
    });
    document.querySelectorAll(commentSelector(commentId)).forEach((highlight) => {
      highlight.classList.add("is-active");
    });
    const card = document.getElementById(cardId(commentId));
    card?.classList.add("is-active");
  }

  function updateCommentCount() {
    if (!ui.commentCount) {
      return;
    }
    const total = state.comments.comments.length;
    const unresolved = state.comments.comments.filter((thread) => !isResolvedThread(thread)).length;
    ui.commentCount.textContent = t.commentCount(unresolved, total);
  }

  function applyFilterVisibility() {
    const canvas = document.getElementById("canvas") || document.body;
    canvas.classList.toggle("hide-resolved", state.filter === "hide-resolved");
    canvas.classList.toggle("only-open", state.filter === "only-open");
    state.comments.comments.forEach((thread) => {
      const visible = shouldShowThreadByFilter(thread);
      document.querySelectorAll(commentSelector(thread.id)).forEach((highlight) => {
        highlight.querySelectorAll(".cx-num").forEach((badge) => {
          badge.hidden = !visible;
        });
      });
      const card = document.getElementById(cardId(thread.id));
      if (card) {
        card.hidden = !visible;
      }
    });
    schedulePositionCards();
  }

  function shouldShowThreadByFilter(thread) {
    const cardState = threadCardState(thread);
    if (state.filter === "hide-resolved") {
      return cardState !== "resolved";
    }
    if (state.filter === "only-open") {
      return cardState === "open";
    }
    return true;
  }

  function initI18nLabels() {
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.dataset.i18n;
      if (t[key] === undefined) { return; }
      if (el.tagName === "SELECT" || el.tagName === "ASIDE" || el.tagName === "NAV") {
        el.setAttribute("aria-label", t[key]);
      } else {
        el.textContent = t[key];
      }
    });
    document.querySelectorAll("[data-i18n-title]").forEach(function (el) {
      var key = el.dataset.i18nTitle;
      if (t[key] !== undefined) { el.title = t[key]; }
    });
    document.querySelectorAll("[data-i18n] option[data-i18n]").forEach(function (opt) {
      var key = opt.dataset.i18n;
      if (t[key] !== undefined) { opt.textContent = t[key]; }
    });
  }

  function initThemeToggle() {
    const button = document.getElementById("themeToggle");
    const saved = safeLocalStorageGet(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      document.documentElement.dataset.theme = saved;
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      document.documentElement.dataset.theme = "dark";
    }
    if (!button) {
      return;
    }
    const label = button.querySelector(".tt-label");
    if (label) {
      const current = document.documentElement.dataset.theme || "light";
      label.textContent = current === "dark" ? "Light" : "Dark";
    }
    button.addEventListener("click", () => {
      const current = document.documentElement.dataset.theme;
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      safeLocalStorageSet(THEME_STORAGE_KEY, next);
      if (label) {
        label.textContent = next === "dark" ? "Light" : "Dark";
      }
      schedulePositionCards();
    });
  }

  function initFilter() {
    const select = document.getElementById("filterSelect");
    if (!select) {
      return;
    }
    const storageKey = "reviewFilter_" + documentId;
    const saved = localStorage.getItem(storageKey);
    if (saved && Array.from(select.options).some((o) => o.value === saved)) {
      select.value = saved;
    }
    state.filter = select.value || "all";
    select.addEventListener("change", () => {
      state.filter = select.value || "all";
      localStorage.setItem(storageKey, state.filter);
      applyFilterVisibility();
    });
  }

  function applyFocusState(canvas, button, isFocus) {
    canvas.classList.toggle("is-focus", isFocus);
    button.setAttribute("aria-pressed", isFocus ? "true" : "false");
    const label = button.querySelector(".ft-label");
    if (label) {
      label.textContent = isFocus ? t.normalLabel : t.focusLabel;
    } else {
      button.textContent = isFocus ? t.normalLabel : t.focusLabel;
    }
  }

  function initFocusToggle() {
    const button = document.getElementById("focusToggle");
    const canvas = document.getElementById("canvas");
    if (!button || !canvas) {
      return;
    }
    const stored = localStorage.getItem("rw:focus");
    if (stored === "true") {
      applyFocusState(canvas, button, true);
      schedulePositionCards();
    }
    button.addEventListener("click", () => {
      const isFocus = !canvas.classList.contains("is-focus");
      applyFocusState(canvas, button, isFocus);
      localStorage.setItem("rw:focus", isFocus ? "true" : "false");
      schedulePositionCards();
    });
  }

  function initPublishToggle() {
    const button = document.getElementById("publishToggle");
    if (!button) {
      return;
    }

    button.addEventListener("click", () => {
      setPublished(!document.body.classList.contains("is-published"));
    });

    const exitButton = document.getElementById("pubExitBtn");
    if (exitButton) {
      exitButton.addEventListener("click", () => setPublished(false));
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && document.body.classList.contains("is-published")) {
        setPublished(false);
      }
    });

    document.querySelectorAll(".pe-w").forEach((widthButton) => {
      widthButton.addEventListener("click", () => {
        const canvas = document.getElementById("canvas");
        if (!canvas) {
          return;
        }
        const isMax = widthButton.getAttribute("data-pw") === "max";
        canvas.classList.toggle("is-focus", isMax);
        const focusButton = document.getElementById("focusToggle");
        if (focusButton) {
          focusButton.setAttribute("aria-pressed", isMax ? "true" : "false");
          const label = focusButton.querySelector(".ft-label");
          if (label) {
            label.textContent = isMax ? t.normalLabel : t.focusLabel;
          }
        }
        document.querySelectorAll(".pe-w").forEach((buttonItem) => {
          buttonItem.classList.toggle("on", buttonItem === widthButton);
        });
        schedulePositionCards();
      });
    });

    const downloadButton = document.getElementById("pubDownloadBtn");
    if (downloadButton) {
      downloadButton.addEventListener("click", downloadPublishedDoc);
    }
  }

  function setPublished(on) {
    document.body.classList.toggle("is-published", on);
    const button = document.getElementById("publishToggle");
    if (button) {
      button.setAttribute("aria-pressed", on ? "true" : "false");
      const label = button.querySelector(".pt-label");
      if (label) {
        label.textContent = on ? t.publishActive : t.publishLabel;
      }
    }
    if (on) {
      const canvas = document.getElementById("canvas");
      const isFocus = canvas && canvas.classList.contains("is-focus");
      document.querySelectorAll(".pe-w").forEach((widthButton) => {
        const isMax = widthButton.getAttribute("data-pw") === "max";
        widthButton.classList.toggle("on", isMax === Boolean(isFocus));
      });
    }
    schedulePositionCards();
  }

  async function buildPublishedDoc() {
    const shell = document.querySelector("#canvas .doc-shell");
    if (!shell) {
      return null;
    }
    const clone = shell.cloneNode(true);

    clone.querySelectorAll(".toc, .cmt-rail, .doc-status, .byline, .cx-num").forEach((node) => node.remove());

    clone.querySelectorAll(".cx").forEach((element) => {
      const parent = element.parentNode;
      if (!parent) {
        return;
      }
      while (element.firstChild) {
        parent.insertBefore(element.firstChild, element);
      }
      parent.removeChild(element);
    });

    clone.querySelectorAll("[data-comment]").forEach((node) => {
      node.removeAttribute("data-comment");
    });
    clone.querySelectorAll("[data-cstate-host]").forEach((node) => {
      node.removeAttribute("data-cstate-host");
    });
    clone.querySelectorAll("[data-review-block]").forEach((node) => {
      node.removeAttribute("data-review-block");
      node.removeAttribute("data-review-required");
      node.removeAttribute("data-block-type");
    });

    clone.querySelectorAll(".review-comment-highlight").forEach((element) => {
      const parent = element.parentNode;
      if (!parent) {
        return;
      }
      while (element.firstChild) {
        parent.insertBefore(element.firstChild, element);
      }
      parent.removeChild(element);
    });
    clone.querySelectorAll(".review-comment-badge").forEach((node) => node.remove());

    await embedImages(clone);

    const root = document.documentElement;
    const density = root.getAttribute("data-density") || "compact";
    const docLang = root.lang || "ja";
    const canvas = document.getElementById("canvas");
    const isFocus = canvas && canvas.classList.contains("is-focus");
    const titleElement = clone.querySelector(".doc-title");
    const title = titleElement ? titleElement.textContent.trim() : "document";

    const summaryEl = clone.querySelector(".summary p");
    const firstP = clone.querySelector(".document-content .block-content p");
    const description = (summaryEl || firstP || { textContent: "" }).textContent.trim().slice(0, 200);

    const eyebrow = clone.querySelector(".eyebrow");
    if (eyebrow) {
      eyebrow.innerHTML = '<a href="https://github.com/u-ichi/reviewable-html-workbench" ' +
        'style="color:inherit;text-decoration:none;" target="_blank" rel="noopener">' +
        escapeHtml(eyebrow.textContent.trim()) + "</a>";
    }

    const css = await collectCSS();
    const mermaidScripts = await collectMermaidScripts(clone);
    var darkOverrides =
      "@media(prefers-color-scheme:dark){:root{" +
      "--bg-app:#131519;--bg-rail:#171a1f;--paper:#1c1f24;--paper-2:#20242a;" +
      "--ink:#e7e3da;--ink-2:#a6a299;--ink-3:#7d7a72;--ink-faint:#5b5851;" +
      "--line-1:#2c2f35;--line-2:#393d44;--line-3:#4a4e56;" +
      "--brand:#6ea4dc;--brand-soft:#1f2d3c;" +
      "--open:#6ea4dc;--open-bg:#1c2c3b;--open-line:#355472;" +
      "--reply:#d6a85a;--reply-bg:#352c18;--reply-line:#604c25;" +
      "--resolved:#6dba88;--resolved-bg:#1c2e23;--resolved-line:#345240;" +
      "--code-bg:#15181d;--code-bg-2:#1b1f25;--code-line:#262b32;" +
      "--sh-1:0 1px 2px rgba(0,0,0,.4),0 0 0 1px rgba(255,255,255,.04);" +
      "--sh-2:0 2px 8px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.05);" +
      "--sh-3:0 10px 30px rgba(0,0,0,.6),0 2px 6px rgba(0,0,0,.4);" +
      "--focus-ring:0 0 0 3px color-mix(in srgb,var(--brand) 40%,transparent);" +
      "}}";
    const html =
      "<!DOCTYPE html>\n<html lang=\"" + docLang + "\" data-density=\"" + density + "\">\n" +
      "<head>\n<meta charset=\"utf-8\">\n" +
      "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n" +
      "<title>" + escapeHtml(title) + "</title>\n" +
      '<meta property="og:title" content="' + escapeHtml(title) + '">\n' +
      '<meta property="og:description" content="' + escapeHtml(description) + '">\n' +
      '<meta property="og:type" content="article">\n' +
      '<meta name="twitter:card" content="summary">\n' +
      '<meta name="twitter:title" content="' + escapeHtml(title) + '">\n' +
      '<meta name="twitter:description" content="' + escapeHtml(description) + '">\n' +
      "<style>\n" + css +
      "\n/* published export overrides */\n" +
      "html,body{background:var(--bg-app);}\n" +
      ".canvas{overflow:visible;height:auto;min-height:100vh;}\n" +
      darkOverrides + "\n" +
      "</style>\n" +
      mermaidScripts +
      "</head>\n" +
      "<body class=\"is-published\">\n" +
      "<main class=\"canvas" + (isFocus ? " is-focus" : "") + "\">\n" +
      clone.outerHTML + "\n</main>\n</body>\n</html>\n";
    return { html, title };
  }

  async function collectMermaidScripts(clone) {
    const needsMermaid = Boolean(
      clone.querySelector(".mermaid") ||
      document.querySelector('script[src*="assets/mermaid.min.js"]')
    );
    if (!needsMermaid) {
      return "";
    }
    const mermaid = await fetchAssetText("assets/mermaid.min.js");
    const zoom = await fetchAssetText("assets/diagram-zoom.js");
    let scripts = "";
    if (mermaid) {
      scripts += "<script>\n" + mermaid + "\n</script>\n";
      scripts += "<script>mermaid.initialize({startOnLoad: true, theme: 'dark', securityLevel: 'strict'})</script>\n";
    }
    if (zoom) {
      scripts += "<script>\n" + zoom + "\n</script>\n";
    }
    return scripts;
  }

  async function fetchAssetText(path) {
    try {
      const response = await fetch(new URL(path, window.location.href).toString(), { cache: "no-store" });
      if (response.ok) {
        return await response.text();
      }
    } catch (_error) { /* skip */ }
    return "";
  }

  async function collectCSS() {
    let css = "";
    for (let index = 0; index < document.styleSheets.length; index += 1) {
      try {
        const rules = document.styleSheets[index].cssRules;
        for (let ruleIndex = 0; ruleIndex < rules.length; ruleIndex += 1) {
          css += rules[ruleIndex].cssText + "\n";
        }
      } catch (_error) {
        var href = document.styleSheets[index].href;
        if (href) {
          try {
            var resp = await fetch(href);
            if (resp.ok) {
              css += (await resp.text()) + "\n";
            }
          } catch (_fetchError) { /* skip */ }
        }
      }
    }
    return css;
  }

  async function embedImages(container) {
    var imgs = container.querySelectorAll("img[src]");
    var promises = Array.prototype.map.call(imgs, function(img) {
      var src = img.getAttribute("src");
      if (!src || src.startsWith("data:")) {
        return Promise.resolve();
      }
      var origImg = document.querySelector('img[src="' + CSS.escape(src) + '"]') ||
                    document.querySelector('img[src="' + src + '"]');
      if (origImg && origImg.naturalWidth > 0 && origImg.complete) {
        try {
          var cvs = document.createElement("canvas");
          cvs.width = origImg.naturalWidth;
          cvs.height = origImg.naturalHeight;
          cvs.getContext("2d").drawImage(origImg, 0, 0);
          img.setAttribute("src", cvs.toDataURL("image/png"));
          return Promise.resolve();
        } catch (_canvasError) { /* fall through to fetch */ }
      }
      return fetch(src).then(function(r) { return r.blob(); }).then(function(blob) {
        return new Promise(function(resolve) {
          var reader = new FileReader();
          reader.onloadend = function() {
            img.setAttribute("src", reader.result);
            resolve();
          };
          reader.onerror = function() { resolve(); };
          reader.readAsDataURL(blob);
        });
      }).catch(function() { /* keep original src */ });
    });
    await Promise.all(promises);
  }

  function slugify(value) {
    return (value || "document").replace(/[\\/:*?"<>|\s]+/g, "_").replace(/_+/g, "_").slice(0, 48) || "document";
  }

  function toast(message) {
    const element = document.createElement("div");
    element.className = "pub-toast";
    element.innerHTML = [
      '<svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3.2L13 5"/></svg>',
      escapeHtml(message),
    ].join("");
    document.body.appendChild(element);
    window.requestAnimationFrame(() => {
      element.classList.add("show");
    });
    window.setTimeout(() => {
      element.classList.remove("show");
      window.setTimeout(() => {
        element.remove();
      }, 240);
    }, 2600);
  }

  async function downloadPublishedDoc() {
    const doc = await buildPublishedDoc();
    if (!doc) {
      return;
    }
    const blob = new Blob([doc.html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = slugify(doc.title) + ".html";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 1500);
    toast(t.publishToast);
  }

  function initTocScrollSpy() {
    const toc = document.querySelector(".toc");
    if (!toc) {
      return;
    }
    const links = Array.from(toc.querySelectorAll("a[href^='#']"));
    const headings = Array.from(document.querySelectorAll(".prose h2[id], [data-review-block] h2[id], h2[id]"));
    const canvas = document.getElementById("canvas");
    links.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const id = link.getAttribute("href")?.slice(1);
        const target = id ? document.getElementById(id) : null;
        if (!target) {
          return;
        }
        const sc = canvas || document.documentElement;
        sc.scrollTop = target.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop - 72;
      });
    });
    const onScroll = rafThrottle(() => updateCurrentSection(links, headings));
    if (canvas) {
      canvas.addEventListener("scroll", onScroll);
    }
    window.addEventListener("scroll", onScroll);
    updateCurrentSection(links, headings);

    const tocList = toc.querySelector("ol.toc-list");
    if (tocList) {
      tocList.addEventListener("wheel", (e) => {
        const maxScroll = tocList.scrollHeight - tocList.clientHeight;
        if (maxScroll <= 0) { return; }
        const atTop = tocList.scrollTop <= 0 && e.deltaY < 0;
        const atBottom = tocList.scrollTop >= maxScroll && e.deltaY > 0;
        if (!atTop && !atBottom) {
          e.preventDefault();
          tocList.scrollTop += e.deltaY;
        }
      }, { passive: false });
    }
  }

  function updateCurrentSection(links, headings) {
    let current = null;
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top <= 100) {
        current = heading;
      }
    }
    links.forEach((link) => link.classList.remove("current"));
    if (!current) {
      return;
    }
    const link = links.find((item) => item.getAttribute("href") === `#${current.id}`);
    link?.classList.add("current");
  }

  function rafThrottle(callback) {
    let ticking = false;
    return () => {
      if (ticking) {
        return;
      }
      ticking = true;
      window.requestAnimationFrame(() => {
        ticking = false;
        callback();
      });
    };
  }

  function threadCardState(thread) {
    if (isResolvedThread(thread) || thread.status === "addressed") {
      return "resolved";
    }
    if (isNeedsUserReply(thread) || thread.status === "reply") {
      return "reply";
    }
    return "open";
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

  function replyInitials(reply) {
    if (reply.role === "agent") {
      return "AI";
    }
    if (reply.role === "system") {
      return "SYS";
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
    if (ui.root.contains(event.target) || ui.commentRail?.contains(event.target)) {
      return;
    }
    if (event.target.closest?.(".cx[data-comment]")) {
      return;
    }
    if (captureImageBlockClick(event)) {
      return;
    }
    closeComposer();
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

  function clearDocumentSelectionForNonTextTarget() {
    state.ignoreSelectionChange = true;
    window.getSelection()?.removeAllRanges();
    window.setTimeout(() => {
      state.ignoreSelectionChange = false;
    }, 0);
  }

  function hideFloatingUi(event) {
    if (event?.target && (ui.root.contains(event.target) || ui.commentRail?.contains(event.target))) {
      return;
    }
    ui.toolbar.hidden = true;
    closeComposer();
    schedulePositionCards();
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
    const raw = safeLocalStorageGet(storageKey);
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
    safeLocalStorageSet(storageKey, JSON.stringify(state.comments));
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
    return element?.closest(".cx[data-comment]");
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
        if (node.parentElement?.closest(".cx[data-comment], .cx-num")) {
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

  function cardId(commentId) {
    return `card-${cssIdentifier(commentId)}`;
  }

  function commentSelector(commentId) {
    return `.cx[data-comment="${cssEscape(commentId || "")}"]`;
  }

  function cssIdentifier(value) {
    return String(value || "").replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatDateTime(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  }

  function safeLocalStorageGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function safeLocalStorageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (_error) {
      // localStorage can be disabled in strict browser modes; comments still render.
    }
  }

  function initEventSource() {
    if (typeof EventSource === "undefined") {
      return;
    }
    var es = new EventSource("/events");
    es.addEventListener("comment_updated", function (event) {
      try {
        var data = JSON.parse(event.data);
        if (data.source === "browser") {
          return;
        }
      } catch (_error) {
        // continue with refresh
      }
      fetchAndMergeComments();
    });
    es.addEventListener("document_updated", function (event) {
      var message = t.docUpdated;
      try {
        var data = JSON.parse(event.data);
        if (data.message) {
          message = data.message;
        }
      } catch (_error) {
        // use default message
      }
      showUpdateBanner(message);
    });
    es.addEventListener("error", function () {
      // EventSource auto-reconnects; no action needed
    });
  }

  async function fetchAndMergeComments() {
    try {
      var response = await fetch(COMMENTS_URL, { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      var payload = normalizeComments(await response.json());
      mergeRemoteComments(payload);
    } catch (_error) {
      // fetch failed; skip this update
    }
  }

  function mergeRemoteComments(newPayload) {
    var oldThreads = state.comments.comments;
    var newThreads = newPayload.comments;
    var oldMap = {};
    oldThreads.forEach(function (thread) { oldMap[thread.id] = thread; });
    var hasNewAgentReply = false;
    var hasNewThread = false;
    var changed = false;
    var changedExistingThreads = [];

    newThreads.forEach(function (newThread) {
      var old = oldMap[newThread.id];
      if (!old) {
        state.comments.comments.push(newThread);
        hasNewAgentReply = true;
        hasNewThread = true;
        changed = true;
        return;
      }
      var oldReplyCount = (old.replies || []).length;
      var newReplyCount = (newThread.replies || []).length;
      if (newReplyCount > oldReplyCount) {
        var addedReplies = newThread.replies.slice(oldReplyCount);
        old.replies = newThread.replies;
        var hasAgent = addedReplies.some(function (r) { return r.role === "agent"; });
        if (hasAgent) {
          hasNewAgentReply = true;
        }
        if (changedExistingThreads.indexOf(old) === -1) {
          changedExistingThreads.push(old);
        }
        changed = true;
      }
      if (old.status !== newThread.status) {
        old.status = newThread.status;
        if (changedExistingThreads.indexOf(old) === -1) {
          changedExistingThreads.push(old);
        }
        changed = true;
      }
    });

    if (!changed) {
      return;
    }
    writeLocalComments();
    if (hasNewThread) {
      renderComments();
    } else {
      changedExistingThreads.forEach(refreshThreadDisplay);
    }
    if (hasNewAgentReply) {
      toast(t.agentReplied);
    }
  }

  function showUpdateBanner(message) {
    var existing = document.getElementById("reviewUpdateBanner");
    if (existing) {
      existing.remove();
    }
    var banner = document.createElement("div");
    banner.id = "reviewUpdateBanner";
    banner.className = "review-update-banner";
    banner.innerHTML = [
      '<svg class="rub-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm6.5-.25A.75.75 0 017.25 7h1a.75.75 0 01.75.75v2.75h.25a.75.75 0 010 1.5h-2a.75.75 0 010-1.5h.25v-2h-.25a.75.75 0 01-.75-.75zM8 6a1 1 0 100-2 1 1 0 000 2z"/></svg>',
      '<span class="rub-message">' + escapeHtml(message) + '</span>',
      '<button type="button" class="rub-reload">' + escapeHtml(t.reloadBtn) + '</button>',
      '<button type="button" class="rub-close" aria-label="close">×</button>',
    ].join("");
    document.body.appendChild(banner);
    banner.querySelector(".rub-reload").addEventListener("click", function () {
      window.location.reload();
    });
    banner.querySelector(".rub-close").addEventListener("click", function () {
      banner.remove();
    });
    window.requestAnimationFrame(function () {
      banner.classList.add("show");
    });
  }

  function showSaveError(errorMessage) {
    var existing = document.getElementById("reviewSaveError");
    if (existing) {
      existing.remove();
    }
    var banner = document.createElement("div");
    banner.id = "reviewSaveError";
    banner.className = "review-save-error";
    banner.innerHTML = [
      '<span class="rse-text">' + t.saveError + escapeHtml(errorMessage) + '</span>',
      '<button type="button" class="rse-close" aria-label="close">&times;</button>',
    ].join("");
    banner.querySelector(".rse-close").addEventListener("click", function () {
      banner.remove();
    });
    document.body.prepend(banner);
  }
})();
