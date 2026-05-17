---
id: 4
title: "Milestone 3: Diagram Planner"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "diagram", "deferred"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 04: Milestone 3: Diagram Planner

## 概要

図示した方が理解しやすい内容を本文から分離し、Mermaid sourceやfallback表示として成果物内に残せるようにする。

## ゴール条件

- [x] `diagram_planner.py` が図示候補を分類できる。
  - 検証: `python3 -m unittest discover -s tests`
- [x] Mermaid sourceが `assets/diagrams/*.mmd` に保存される。
- [x] Mermaidを直接renderできない環境でもHTMLが壊れない。
- [x] 外部送信を伴う図式/画像生成は承認ゲート対象として `docs/design.html` に明記されている。

## やること

- [x] `flow`, `architecture`, `matrix`, `timeline`, `concept` の分類を実装する。
- [x] Mermaid source保存を実装する。
- [x] HTML fallback表示を実装する。
- [x] 外部レンダラー利用時の承認境界を設計へ反映する。

## 開発計画・設計同期ルール

- 図示判断ポリシー、外部送信境界、図の保存形式が変わったら `docs/design.html` を更新する。
- Diagram Plannerを前倒し/後ろ倒しする場合は `docs/development-plan.html` の優先順位を更新する。

## Goal 実行

- goal-ready: true
- objective: "図示候補を分類し、source保存とfallback表示まで実装する"
- scope:
  - "diagram_planner.py実装"
  - "Mermaid source保存"
  - "HTML fallback"
  - "設計/計画HTML更新"
- stop_conditions:
  - "図示候補分類とsource保存がfixtureで検証できた時"
  - "外部レンダラー利用方針の判断が必要になった時"
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
- 実装: `diagram_planner.py` に図示候補分類、Mermaid source保存計画、safe filename生成を追加。
- Renderer連携: `render.py` で `type: "diagram"` ブロックのMermaid sourceを `assets/diagrams/*.mmd` へ保存し、HTMLにはsource保存先とfallback `<pre>` を表示するようにした。
- 検証強化: `validate_bundle.py` でmanifest上のdiagram asset存在を検証するようにした。
- テスト: `tests/test_renderer_bundle.py` に図示分類、source保存、fallback表示、manifest連携のテストを追加。
- 設計同期: `docs/design.html` と `docs/development-plan.html` にDiagram Plannerの実装済み契約と次タスクを反映。
- 検証: `python3 -m unittest discover -s tests`、`python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`、`python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`、`python3 -m json.tool .claude-plugin/plugin.json >/dev/null`、`python3 -m json.tool .codex-plugin/plugin.json >/dev/null` が通過。

## 成果物

- `scripts/html_review_workbench/diagram_planner.py`
- `scripts/html_review_workbench/render.py`
- `scripts/html_review_workbench/validate_bundle.py`
- `templates/style.css`
- `tests/test_renderer_bundle.py`
- `docs/design.html`
- `docs/development-plan.html`
