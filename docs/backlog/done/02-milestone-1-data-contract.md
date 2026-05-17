---
id: 2
title: "Milestone 1: Data Contract"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "schema", "contract"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 02: Milestone 1: Data Contract

## 概要

HTML生成、コメント保存、Preview Runtimeの入出力schemaを固定し、後続実装をfixture駆動で進められる状態にする。

## ゴール条件

- [x] `document-model.json` schemaが定義されている。
  - 検証: `test -f schemas/document-model.schema.json`
- [x] `comments.json` schemaが定義されている。
  - 検証: `test -f schemas/comments.schema.json`
- [x] `preview-session.json` schemaが定義されている。
  - 検証: `test -f schemas/preview-session.schema.json`
- [x] 最小fixtureとschema validation testがある。
  - 検証: `python3 -m unittest discover -s tests`
- [x] schema変更が `docs/development-plan.html` と `docs/design.html` に反映されている。
  - 検証: `rg -n "document-model|comments.json|preview-session" docs/development-plan.html docs/design.html`

## やること

- [x] `schemas/` を作成する。
- [x] `tests/fixtures/minimal_document_model.json` を追加する。
- [x] schema validation helperを実装する。
- [x] コメントreply/statusのschemaを明確化する。

## 開発計画・設計同期ルール

- schemaのfield追加/削除/意味変更は `docs/design.html` のデータ構造説明へ反映する。
- Milestone範囲や完了条件が変わった場合は `docs/development-plan.html` を更新する。
- `/backlog progress` には変更したschema名と設計反映有無を記録する。

## Goal 実行

- goal-ready: true
- objective: "renderer/comment/previewのデータ契約を固定し、以降の実装をfixtureで検証可能にする"
- scope:
  - "3 schema作成"
  - "fixture追加"
  - "schema validation test追加"
  - "設計/計画HTML更新"
- stop_conditions:
  - "schema validation testが通った時"
  - "field設計に未決事項が残り、ユーザー判断が必要になった時"
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
- `schemas/document-model.schema.json`, `schemas/comments.schema.json`, `schemas/preview-session.schema.json` を追加。
- `tests/fixtures/minimal_document_model.json`, `tests/fixtures/minimal_comments.json`, `tests/fixtures/minimal_preview_session.json` を追加。
- `scripts/html_review_workbench/schema_validation.py` と `tests/test_schema_validation.py` を追加し、標準ライブラリだけでfixture validationできるようにした。
- `docs/design.html` と `docs/development-plan.html` にschema契約、fixture、コメントstatus/reply構造を反映。
- 検証: `python3 -m unittest discover -s tests` は 9 tests passed。
- 完了: ゴール条件を再検証し、backlog を完了へ移動。
- 完了判定レビューで Preview Runtime の `0.0.0.0` bind 禁止を schema にも入れるべきと判断し、`preview-session.schema.json` と validation test に反映。

## 成果物

- `schemas/document-model.schema.json`
- `schemas/comments.schema.json`
- `schemas/preview-session.schema.json`
- `tests/fixtures/minimal_document_model.json`
- `tests/fixtures/minimal_comments.json`
- `tests/fixtures/minimal_preview_session.json`
- `scripts/html_review_workbench/schema_validation.py`
- `tests/test_schema_validation.py`
