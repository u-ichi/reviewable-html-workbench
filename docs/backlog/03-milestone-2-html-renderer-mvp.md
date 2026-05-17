---
id: 3
title: "Milestone 2: HTML Renderer MVP"
status: バックログ
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

- [ ] `render` CLIがfixtureからHTML bundleを生成できる。
  - 検証: `python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`
- [ ] `validate` CLIがHTML / manifest / review blockを検証できる。
  - 検証: `python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`
- [ ] 生成HTMLが `data-review-block` を持つ。
  - 検証: `rg -n "data-review-block" output/tmp/test-render/index.html`
- [ ] renderer仕様変更が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [ ] `render.py` をplaceholderから実装する。
- [ ] `templates/report.html.j2` を実用テンプレートにする。
- [ ] `templates/style.css` を整理する。
- [ ] `renderer-manifest.json` に入力hash、生成時刻、renderer versionを残す。
- [ ] `validate_bundle.py` の最小検証を実装する。

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

## 成果物

（完了時に記載）
