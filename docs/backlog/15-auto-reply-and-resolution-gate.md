---
id: 15
title: "コメント自動回答 + 解決待ちゲート"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["review-comments", "auto-reply", "resolution-gate", "preview"]
assignee: ""
created: 2026-06-17
updated: 2026-06-17
---

# 15: コメント自動回答 + 解決待ちゲート

## 概要

ユーザーが HTML 上にコメントを追加したら、agent が自動的に検知して `add-reply` で回答する。コメントスレッドが解決するまでドキュメント修正には入らない制御をセットにする。

## 動機

現状はユーザーが「コメント入れた」と agent に伝え、agent が `ingest-review` → `add-reply` を手動で実行する。コメント追加から回答までのラグと手間を削減したい。

## ゴール条件

- [x] preview server が `comments.json` の PUT を受けた時に、agent 側で検知できるイベントを出せる。
- [x] agent がコメント追加イベントを受けて `ingest-review` → `add-reply` を実行するフローが skill に定義されている。
- [x] 回答時にコメントの `comment` と `selected_text` を読み、設計資料の文脈を踏まえることが skill に定義されている。
- [x] 未解決の `needs_clarification` コメントがある間は、設計反映へ進まない解決待ちゲートを確認できる。
- [x] ユーザーがコメントを解決した後、必要なドキュメント修正を反映するフローが skill に定義されている。
- [x] agent がドキュメント修正と再 render を完了した時に、ブラウザ上へ更新通知を出せる。
- [x] ブラウザ通知は自動リロードせず、ユーザーが自分のタイミングでリロードできる。

## やること

- [x] preview server に `comments.json` 更新イベントを追加する。
- [x] `watch-comments` CLI でコメント更新イベントを監視できるようにする。
- [x] `check-gates` CLI で未解決の `needs_clarification` コメントを検出できるようにする。
- [x] `notify-update` CLI でブラウザへドキュメント更新通知を送れるようにする。
- [x] `reviewable-design-doc` skill にコメント自動回答と解決待ちゲートのフローを追加する。
- [x] `visual-html-renderer` skill の preview 後手順を `watch-comments` 利用に合わせる。
- [x] `review-comments.js` に SSE 購読と更新通知バナーを追加する。
- [x] manifest と package version を `1.9.0` に揃える。

## Goal 実行

- goal-ready: true
- objective: "HTML レビューコメントの追加検知、agent reply、解決待ちゲート、ブラウザ更新通知を一連のレビュー運用として使える状態にする"
- scope:
  - "comments.json PUT からのイベント通知"
  - "agent reply フロー"
  - "needs_clarification 解決待ちゲート"
  - "解決後の設計反映フロー"
  - "ブラウザ更新通知"
  - "version 整合"
- stop_conditions:
  - "agent を継続実行させるための Monitor ツールや実行環境が使えない時"
  - "外部アップロード型の通知・レンダリング手段が必要になった時"
  - "複数 agent セッション間の排他制御が必要になった時"
- verification:
  - "python3 -m json.tool .claude-plugin/plugin.json >/dev/null"
  - "python3 -m json.tool .claude-plugin/marketplace.json >/dev/null"
  - "python3 -m json.tool .codex-plugin/plugin.json >/dev/null"
  - "python3 -m json.tool .agents/plugins/marketplace.json >/dev/null"
  - "env PYTHONPYCACHEPREFIX=tmp/python-pycache python3 -m unittest discover -s tests"
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

- 複数 agent セッションが同じコメントを同時処理する場合の排他制御。
- agent セッション終了後の未処理イベント復旧。
- コメントが大量に同時追加された場合の優先度制御。

## 進捗ログ

### 2026-06-17

- backlog 15 を標準 backlog 形式に変換し、現在の実装差分に基づいて完了済み項目を整理した。
- `scripts/html_review_workbench/event_bus.py`、`preview_server.py`、`watch_comments.py`、`resolution_gate.py`、`templates/review-comments.js`、`skills/reviewable-design-doc/SKILL.md`、`skills/visual-html-renderer/SKILL.md`、関連テストで、イベント通知・監視・解決待ちゲート・更新通知の実装根拠を確認した。
- manifest / package version を `1.9.0` に揃え、`env PYTHONPYCACHEPREFIX=tmp/python-pycache python3 -m unittest discover -s tests` が 118 tests OK で通ることを確認した。
- `bin/plugin-dev-switch.sh status` で Claude / Codex とも dev mode、`codex plugin list --marketplace reviewable-html-workbench-local --json` で `installed: true` / `enabled: true` / `version: 1.9.0` を確認した。

## 成果物

- `scripts/html_review_workbench/event_bus.py`
- `scripts/html_review_workbench/watch_comments.py`
- `scripts/html_review_workbench/resolution_gate.py`
- `scripts/html_review_workbench/preview_server.py`
- `scripts/html_review_workbench/cli.py`
- `templates/review-comments.js`
- `skills/reviewable-design-doc/SKILL.md`
- `skills/visual-html-renderer/SKILL.md`
- `tests/test_event_bus.py`
- `tests/test_resolution_gate.py`
- `tests/test_review_comments_js.py`
- `tests/test_add_reply.py`
- `tests/test_preview_server.py`
- `tests/test_project_layout.py`
