---
id: 9
title: "Milestone 8: Codex Plugin Packaging"
status: バックログ
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

- [ ] Codex plugin構成が検証できる。
  - 検証: `python3 -m json.tool .codex-plugin/plugin.json >/dev/null`
- [ ] Codex marketplace登録方法がdocs化されている。
- [ ] Codex側で2 skillがplugin経由で発火する。
- [ ] base repo管理方式との統合方針が `docs/development-plan.html` と `docs/design.html` に反映されている。
- [ ] plugin versioningとrelease tag手順が決まっている。

## やること

- [ ] `.codex-plugin/plugin.json` を最終化する。
- [ ] Codex marketplace登録手順を作る。
- [ ] `home/skills` とplugin repoの同名skill優先順位を検証する。
- [ ] `bin/build-codex-skills.sh` 生成物との衝突有無を確認する。
- [ ] base repoの `install.sh` に含めるか、個別導入に分けるか決める。

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
