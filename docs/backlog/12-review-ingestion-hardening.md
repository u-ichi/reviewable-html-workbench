---
id: 12
title: "Review Ingestion Hardening"
status: 進行中
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["review-ingestion", "hardening", "deferred"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 12: Review Ingestion Hardening

## 概要

07で `comments.json` → 分類 → agent reply/state保存の最小縦通しを固めた後、UI検証方針、JS責務境界、document model限定反映、status設計を段階的に強化する。物理的なJS分割や本格UI E2Eは、実出力評価後の #13 で必ず実施判断する。

## ゴール条件

- [x] `review-comments.js` の最低限のDOM単位検証方針が決まっている。
- [x] `comments-api` / `selection-anchor` / `thread-popover` 相当のJS責務境界が静的検証で追跡できている。
- [x] ingestion分類とcomments UI statusを混ぜない状態設計になっている。
- [x] document model反映がfixture上の限定置換から安全に拡張されている。
- [x] 実出力評価で確認する項目と自動検証に寄せる項目が整理されている。

## やること

- [x] DOM単位検証の最小構成を決める。
- [x] `review-comments.js` の分割要否と境界を決める。物理分割は #13 の実出力評価後hardeningで判断する。
- [x] comments statusとingestion classificationの関係を整理する。
- [x] document model反映の安全な適用範囲を設計する。
- [x] 10の実出力評価へ渡す確認観点を整理する。

## 開発計画・設計同期ルール

- 検証方式、JS分割、状態設計、document model反映方式が固まったら `docs/design.html` を更新する。
- 実出力評価の完了条件に影響する場合は `docs/development-plan.html` を更新する。
- 物理的なJS分割、本格UI E2E、高度なdocument model反映は #13 の実施判断対象として残す。

## Goal 実行

- goal-ready: true
- objective: "Review Ingestionの最小縦通し後に、UI検証・JS分割・状態設計・document model反映を安全に強化する"
- scope:
  - "DOM単位検証方針"
  - "review-comments.js分割"
  - "status/classification整理"
  - "document model反映強化"
  - "実出力評価への引き継ぎ"
- stop_conditions:
  - "07の最小縦通しが完了していない時"
  - "Playwright等の新規依存導入判断が必要になった時"
  - "document model反映の仕様判断が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
- goal: "docs/goals/12-review-ingestion-hardening/goal.md"
- state: "docs/goals/12-review-ingestion-hardening/state.yaml"
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 06引き継ぎを受け、07から外す項目の受け皿として作成。07は分類・reply・state保存の最小縦通しに集中する。
- 実装完了。新規依存なしの静的JS境界テスト、status/classification分離テスト、`--apply-model` 指定時のdocument model完全一致置換を追加。検証receipt: `docs/goals/12-review-ingestion-hardening/notes/verification-2026-05-17.md`。

## 成果物

- `tests/test_review_comments_js.py`
- `tests/test_ingest_review.py`
- `scripts/html_review_workbench/ingest_review.py` の限定model置換
- `docs/goals/12-review-ingestion-hardening/notes/verification-2026-05-17.md`
