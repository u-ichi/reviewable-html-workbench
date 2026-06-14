/* ============================================================
   Reviewable HTML Workbench — interactions (vanilla, no deps)
   ============================================================ */
(function () {
  "use strict";
  var root = document.documentElement;
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ---------- comment data --------------------------------- */
  var COMMENTS = [
    {
      id: "c1", state: "open", anchor: "c1",
      author: { name: "佐藤 (PM)", initials: "ST", av: "u1" },
      time: "2日前 · 06/11 14:22",
      quote: "オンプレ Postgres では月次バッチが SLA を逸脱し始めている",
      body: "ここは前提として重要なので根拠を1つ足してほしいです。逸脱の頻度と影響範囲（どのレポートが遅延したか）が分かると意思決定しやすい。",
      thread: []
    },
    {
      id: "c2", state: "reply",
      author: { name: "田中 (Data Eng)", initials: "TN", av: "u2" },
      time: "1日前 · 06/12 09:05",
      quote: "コスト列（月額試算）",
      body: "この月額はどのワークロード前提ですか？ クエリ量とストレージのどちらが支配的かで結論が変わりそうです。",
      thread: [
        { agent: true, name: "Workbench Agent", initials: "AI", role: "回答", time: "1日前 · 09:41",
          body: "前提を表下の注記に追記しました。スキャン 12TB/月・ストレージ 4TB 常時で試算しています。クエリ量が支配的なため、定額系の Snowflake が相対的に不利になります。" }
      ]
    },
    {
      id: "c3", state: "resolved",
      author: { name: "高橋 (Reviewer)", initials: "TK", av: "u4" },
      time: "1日前 · 06/12 11:30",
      quote: "推奨: ClickHouse + 既存 Postgres の併用",
      body: "「併用」のときの同期遅延が運用上許容できるか不明瞭でした。数値根拠を求めます。",
      thread: [
        { agent: true, name: "Workbench Agent", initials: "AI", role: "回答", time: "1日前 · 11:52",
          body: "CDC（Debezium）経由で P95 同期遅延は 8 秒という検証ログを §5 に追加しました。" },
        { name: "高橋 (Reviewer)", initials: "TK", av: "u4", role: "確認", time: "23時間前 · 12:10",
          body: "ログ確認しました。許容範囲です。クローズします。" }
      ],
      resolvedBy: "高橋 さんが解決済みにしました · 23時間前"
    },
    {
      id: "c4", state: "open", anchor: "c4",
      author: { name: "鈴木 (SRE)", initials: "SZ", av: "u3" },
      time: "5時間前 · 06/13 08:40",
      quote: "アーキテクチャ概念図",
      body: "図のレンダリングに失敗しています（fallback 表示）。元の Mermaid 定義を残してもらえると確認しやすいです。",
      thread: []
    }
  ];

  /* ---------- card rendering ------------------------------- */
  var STATE_LABEL = { open: "未対応", reply: "返信あり", resolved: "解決済み" };

  function esc(s) { return String(s).replace(/[&<>]/g, function (m) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]; }); }

  function replyHTML(r) {
    var avCls = r.agent ? "from-agent" : "";
    var av = r.agent ? "AI" : r.initials;
    var avColor = r.agent ? "" : (r.av || "u2");
    return '<div class="reply ' + avCls + '">' +
      '<div class="av ' + avColor + '">' + esc(av) + '</div>' +
      '<div><div class="reply-name">' + esc(r.name) +
        (r.role ? '<span class="role">' + esc(r.role) + '</span>' : '') +
        '<span class="reply-time">' + esc(r.time) + '</span></div>' +
        '<div class="reply-body">' + esc(r.body) + '</div></div></div>';
  }

  function cardInner(c) {
    var s = c.state;
    var threadHTML = c.thread.length
      ? '<div class="cmt-thread">' + c.thread.map(replyHTML).join("") + '</div>' : '';
    var resolvedHTML = (s === "resolved" && c.resolvedBy)
      ? '<div class="cmt-resolved-by">' + checkIco() + esc(c.resolvedBy) + '</div>' : '';
    var foot = (s === "resolved")
      ? '<div class="cmt-foot"><button class="btn ghost reopen" data-act="reopen">再オープン</button></div>'
      : '<div class="cmt-foot">' +
          '<input class="cmt-input" placeholder="返信を入力…" aria-label="返信">' +
          '<button class="btn primary" data-act="reply">送信</button>' +
          '<button class="btn ghost resolve" data-act="resolve" title="解決にする">' + checkIco() + '</button>' +
        '</div>';
    return '<div class="cmt-head">' +
        '<div class="av ' + c.author.av + '">' + esc(c.author.initials) + '</div>' +
        '<div class="cmt-who"><div class="cmt-name">' + esc(c.author.name) + '</div>' +
          '<div class="cmt-time">' + esc(c.time) + '</div></div>' +
        '<span class="cmt-state"><span class="sdot"></span>' + STATE_LABEL[s] + '</span>' +
      '</div>' +
      '<p class="cmt-quote">“' + esc(c.quote) + '”</p>' +
      '<div class="cmt-body"><p>' + esc(c.body) + '</p></div>' +
      threadHTML + resolvedHTML + foot;
  }

  function checkIco() {
    return '<svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3.2L13 5"/></svg>';
  }

  var layer = $("#cmtLayer");
  var countEl = $("#cmtCount");

  function buildCards() {
    layer.innerHTML = "";
    COMMENTS.forEach(function (c) {
      var el = document.createElement("aside");
      el.className = "cmt";
      el.setAttribute("data-cstate", c.state);
      el.setAttribute("data-for", c.id);
      el.id = "card-" + c.id;
      el.innerHTML = cardInner(c);
      bindCard(el, c);
      layer.appendChild(el);
    });
    updateCount();
    positionCards();
  }

  function updateCount() {
    var open = COMMENTS.filter(function (c) { return c.state !== "resolved"; }).length;
    countEl.textContent = open + " 件未解決 / " + COMMENTS.length + " 件";
  }

  function bindCard(el, c) {
    el.addEventListener("click", function (e) {
      if (e.target.closest("button") || e.target.closest("input")) return;
      activate(c.id, true);
    });
    el.addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      var act = btn.getAttribute("data-act");
      if (act === "resolve") { setState(c, "resolved", c.resolvedBy || "あなたが解決済みにしました · たった今"); }
      else if (act === "reopen") { setState(c, "open"); }
      else if (act === "reply") {
        var input = $(".cmt-input", el);
        var txt = input && input.value.trim();
        if (!txt) { input && input.focus(); return; }
        c.thread.push({ name: "あなた", initials: "ME", av: "u1", role: "返信", time: "たった今", body: txt });
        if (c.state === "open") c.state = "reply";
        rerender(c);
      }
    });
  }

  function setState(c, state, resolvedBy) {
    c.state = state;
    if (state === "resolved") c.resolvedBy = resolvedBy || c.resolvedBy;
    rerender(c);
  }

  function rerender(c) {
    var el = $("#card-" + c.id);
    el.setAttribute("data-cstate", c.state);
    el.innerHTML = cardInner(c);
    bindCard(el, c);
    // sync highlight
    var hl = $('.cx[data-comment="' + c.id + '"]');
    if (hl) hl.setAttribute("data-state", c.state === "resolved" ? "resolved" : (c.state === "reply" ? "reply" : "open"));
    updateCount();
    positionCards();
    activate(c.id, false);
  }

  /* ---------- positioning (Docs-style margin align) -------- */
  function positionCards() {
    if (!isDesktopRail()) return;
    var layerRect = layer.getBoundingClientRect();
    var ordered = COMMENTS.slice().map(function (c) {
      var hl = $('.cx[data-comment="' + c.id + '"]');
      var top = hl ? (hl.getBoundingClientRect().top - layerRect.top) : 0;
      return { c: c, top: Math.max(0, top), el: $("#card-" + c.id) };
    }).sort(function (a, b) { return a.top - b.top; });

    var cursor = 0;
    ordered.forEach(function (o) {
      if (!o.el || o.el.offsetParent === null) return;
      var t = Math.max(o.top, cursor);
      o.el.style.top = t + "px";
      cursor = t + o.el.offsetHeight + 14;
    });
  }

  function isDesktopRail() {
    return window.matchMedia("(min-width: 901px)").matches &&
      $("#viewDoc").classList.contains("active");
  }

  /* ---------- activate / link highlight <-> card ----------- */
  function activate(id, scrollCard) {
    $$(".cx.is-active").forEach(function (e) { e.classList.remove("is-active"); });
    $$(".cmt.is-active").forEach(function (e) { e.classList.remove("is-active"); });
    var hl = $('.cx[data-comment="' + id + '"]');
    var card = $("#card-" + id);
    if (hl) hl.classList.add("is-active");
    if (card) {
      card.classList.add("is-active");
      positionCards();
      if (scrollCard) {
        var canvas = $("#canvas");
        var cRect = card.getBoundingClientRect();
        var vRect = canvas.getBoundingClientRect();
        if (cRect.top < vRect.top + 60 || cRect.bottom > vRect.bottom - 20) {
          canvas.scrollBy({ top: cRect.top - vRect.top - 120, behavior: "smooth" });
        }
      }
    }
  }

  // clicking highlighted text in the doc
  $$(".cx[data-comment]").forEach(function (hl) {
    hl.addEventListener("click", function () {
      var id = hl.getAttribute("data-comment");
      activate(id, true);
      var card = $("#card-" + id);
      if (card) {
        var canvas = $("#canvas");
        var cRect = card.getBoundingClientRect(), vRect = canvas.getBoundingClientRect();
        canvas.scrollBy({ top: cRect.top - vRect.top - 120, behavior: "smooth" });
      }
    });
  });

  /* ---------- toolbar: tabs -------------------------------- */
  $$(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      $$(".tab").forEach(function (t) { t.setAttribute("aria-selected", "false"); });
      tab.setAttribute("aria-selected", "true");
      var target = tab.getAttribute("data-view");
      $$(".view").forEach(function (v) { v.classList.remove("active"); });
      $("#" + target).classList.add("active");
      $("#canvas").scrollTop = 0;
      if (target === "viewDoc") requestAnimationFrame(positionCards);
    });
  });

  /* ---------- toolbar: theme ------------------------------- */
  $("#themeToggle").addEventListener("click", function () {
    var dark = root.getAttribute("data-theme") === "dark";
    root.setAttribute("data-theme", dark ? "light" : "dark");
    this.querySelector(".tt-label").textContent = dark ? "Light" : "Dark";
    requestAnimationFrame(positionCards);
  });

  /* ---------- toolbar: focus / wide mode ------------------- */
  var focusBtn = $("#focusToggle");
  function setFocus(on) {
    canvas.classList.toggle("is-focus", on);
    focusBtn.setAttribute("aria-pressed", on ? "true" : "false");
    focusBtn.querySelector(".ft-label").textContent = on ? "標準表示" : "最大化";
    // keep the published-mode width switch in sync
    var stdBtn = $('.pe-w[data-pw="standard"]'), maxBtn = $('.pe-w[data-pw="max"]');
    if (stdBtn && maxBtn) { stdBtn.classList.toggle("on", !on); maxBtn.classList.toggle("on", on); }
    requestAnimationFrame(positionCards);
  }
  focusBtn.addEventListener("click", function () {
    setFocus(!canvas.classList.contains("is-focus"));
  });
  $$(".pe-w").forEach(function (b) {
    b.addEventListener("click", function () { setFocus(b.getAttribute("data-pw") === "max"); });
  });

  /* ---------- toolbar: published / public preview ---------- */
  var pubBtn = $("#publishToggle");
  function setPublished(on) {
    document.body.classList.toggle("is-published", on);
    pubBtn.setAttribute("aria-pressed", on ? "true" : "false");
    pubBtn.querySelector(".pt-label").textContent = on ? "プレビュー中" : "公開プレビュー";
    // public view only makes sense on the document; force it active
    if (on) {
      $$(".tab").forEach(function (t) { t.setAttribute("aria-selected", "false"); });
      $$(".view").forEach(function (v) { v.classList.remove("active"); });
      $("#viewDoc").classList.add("active");
      $('.tab[data-view="viewDoc"]').setAttribute("aria-selected", "true");
    }
    requestAnimationFrame(positionCards);
  }
  pubBtn.addEventListener("click", function () {
    setPublished(!document.body.classList.contains("is-published"));
  });
  $("#pubExitBtn").addEventListener("click", function () { setPublished(false); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && document.body.classList.contains("is-published")) setPublished(false);
  });

  /* ---------- export: publishable self-contained HTML ------ */
  function collectCSS() {
    var css = "";
    for (var i = 0; i < document.styleSheets.length; i++) {
      try {
        var rules = document.styleSheets[i].cssRules;
        for (var j = 0; j < rules.length; j++) css += rules[j].cssText + "\n";
      } catch (err) { /* cross-origin sheet — skip */ }
    }
    return css;
  }

  function buildPublishedDoc() {
    var src = $("#viewDoc .doc-shell");
    if (!src) return null;
    var shell = src.cloneNode(true);
    // strip navigation + every review affordance
    $$(".toc, .cmt-rail, .doc-status, .byline, .cx-num", shell).forEach(function (n) { n.remove(); });
    // unwrap highlight spans, keep their text
    $$(".cx", shell).forEach(function (el) {
      var p = el.parentNode;
      while (el.firstChild) p.insertBefore(el.firstChild, el);
      p.removeChild(el);
    });
    $$("[data-comment]", shell).forEach(function (n) { n.removeAttribute("data-comment"); });
    $$("[data-cstate-host]", shell).forEach(function (n) { n.removeAttribute("data-cstate-host"); });

    var theme = root.getAttribute("data-theme") || "light";
    var focus = canvas.classList.contains("is-focus");
    var titleEl = $(".doc-title", shell);
    var title = titleEl ? titleEl.textContent.trim() : "公開文書";

    var html =
      '<!DOCTYPE html>\n<html lang="ja" data-theme="' + theme + '" data-density="compact">\n' +
      '<head>\n<meta charset="UTF-8">\n' +
      '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n' +
      '<title>' + esc(title) + '</title>\n' +
      '<style>\n' + collectCSS() +
      '\n/* published export overrides */\n' +
      'html,body{background:var(--bg-app);}\n' +
      '.canvas{overflow:visible;height:auto;min-height:100vh;}\n' +
      '</style>\n</head>\n' +
      '<body class="is-published">\n' +
      '<main class="canvas' + (focus ? " is-focus" : "") + '">\n' +
      shell.outerHTML + '\n</main>\n</body>\n</html>\n';
    return { html: html, title: title };
  }

  function slugify(s) {
    return (s || "document").replace(/[\\/:*?"<>|\s]+/g, "_").replace(/_+/g, "_").slice(0, 48) || "document";
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "pub-toast";
    t.innerHTML =
      '<svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3.2L13 5"/></svg>' + msg;
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.classList.add("show"); });
    setTimeout(function () { t.classList.remove("show"); setTimeout(function () { t.remove(); }, 240); }, 2600);
  }

  $("#pubDownloadBtn").addEventListener("click", function () {
    var doc = buildPublishedDoc();
    if (!doc) return;
    var blob = new Blob([doc.html], { type: "text/html;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = slugify(doc.title) + ".html";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
    toast("公開用HTMLを書き出しました");
  });

  /* ---------- toolbar: viewport ---------------------------- */
  $$("#viewportSeg button").forEach(function (b) {
    b.addEventListener("click", function () {
      $$("#viewportSeg button").forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on");
      var vp = b.getAttribute("data-vp");
      // viewport only switches between desktop doc and mobile preview tab
      $$(".tab").forEach(function (t) { t.setAttribute("aria-selected", "false"); });
      $$(".view").forEach(function (v) { v.classList.remove("active"); });
      if (vp === "mobile") {
        $("#viewMobile").classList.add("active");
        $('.tab[data-view="viewMobile"]').setAttribute("aria-selected", "true");
      } else {
        $("#viewDoc").classList.add("active");
        $('.tab[data-view="viewDoc"]').setAttribute("aria-selected", "true");
        requestAnimationFrame(positionCards);
      }
      $("#canvas").scrollTop = 0;
    });
  });

  /* ---------- toolbar: review filter ----------------------- */
  $("#filterSelect").addEventListener("change", function () {
    var v = this.value;
    var c = $("#canvas");
    c.classList.remove("hide-resolved", "only-open");
    if (v === "hide-resolved") c.classList.add("hide-resolved");
    if (v === "only-open") c.classList.add("only-open");
    requestAnimationFrame(positionCards);
  });

  /* ---------- mobile threads ------------------------------- */
  $$(".m-thread-head").forEach(function (h) {
    h.addEventListener("click", function () { h.parentElement.classList.toggle("open-state"); });
  });
  var fab = $("#mFab");
  if (fab) fab.addEventListener("click", function () {
    var first = $(".m-thread");
    if (first) {
      first.classList.add("open-state");
      var sc = $(".m-scroll"), r = first.getBoundingClientRect(), sr = sc.getBoundingClientRect();
      sc.scrollBy({ top: r.top - sr.top - 80, behavior: "smooth" });
    }
  });

  /* ---------- TOC scroll spy ------------------------------- */
  var canvas = $("#canvas");
  var tocLinks = $$(".toc a");
  function spy() {
    if (!$("#viewDoc").classList.contains("active")) return;
    var best = null, bestTop = -Infinity;
    $$(".prose h2[id]").forEach(function (h) {
      var t = h.getBoundingClientRect().top;
      if (t < 160 && t > bestTop) { bestTop = t; best = h.id; }
    });
    tocLinks.forEach(function (a) {
      a.classList.toggle("current", a.getAttribute("href") === "#" + best);
    });
  }
  tocLinks.forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      var t = $(a.getAttribute("href"));
      if (t) {
        var r = t.getBoundingClientRect(), vr = canvas.getBoundingClientRect();
        canvas.scrollBy({ top: r.top - vr.top - 90, behavior: "smooth" });
      }
    });
  });

  /* ---------- init ----------------------------------------- */
  buildCards();
  var rt;
  canvas.addEventListener("scroll", function () {
    spy();
    if (rt) cancelAnimationFrame(rt);
    rt = requestAnimationFrame(positionCards);
  });
  window.addEventListener("resize", function () { positionCards(); });
  window.addEventListener("load", function () { positionCards(); });
  setTimeout(positionCards, 60);
  setTimeout(positionCards, 300);
})();
