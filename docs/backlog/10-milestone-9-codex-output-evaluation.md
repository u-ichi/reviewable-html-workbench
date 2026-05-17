---
id: 10
title: "Milestone 9: Codex実出力評価"
status: バックログ
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "codex", "evaluation"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 10: Milestone 9: Codex実出力評価

## 概要

Codex上で実際の設計資料をpluginで作り、コメント作成、review ingestion、agent reply、再生成までのレビューサイクルを完走させる。完走結果から、UI E2E・JS物理分割・document model反映拡張の不足を分類し、#13へ引き継ぐ。

## ゴール条件

- [ ] `docs/design.html` 自体をpluginで再生成できる。
- [ ] preview URLを開いて表示確認できる。
- [ ] HTML上でコメントを入れられる。
- [ ] `ingest-review` でコメントを取り込める。
- [ ] 確認が必要なコメントにagent replyが残る。
- [ ] 反映後HTMLを再生成できる。
- [ ] UI E2E・JS物理分割・document model反映拡張の要否が評価receiptに記録されている。
- [ ] 実出力評価の結果が `docs/development-plan.html` と `docs/design.html` に反映されている。

## やること

- [ ] 実際の設計資料をdocument model化する。
- [ ] pluginでHTMLを生成する。
- [ ] preview表示を確認する。
- [ ] コメントを入れて保存する。
- [ ] `ingest-review` を実行する。
- [ ] 反映後HTMLを再生成する。
- [ ] UI E2E・JS物理分割・document model反映拡張の不足を #13 へ引き継ぐ。

## 開発計画・設計同期ルール

- 実出力評価で発見した仕様変更、未決事項、次Milestoneは `docs/development-plan.html` に反映する。
- 実装と設計がずれた場合は `docs/design.html` を正す。
- `/backlog progress` では、使用したfixture/出力URL/コメント件数/反映件数に加えて、#13へ引き継ぐhardening項目を記録する。

## Goal 実行

- goal-ready: true
- objective: "CodexでHTMLレビューサイクルを実データで完走させ、設計/計画に反映する"
- scope:
  - "docs/design.html再生成"
  - "preview表示"
  - "comment作成"
  - "ingest-review"
  - "agent reply"
  - "post-evaluation hardening項目の分類"
  - "設計/計画HTML更新"
- stop_conditions:
  - "Codexでレビューサイクルが完走した時"
  - "実出力で設計変更が必要になり、追加判断が必要になった時"
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
