---
name: reviewable-design-doc
description: |
  要求・設計・アーキテクチャ・未決事項を整理し、レビュー可能な設計資料HTMLを作りたい時に使う。レビュー完了後はHTMLコメントを読み込み、設計へ反映し、確認が必要な場合はHTMLコメントスレッドへagent返信を書き戻す。Triggers: レビュー可能な設計資料, 設計資料をHTMLで, design doc, reviewable design doc, レビュー終わったので確認して, コメントを反映して。使用しない場面: 汎用HTMLレンダリングだけ、Notion投稿だけ、既存HTMLの見た目修正だけ。
---

# reviewable-design-doc

## 役割

設計資料としてレビューできる構造を作り、最終HTML生成は `visual-html-renderer` に渡す。

レビュー完了後は `annotations/comments.json` を読み、明確な指摘は設計へ反映し、確認が必要な指摘はHTMLの同じコメントスレッドへagent replyとして返信する。

## 基本手順

1. 設計対象、読者、レビュー目的、完了条件を整理する。
2. 要求、制約、アーキテクチャ、代替案、意思決定、未決事項へ分解する。
3. レビュー観点とコメントしてほしい範囲を明示する。
4. 図示要求とreview modeを含む文書モデルを作る。
5. `visual-html-renderer` を使ってHTML bundleとpreview URLを生成する。
6. レビュー完了後は `ingest-review` CLIでコメントを分類し、設計へ反映する。
7. 確認が必要なコメントには、チャットだけでなくHTMLコメントへagent replyを書き戻す。

## ガード

- 設計として未確定の内容は確定事項と分けて書く。
- レビューコメント機能は必須で有効化する。
- 確認が必要な場合、チャットだけで聞き返さずHTMLコメントへ返信する。
- HTML低レベル実装をこのskillに重複実装しない。
