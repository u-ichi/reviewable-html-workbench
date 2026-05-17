---
id: 4
title: "Milestone 3: Diagram Planner"
status: バックログ
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

- [ ] `diagram_planner.py` が図示候補を分類できる。
  - 検証: `python3 -m unittest discover -s tests`
- [ ] Mermaid sourceが `assets/diagrams/*.mmd` に保存される。
- [ ] Mermaidを直接renderできない環境でもHTMLが壊れない。
- [ ] 外部送信を伴う図式/画像生成は承認ゲート対象として `docs/design.html` に明記されている。

## やること

- [ ] `flow`, `architecture`, `matrix`, `timeline`, `concept` の分類を実装する。
- [ ] Mermaid source保存を実装する。
- [ ] HTML fallback表示を実装する。
- [ ] 外部レンダラー利用時の承認境界を設計へ反映する。

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

## 成果物

（完了時に記載）
