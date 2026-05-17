---
id: 3
title: "Milestone 2: HTML Renderer MVP"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "renderer", "html"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 03: Milestone 2: HTML Renderer MVP

## 概要

最小文書モデルから `index.html` と `renderer-manifest.json` を生成し、review blockを持つHTML bundleを作れるようにする。

## ゴール条件

- [x] `render` CLIがfixtureからHTML bundleを生成できる。
  - 検証: `python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`
- [x] `validate` CLIがHTML / manifest / review blockを検証できる。
  - 検証: `python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`
- [x] 生成HTMLが `data-review-block` を持つ。
  - 検証: `rg -n "data-review-block" output/tmp/test-render/index.html`
- [x] renderer仕様変更が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [x] `render.py` をplaceholderから実装する。
- [x] `templates/report.html.j2` を実用テンプレートにする。
- [x] `templates/style.css` を整理する。
- [x] `renderer-manifest.json` に入力hash、生成時刻、renderer versionを残す。
- [x] `validate_bundle.py` の最小検証を実装する。

## 開発計画・設計同期ルール

- HTML構造、CSS方針、review block規約を変更したら `docs/design.html` を更新する。
- Renderer MVPの完了条件や検証コマンドが変わったら `docs/development-plan.html` を更新する。
- `/backlog progress` では実際に生成したHTML出力先を記録する。

## Goal 実行

- goal-ready: true
- objective: "最小文書モデルからreview可能なHTML bundleを生成・検証できるようにする"
- scope:
  - "render.py実装"
  - "HTML template整備"
  - "manifest生成"
  - "validate最小実装"
  - "設計/計画HTML更新"
- stop_conditions:
  - "fixtureからHTML生成とvalidateが成功した時"
  - "renderer contractの変更が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
  - "python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render"
  - "python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render"
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 実装: `render.py` / `validate_bundle.py` / `cli.py` をRenderer MVPとして実装し、`templates/report.html.j2` と `templates/style.css` をreview block付きHTML bundle向けに更新。
- テスト: `tests/test_renderer_bundle.py` を追加し、manifest、asset、`data-review-block`、bundle validationを検証。
- 設計同期: `docs/design.html` と `docs/development-plan.html` にmanifest項目とvalidate範囲を反映。
- 生成物管理: `output/` をgit管理外にするため `.gitignore` に追加。
- 検証: `python3 -m unittest discover -s tests`、`python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`、`python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`、`rg -n "data-review-block" output/tmp/test-render/index.html`、`claude plugins validate .` が通過（Claude plugin validate は既存の `CLAUDE.md` warning あり）。
- 完了: ゴール条件を再検証し、backlogを完了へ更新。

## 成果物

- `scripts/html_review_workbench/render.py`: fixtureからreview block付きHTML bundleを生成。
- `scripts/html_review_workbench/validate_bundle.py`: HTML / manifest / review blockの最小検証を実装。
- `templates/report.html.j2` / `templates/style.css`: 実用テンプレートとbundle CSSを整備。
- `tests/test_renderer_bundle.py`: manifest、asset、diagram fallback、`data-review-block`、bundle validationを検証。
- `docs/design.html` / `docs/development-plan.html`: Renderer MVP仕様と完了条件を同期。
