---
id: 13
title: "Post Evaluation Hardening"
status: バックログ
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "hardening", "e2e", "post-evaluation"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 13: Post Evaluation Hardening

## 概要

10のCodex実出力評価で見つかった不足を必ず回収するための後段hardening。UI E2E、`review-comments.js` の物理分割、高度なdocument model反映を「必要なら後で」ではなく、実出力評価後に実施判断と対応を行う対象として固定する。

## ゴール条件

- [ ] 実出力評価で見つかった未達・不安定挙動・手動確認依存が一覧化されている。
- [ ] Playwright等のブラウザE2Eを導入するか、導入しない場合の代替検証が決まっている。
- [ ] `review-comments.js` を物理分割するか、分割しない場合の維持基準が決まっている。
- [ ] document model反映を完全一致置換から拡張するか、拡張しない場合の安全基準が決まっている。
- [ ] 実施したhardening結果が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [ ] 10の実出力評価receiptを読み、UI E2E / JS分割 / document model反映 / skill導線の不足を分類する。
- [ ] UI E2Eの導入判断を行い、導入する場合は最小E2Eを実装する。
- [ ] `review-comments.js` の物理分割判断を行い、分割する場合は `comments-api` / `selection-anchor` / `thread-popover` などへ分ける。
- [ ] document model反映の拡張判断を行い、拡張する場合は安全な変換ルールとfixtureを追加する。
- [ ] 追加した検証・未採用判断・残リスクを設計と開発計画へ反映する。

## 開発計画・設計同期ルール

- E2E導入、JS分割、document model反映拡張を実施または見送った理由を `docs/development-plan.html` に残す。
- script API、bundle構成、検証方法、反映ルールが変わったら `docs/design.html` を更新する。
- `/backlog progress` では、10の評価receiptから回収した項目、実施したhardening、残したリスクを記録する。

## Goal 実行

- goal-ready: true
- objective: "Codex実出力評価で見つかった不足を回収し、UI E2E・JS分割・document model反映拡張を実施または明示的に見送れる状態にする"
- scope:
  - "実出力評価receiptの不足分類"
  - "UI E2E導入判断"
  - "review-comments.js物理分割判断"
  - "document model反映拡張判断"
  - "設計/計画HTML更新"
- stop_conditions:
  - "10の実出力評価receiptが存在しない時"
  - "Playwright等の新規依存導入にユーザー承認が必要な時"
  - "document model反映の安全基準についてユーザー判断が必要な時"
- verification:
  - "python3 -m unittest discover -s tests"
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 10の実出力評価後に、UI E2E・JS物理分割・高度なdocument model反映を必ず実施判断するための回収枠として作成。

## 成果物

（完了時に記載）
