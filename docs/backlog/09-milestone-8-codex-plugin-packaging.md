---
id: 9
title: "Milestone 8: Codex Plugin Packaging"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "codex", "plugin", "base-repo"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 09: Milestone 8: Codex Plugin Packaging

## 概要

Codex CLIでpluginとして読み込める状態にし、base repoの `home/skills` / `home/generated/codex-skills` 管理方式とplugin管理のどちらを正本にするか決める。

## ゴール条件

- [x] Codex plugin構成が検証できる。
  - 検証: `python3 -m json.tool .codex-plugin/plugin.json >/dev/null`
- [x] Codex marketplace登録方法がdocs化されている。
- [x] Codex側で2 skillがplugin経由で発火する。
  - 旧構成 (`AVAILABLE` + `source.path: "."`) では新規 Codex process の skill discovery に載らないことを確認。
  - `INSTALLED_BY_DEFAULT` + `source.path: "./plugins/reviewable-html-workbench"` + symlink 構成へ修正済み。
  - `~/.codex/skills` へ2 skillをmaterializeし、新規Codex processで `reviewable-html-workbench:visual-html-renderer` と `reviewable-html-workbench:reviewable-design-doc` の発火を確認。
- [x] base repo管理方式との統合方針が `docs/development-plan.html` と `docs/design.html` に反映されている。
- [x] plugin versioningとrelease tag手順が決まっている。

## やること

- [x] `.codex-plugin/plugin.json` を最終化する。
- [x] Codex marketplace登録手順を作る。
- [x] `home/skills` とplugin repoの同名skill優先順位を検証する。
- [x] `bin/build-codex-skills.sh` 生成物との衝突有無を確認する。
- [x] base repoの `install.sh` に含めるか、個別導入に分けるか決める。

## 開発計画・設計同期ルール

- base repo統合方針、plugin正本、adapter方針が変わったら `docs/development-plan.html` と `docs/design.html` を更新する。
- `/backlog progress` では、採用した管理方式と未決事項を明記する。

## Goal 実行

- goal-ready: true
- objective: "Codex pluginとして配布・導入できる形にし、base repo管理方式との統合方針を決める"
- scope:
  - "Codex plugin packaging"
  - "marketplace登録手順"
  - "base repo統合方針"
  - "versioning/release"
  - "設計/計画HTML更新"
- stop_conditions:
  - "Codex plugin導入方式とbase repo統合方針が決まった時"
  - "Codex plugin仕様またはbase repo install設計の判断が必要になった時"
- verification:
  - "python3 -m json.tool .codex-plugin/plugin.json >/dev/null"
  - "python3 -m unittest discover -s tests"
- goal: docs/goals/09-milestone-8-codex-plugin-packaging/goal.md
- state: docs/goals/09-milestone-8-codex-plugin-packaging/state.yaml
- final_receipt: docs/goals/09-milestone-8-codex-plugin-packaging/notes/verification-2026-05-17.md

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 着手。Goal実行入力とGoalBuddy stateを生成し、Codex plugin packagingの実装を開始。
- `.agents/plugins/marketplace.json` と `docs/codex-plugin-packaging.md` を追加し、repo-local marketplace登録手順を固定。
- base repo / live skills に同名skillが無いことを確認し、plugin repoを管理元、base repo `install.sh` には含めない方針を設計/計画HTMLへ反映。
- 一時 `CODEX_HOME` + `/private/tmp` symlink 経由で `codex plugin marketplace add` が成功。実ユーザー環境への登録とskill発火確認は承認待ち。
- 実ユーザー環境に marketplace と plugin enabled 行を追加したが、旧 `AVAILABLE` + `source.path: "."` 構成では新規 Codex process の skill discovery に載らなかった。
- Codex loader の既存例に合わせ、`plugins/reviewable-html-workbench -> ..` symlink、`source.path: "./plugins/reviewable-html-workbench"`、`policy.installation: "INSTALLED_BY_DEFAULT"` へ修正。
- `~/.codex/skills/visual-html-renderer` と `~/.codex/skills/reviewable-design-doc` を plugin repo のskillへsymlinkし、新規Codex processでplugin namespace付き発火を確認。

## 成果物

- `.agents/plugins/marketplace.json`
- `plugins/reviewable-html-workbench` symlink
- `docs/codex-plugin-packaging.md`
- `docs/goals/09-milestone-8-codex-plugin-packaging/goal.md`
- `docs/goals/09-milestone-8-codex-plugin-packaging/state.yaml`
- `docs/goals/09-milestone-8-codex-plugin-packaging/notes/verification-2026-05-17.md`
