---
id: 6
title: "Milestone 5: Comment UI and Store"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "comments", "ui"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 06: Milestone 5: Comment UI and Store

## 概要

HTML上で範囲選択コメントを作成し、thread / reply / statusを持つ `comments.json` として保存できるようにする。

## ゴール条件

- [x] HTML上で範囲選択コメントを作成できる。
- [x] `comments.json` にcomment threadが保存される。
- [x] agent reply / statusをschemaとして保持できる。
- [x] 保存先が成果物ディレクトリ外へ出ない。
- [x] Preview URLでユーザーがコメント作成・保存・再読込を確認できる。
- [x] コメントUI/保存仕様が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [x] `templates/review-comments.js` を実装する。
- [x] Selection APIからblock id、選択テキスト、前後文脈を取得する。
- [x] `comment_store.py` を実装する。
- [x] standalone modeのlocalStorage export/importを実装する。
- [x] review-server modeで `comments.json` を正本にする。

## 開発計画・設計同期ルール

- コメントschema、UI動作、保存先制約が変わったら `docs/design.html` を更新する。
- Comment UI milestoneの順序や完了条件が変わったら `docs/development-plan.html` を更新する。

## Goal 実行

- goal-ready: true
- objective: "HTML上の範囲選択コメントをcomments.jsonへ安全に保存できるようにする"
- scope:
  - "review-comments.js実装"
  - "comment_store.py実装"
  - "comments schema対応"
  - "設計/計画HTML更新"
- stop_conditions:
  - "コメント作成、保存、再読込が検証できた時"
  - "Preview URLでユーザー確認が完了した時"
  - "ブラウザ側UI仕様の判断が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
  - "Preview URLでのユーザー確認"
- goal: "docs/goals/06-milestone-5-comment-ui-store/goal.md"
- state: "docs/goals/06-milestone-5-comment-ui-store/state.yaml"
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 作業着手。06完了直前、07着手前にPreview URLでユーザー確認するゲートを追加。
- 実装と自動検証完了。Preview URL `http://127.0.0.1:62515/index.html` でユーザー確認待ち。
- ユーザー確認を受け、固定サイドパネル型から範囲選択近傍に表示するNotion風コメントUIへ変更。保存済みコメントは本文側ハイライトをクリックしてthread popoverを開く。
- ユーザー確認を受け、thread popoverにコメント編集、削除、ユーザー返信追加を追加。`テスト` commentへagent replyを追加して往復確認待ち。
- ユーザー確認を受け、thread popoverの `user:note` などの機械的表記を廃止。初回コメントは `Cmd+Enter` / `Ctrl+Enter` またはCommentボタンで投稿し、返信欄は `Enter` で投稿、`Shift+Enter` で改行するUXへ変更。
- ユーザー確認を受け、見出しから本文に跨る複数text node選択コメントに対応。`anchor.start/end` を保存し、複数nodeへ分割ハイライトする。
- ユーザー確認を受け、ヘッダーを含む生成HTML全域をコメント可能に変更。画像/Mermaid挙動確認用サンプルPreview `http://127.0.0.1:51689/index.html` を作成。
- ユーザー確認を受け、SVG内textへHTML `<mark>` を挿入しないよう修正。SVG文字コメントは保存とblock強調で扱い、SVG DOMを壊さない。
- ユーザー確認を受け、描画済みMermaid相当のSVGサンプルを追加。SVG textコメントは保存し、text範囲ハイライト不能時はblock-level badgeからthreadを開けるようにした。
- ユーザー確認を受け、`selected_text` fallback経路でもSVG text nodeを除外。描画済みMermaidの文字が消える不具合を修正。
- ユーザーが追加した4件のコメントすべてにagent replyを追加。返信があるthreadは本文ハイライト、review block枠、block-level badgeを青系に変え、未返信コメントと区別できるようにした。
- ユーザー確認を受け、返信欄の投稿キーを `Enter` に変更し、`Shift+Enter` では改行を保持するようにした。初回コメント欄は `Cmd+Enter` / `Ctrl+Enter` とCommentボタンで投稿する。
- ユーザー確認を受け、画面下部のコメントでもthread popoverがviewport内に収まり、返信欄まで操作できるようにした。
- ユーザー確認を受け、statusを `needs_agent_review` / `needs_user_reply` / `resolved` に絞った。ハイライト色はstatusで判定し、`needs_user_reply` は青系、`resolved` は薄いグレー系、`needs_agent_review` は通常色にした。
- 追加開発で膨らんだ `review-comments.js` を整理。status文字列を定数化し、ハイライトmark生成とstatus別class付与を共通化。読み込み時に旧statusや欠損reply配列をMVPの3状態へ正規化する入口を追加。
- ユーザー確認ゲート完了。「一通り問題無さそう」を受け、Preview URLでのコメント作成・保存・再読込確認を完了扱いにした。

## 成果物

- コメントUI: `templates/review-comments.js`
- コメントUI style: `templates/style.css`
- コメントschema: `schemas/comments.schema.json`
- コメント保存層: `scripts/html_review_workbench/comment_store.py`
- Preview保存API: `scripts/html_review_workbench/preview_server.py`
- renderer組み込み: `scripts/html_review_workbench/render.py`, `templates/report.html.j2`
- 設計同期: `docs/design.html`, `docs/development-plan.html`
- 検証記録: `docs/goals/06-milestone-5-comment-ui-store/notes/verification-2026-05-17.md`
