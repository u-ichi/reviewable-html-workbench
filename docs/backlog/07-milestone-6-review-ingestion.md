---
id: 7
title: "Milestone 6: Review Ingestion"
status: バックログ
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

「レビュー終わったので確認して」発話から `comments.json` を読み込み、明確な指摘は設計へ反映し、確認が必要な指摘にはHTMLコメントスレッドへagent replyを書き戻す。

## ゴール条件

- [ ] `ingest-review` CLIが `comments.json` を読み込める。
- [ ] コメントを `actionable`, `needs_clarification`, `blocked`, `already_addressed` に分類できる。
- [ ] `actionable` はdocument modelへ反映される。
- [ ] `needs_clarification` は同じコメントスレッドへagent replyを追加する。
- [ ] `annotations/review-cycle-state.json` に処理結果が残る。
- [ ] Review Ingestion仕様が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [ ] `ingest_review.py` を実装する。
- [ ] comment分類ルールを実装する。
- [ ] agent reply書き戻しを実装する。
- [ ] review-cycle-stateの保存を実装する。
- [ ] 反映後HTML再生成の導線を実装する。

## 開発計画・設計同期ルール

- コメント分類、agent reply、設計反映の判断基準が変わったら `docs/design.html` を更新する。
- Review Ingestionの完了条件が変わったら `docs/development-plan.html` を更新する。
- `/backlog progress` では、反映済み/確認待ち/blocked件数を記録する。

## Goal 実行

- goal-ready: true
- objective: "CodexがHTMLレビューコメントを読み込み、設計反映とagent reply書き戻しを行えるようにする"
- scope:
  - "ingest_review.py実装"
  - "comment分類"
  - "agent reply書き戻し"
  - "review-cycle-state"
  - "設計/計画HTML更新"
- stop_conditions:
  - "コメント取り込みとagent reply追記がfixtureで検証できた時"
  - "設計反映の判断にユーザー確認が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。

## 成果物

（完了時に記載）
