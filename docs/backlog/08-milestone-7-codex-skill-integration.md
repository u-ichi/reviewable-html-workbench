---
id: 8
title: "Milestone 7: Codex Skill Integration"
status: バックログ
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "codex", "skill"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 08: Milestone 7: Codex Skill Integration

## 概要

Codex上で `visual-html-renderer` と `reviewable-design-doc` が共通scriptを使い、一連のHTML生成・preview・review ingestion workflowを実行できるようにする。

## ゴール条件

- [ ] Codexで2つのskillが発火する。
- [ ] `visual-html-renderer` が `render`, `validate`, `preview` を呼ぶ手順を持つ。
- [ ] `reviewable-design-doc` が `render`, `ingest-review`, `preview` を呼ぶ手順を持つ。
- [ ] 同じfixtureから同じ成果物構造が出る。
- [ ] Codex skill統合方針が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [ ] `skills/visual-html-renderer/SKILL.md` を実装に合わせて更新する。
- [ ] `skills/reviewable-design-doc/SKILL.md` を実装に合わせて更新する。
- [ ] `agents/openai.yaml` を同期する。
- [ ] Codexでのskill discovery / triggerを検証する。

## 開発計画・設計同期ルール

- skill境界、trigger、CLI呼び出し順が変わったら `docs/design.html` を更新する。
- Codex統合の完了条件が変わったら `docs/development-plan.html` を更新する。

## Goal 実行

- goal-ready: true
- objective: "Codex上で2つのskillから共通scriptを呼び、一連のHTMLレビューworkflowを実行できるようにする"
- scope:
  - "Codex skill発火"
  - "SKILL.md更新"
  - "openai.yaml同期"
  - "fixture workflow検証"
  - "設計/計画HTML更新"
- stop_conditions:
  - "Codexで2 skillが実行可能になった時"
  - "Codex plugin discovery仕様の追加調査が必要になった時"
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
