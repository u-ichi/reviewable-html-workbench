---
id: 8
title: "Milestone 7: Codex Skill Integration"
status: 完了
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

- [x] Codexで2つのskillが発火する。
- [x] `visual-html-renderer` が `render`, `validate`, `preview` を呼ぶ手順を持つ。
- [x] `reviewable-design-doc` が `render`, `ingest-review`, `preview` を呼ぶ手順を持つ。
- [x] 同じfixtureから同じ成果物構造が出る。
- [x] Codex skill統合方針が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [x] `skills/visual-html-renderer/SKILL.md` を実装に合わせて更新する。
- [x] `skills/reviewable-design-doc/SKILL.md` を実装に合わせて更新する。
- [x] `agents/openai.yaml` を同期する。
- [x] Codexでのskill discovery / triggerを検証する。

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
- goal: "docs/goals/08-milestone-7-codex-skill-integration/goal.md"
- state: "docs/goals/08-milestone-7-codex-skill-integration/state.yaml"
- final_receipt: "docs/goals/08-milestone-7-codex-skill-integration/notes/verification-2026-05-17.md"

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 作業開始。Goal入力とGoalBuddy stateを `docs/goals/08-milestone-7-codex-skill-integration/` に生成し、frontmatterを `進行中` に更新。
- 実装完了。2つのSKILL.mdに共通CLI workflowを追加し、`agents/openai.yaml` のtrigger/entrypoint/workflowを同期。fixture workflow検証を `tests/test_codex_skill_integration.py` に追加し、設計/計画HTMLへCodex統合方針を反映。検証receipt: `docs/goals/08-milestone-7-codex-skill-integration/notes/verification-2026-05-17.md`。
- 完了。`/backlog done 08 --from-goal docs/goals/08-milestone-7-codex-skill-integration` 相当の完了判定として、GoalBuddy stateを session_complete に更新。

## 成果物

- `skills/visual-html-renderer/SKILL.md`
- `skills/reviewable-design-doc/SKILL.md`
- `skills/visual-html-renderer/agents/openai.yaml`
- `skills/reviewable-design-doc/agents/openai.yaml`
- `tests/test_codex_skill_integration.py`
- `docs/design.html`
- `docs/development-plan.html`
- `docs/goals/08-milestone-7-codex-skill-integration/notes/verification-2026-05-17.md`
