---
id: 11
title: "Milestone 10: Claude Code対応"
status: バックログ
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "claude", "later"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 11: Milestone 10: Claude Code対応

## 概要

Codex版MVPが実出力評価まで完走した後、Claude Code pluginとして同じworkflowを使えるようにする。

## ゴール条件

- [ ] `.claude-plugin/plugin.json` がClaude plugin schemaに合っている。
  - 検証: `claude plugins validate .`
- [ ] `claude --plugin-dir <repo>` で手元起動できる。
- [ ] Claude側で2 skillが発火する。
- [ ] Codexで確立したfixtureと実出力評価をClaudeでも再実行できる。
- [ ] Claude対応方針が `docs/development-plan.html` と `docs/design.html` に反映されている。

## やること

- [ ] Claude plugin schemaに合わせてmanifestを調整する。
- [ ] Claude側のskill discovery / slash command / CLI呼び出し差分を確認する。
- [ ] base repoの `~/.claude/skills` symlink配布と plugin install のどちらを正本にするか決める。
- [ ] Codex fixtureをClaudeでも実行する。
- [ ] Claude固有差分を最小adapterに閉じ込める。

## 開発計画・設計同期ルール

- Claude対応はCodex完走後に開始する。前倒しする場合は `docs/development-plan.html` の優先順位を更新する。
- Claude固有差分がskill境界やscript APIに影響する場合は `docs/design.html` を更新する。
- `/backlog progress` では、Codexとの差分とClaudeで再利用できた範囲を記録する。

## Goal 実行

- goal-ready: true
- objective: "Codexで確立したHTMLレビューworkflowをClaude Code pluginとしても利用可能にする"
- scope:
  - "Claude manifest調整"
  - "claude plugins validate"
  - "Claude skill discovery検証"
  - "Codex fixture再実行"
  - "設計/計画HTML更新"
- stop_conditions:
  - "Claude Codeで同じworkflowが検証できた時"
  - "Claude plugin仕様差分により設計判断が必要になった時"
- verification:
  - "claude plugins validate ."
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
