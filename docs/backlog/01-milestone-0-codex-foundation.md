---
id: 1
title: "Milestone 0: Codex基盤整理"
status: 進行中
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "codex-first", "foundation"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 01: Milestone 0: Codex基盤整理

## 概要

Codex firstで開発を進めるため、CI、Codex plugin manifest、skill description、CLI契約、設計ドキュメント同期の基盤を整える。

## ゴール条件

- [ ] `main` pushでCIが通る。
  - 検証: `python3 -m unittest discover -s tests`
- [x] `.codex-plugin/plugin.json` の必須fieldと検証方法が明文化されている。
  - 検証: `python3 -m json.tool .codex-plugin/plugin.json >/dev/null`
- [x] `docs/development-plan.html` と `docs/design.html` がMilestone 0完了状態に更新されている。
  - 検証: `test -f docs/development-plan.html && test -f docs/design.html`

## やること

- [x] `.github/workflows/test.yml` を追加する。
- [x] Codex manifest / skill discovery の検証手順を追加する。
- [x] `skills/*/SKILL.md` のdescriptionをCodex発火に合わせて調整する。
- [x] `scripts.html_review_workbench.cli` のsubcommand契約を固定する。

## 開発計画・設計同期ルール

- 作業開始時に `docs/development-plan.html` と `docs/design.html` の関連箇所を確認する。
- 大きい進捗、Milestone順序、完了条件、リスクが変わった場合は `docs/development-plan.html` を同じ作業内で更新する。
- skill範囲、データ構造、Preview Runtime、コメント取り込み仕様が変わった場合は `docs/design.html` も同じ作業内で更新する。
- `/backlog progress` では、更新した計画/設計セクションを進捗ログに記録する。
- `/backlog done` は、開発計画と設計の更新要否を確認してから完了にする。

## Goal 実行

- goal-ready: true
- objective: "Codex firstのplugin開発を進められる基盤を整え、CIと計画/設計同期ルールを有効にする"
- scope:
  - "CI追加"
  - "Codex manifest検証"
  - "skill description調整"
  - "development-plan/design同期"
- stop_conditions:
  - "CIが通り、Milestone 0のゴール条件を満たした時"
  - "Codex plugin構成の前提が崩れ、設計判断が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
  - "python3 -m json.tool .codex-plugin/plugin.json >/dev/null"
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 作業開始。CI、Codex manifest検証、skill discovery、CLI契約、開発計画/設計同期をMilestone 0の実施範囲として確認。
- `.github/workflows/test.yml` を追加し、`main` push / pull request で unittest、manifest JSON syntax check、CLI help check を実行するようにした。
- `tests/test_project_layout.py` に Codex manifest必須field、skill description、CLI subcommand契約の検証を追加。
- `scripts.html_review_workbench.cli` に `render` / `preview` / `ingest-review` / `validate` の `COMMAND_CONTRACT` を追加。
- `skills/*/SKILL.md` のdescriptionに Codex発火用の用途と使用しない場面を明記。
- `docs/development-plan.html` の Milestone 0 を完了状態に更新し、`docs/design.html` に Codex基盤契約を追加。
- 検証: `python3 -m unittest discover -s tests` passed (5 tests)。
- 検証: `python3 -m json.tool .codex-plugin/plugin.json` passed。
- 検証: `python3 -m scripts.html_review_workbench.cli --help` passed。
- 検証: `claude plugins validate .` passed with warning (`CLAUDE.md` at plugin root is not loaded as project context)。
- 未実施: `main` push 後の GitHub Actions 実測確認は commit/push 承認後に行う。

## 成果物

- `.github/workflows/test.yml`
- `tests/test_project_layout.py`
- `scripts/html_review_workbench/cli.py`
- `skills/visual-html-renderer/SKILL.md`
- `skills/reviewable-design-doc/SKILL.md`
- `docs/development-plan.html`
- `docs/design.html`
