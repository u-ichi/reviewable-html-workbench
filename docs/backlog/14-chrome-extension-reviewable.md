---
id: 14
title: "Chrome拡張化によるレビュー機能の汎用化"
status: バックログ
notion_url: "https://app.notion.com/p/3810921ecd0a811ba090c73e74ea2a92"
notion_id: "3810921e-cd0a-811b-a090-c73e74ea2a92"
parent_notion_url: ""
tags: []
assignee: ""
created: 2026-06-16
updated: 2026-06-16
---

# 14: Chrome拡張化によるレビュー機能の汎用化

## 概要

X (Twitter) で @toromo_cd から提案されたアイデア。
現在のレビュー UI（コメント・返信・解決）は workbench で生成した HTML にのみ組み込まれている。
`<meta name="reviewable" content="true">` のような meta タグを検出して、
任意の HTML にレビュー機能を後付けできるブラウザ拡張を開発する。

### 背景

- 現行: agent が document model → render.py → HTML bundle（review-comments.js + style.css 同梱）として生成
- 課題: workbench 以外で作られた HTML にはレビュー機能を使えない
- 提案: meta タグをスイッチにしたブラウザ拡張で、任意 HTML にレビュー UI を注入

### アーキテクチャ方針候補

**案 A: meta タグ検出 → 既存 JS/CSS inject**
- 最も軽量。workbench 生成 HTML のみ対応
- 課題: `data-review-block` が無い HTML では動作しない

**案 B: 軽量 overlay 型**
- 拡張独自のレビュー overlay。既存 HTML 構造に依存しない
- 課題: review-comments.js のほぼ全面書き換え。agent 連携が難しい

**案 C: ハイブリッド（推奨）**
- workbench HTML と汎用 HTML の両方をサポート
- `data-review-block` があれば既存ロジック活用、無ければ自動付与
- Shadow DOM で UI 隔離。コメント永続化は preview server / Extension Storage の切り替え
- Export した comments.json で既存の ingest_review.py と連携可能

### 再利用可能な既存コード

- コメントデータ形式 (`schemas/comments.schema.json`)
- テキスト選択 → アンカー計算 (`selectionAnchorInBlock`, `textNodesIn`)
- ハイライト描画 (`highlightByOffsets`, `wrapTextNodeSlice`)
- コメントカード UI (`renderCommentCards`, `cardInner`)

### 新規開発が必要な部分

- ブラウザ拡張 manifest (Manifest V3)
- `data-review-block` 自動付与ロジック（段落・見出し・リスト検出）
- Shadow DOM ベースの UI ホスティング
- Extension Storage API adapter
- ページ横断のコメント管理（URL ベースの紐付け）

## ゴール条件

- [ ] ブラウザ拡張として Manifest V3 で動作する
  - 検証: 拡張管理画面で unpacked ロードしてエラーが出ないこと
- [ ] `<meta name="reviewable" content="true">` のある HTML ページでレビュー UI が自動有効化される
  - 検証: meta タグ付き HTML をブラウザで開き、テキスト選択 → コメント追加 → 返信 → 解決ができること
- [ ] workbench 生成 HTML（`data-review-block` あり）で既存のコメント機能と同等に動作する
  - 検証: workbench 生成 HTML を拡張経由で開き、コメント位置・ハイライト・カード表示が正しいこと
- [ ] 汎用 HTML（`data-review-block` なし）でもブロック自動検出によりコメントできる
  - 検証: 適当な外部 HTML に meta タグを追加して、段落単位でコメントが付けられること
- [ ] コメントデータが既存の comments.json 形式で Export/Import できる
  - 検証: Export した JSON が `schemas/comments.schema.json` に適合すること

## やること

- [ ] ブラウザ拡張 Manifest V3 の content script 仕様と Shadow DOM 制約を調査
- [ ] review-comments.js から拡張に移植する関数を特定・依存関係を整理
- [ ] data-review-block 自動付与のヒューリスティクス設計
- [ ] Manifest V3 の manifest.json と content script の骨格を作成
- [ ] review-comments.js を拡張用に分離（Shadow DOM 対応）
- [ ] コメント Storage adapter（Extension Storage / HTTP PUT 切り替え）を実装
- [ ] テスト用 HTML（workbench 生成 / 汎用）で動作検証
- [ ] Web Store 公開準備（任意、後回し可）

## Goal 実行

- goal-ready: false
- objective: ""
- scope:
  - ""
- stop_conditions:
  - ""
- verification:
  - ""
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-06-16

- 初期作成。X (Twitter) @toromo_cd の提案に基づくアイデア登録
- 案 A / B / C の 3 方針を整理、案 C（ハイブリッド）を推奨として記載

## 成果物

（完了時に記載）
