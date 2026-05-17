---
id: 7
title: "Milestone 6: Review Ingestion"
status: 進行中
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "review-ingestion", "agent-reply"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 07: Milestone 6: Review Ingestion

## 概要

「レビュー終わったので確認して」発話から `comments.json` を読み込み、コメントを分類し、確認が必要な指摘にはHTMLコメントスレッドへagent replyを書き戻す。07ではdocument modelへの自由反映までは広げず、fixture上で分類・reply・state保存の最小縦通しを固める。

## ゴール条件

- [x] `ingest-review` CLIが `comments.json` を読み込める。
- [x] コメントを `actionable`, `needs_clarification`, `blocked`, `already_addressed` に分類できる。
- [x] `actionable` は反映対象として `annotations/review-cycle-state.json` に記録される。
- [x] `needs_clarification` は同じコメントスレッドへagent replyを追加する。
- [x] `annotations/review-cycle-state.json` に処理結果が残る。
- [x] fixtureで `comments.json` → 分類 → agent reply追記 → state保存まで検証できる。

## やること

- [x] `ingest_review.py` を実装する。
- [x] comment分類ルールを実装する。
- [x] agent reply書き戻しを実装する。
- [x] review-cycle-stateの保存を実装する。
- [x] fixtureベースのingestion検証を追加する。

## 開発計画・設計同期ルール

- コメント分類、agent reply、state保存の判断基準が固まった区切りで `docs/design.html` を更新する。
- Review Ingestionの完了条件が変わった区切りで `docs/development-plan.html` を更新する。
- `/backlog progress` では、分類件数、agent reply件数、blocked件数、state保存結果を記録する。
- 07ではUI E2E、`review-comments.js`分割、document modelへの自由反映、comments status拡張は扱わない。

## Goal 実行

- goal-ready: true
- objective: "CodexがHTMLレビューコメントを読み込み、分類・agent reply書き戻し・処理状態保存をfixtureで検証できるようにする"
- scope:
  - "ingest_review.py実装"
  - "comment分類"
  - "agent reply書き戻し"
  - "review-cycle-state"
  - "fixture検証"
- stop_conditions:
  - "コメント取り込み、分類、agent reply追記、state保存がfixtureで検証できた時"
  - "document model反映の判断にユーザー確認が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
- goal: "docs/goals/07-milestone-6-review-ingestion/goal.md"
- state: "docs/goals/07-milestone-6-review-ingestion/state.yaml"
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 06からの引き継ぎを反映し、07は `comments.json` → 分類 → agent reply/state保存の最小縦通しに絞る計画へ変更。UI E2E、JS分割、document model自由反映、comments status拡張は後段backlogへ分離。
- 実装完了。`ingest-review` CLIで `comments.json` 読み込み、分類、agent reply追記、`annotations/review-cycle-state.json` 保存まで対応。検証receipt: `docs/goals/07-milestone-6-review-ingestion/notes/verification-2026-05-17.md`。

## 成果物

- `scripts/html_review_workbench/ingest_review.py`
- `scripts/html_review_workbench/cli.py` の `ingest-review`
- `tests/test_ingest_review.py`
- `docs/goals/07-milestone-6-review-ingestion/notes/verification-2026-05-17.md`
