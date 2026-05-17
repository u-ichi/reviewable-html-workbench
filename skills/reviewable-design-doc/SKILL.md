---
name: reviewable-design-doc
description: |
  要求・設計・アーキテクチャ・未決事項を整理し、レビュー可能な設計資料HTMLを作りたい時に使う。レビュー完了後はHTMLコメントを読み込み、設計へ反映し、確認が必要な場合はHTMLコメントスレッドへagent返信を書き戻す。Triggers: レビュー可能な設計資料, 設計資料をHTMLで, design doc, reviewable design doc, レビュー終わったので確認して, コメントを反映して。使用しない場面: 汎用HTMLレンダリングだけ、Notion投稿だけ、既存HTMLの見た目修正だけ。
argument-hint: "[設計対象またはdocument-model.json] [--review-mode standalone|review-server] [--preview auto|tailscale|local|off]"
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
5. `render` CLIでHTML bundleを生成する。
6. `validate` CLIでHTML bundleを検証する。
7. preview が有効なら `preview` CLIでURLを提示する。
8. レビュー完了後は `ingest-review` CLIでコメントを分類し、必要に応じて設計へ反映する。
9. 確認が必要なコメントには、チャットだけでなくHTMLコメントへagent replyを書き戻す。

## CodexでのCLI呼び出し

HTML生成時は、`visual-html-renderer` と同じ共通CLI入口を使う。

```bash
python3 -m scripts.html_review_workbench.cli render \
  --model <document-model.json> \
  --output <output-dir>

python3 -m scripts.html_review_workbench.cli validate \
  --root <output-dir>

python3 -m scripts.html_review_workbench.cli preview \
  --root <output-dir> \
  --mode auto
```

レビュー取り込み時は、最新のpreview sessionまたはユーザー指定の成果物rootから `annotations/comments.json` を読み込む。

```bash
python3 -m scripts.html_review_workbench.cli ingest-review \
  --root <output-dir>
```

document modelへ反映する場合は、完全一致置換に限定して明示的に実行する。

```bash
python3 -m scripts.html_review_workbench.cli ingest-review \
  --root <output-dir> \
  --model <document-model.json> \
  --apply-model
```

## 完了時の確認

- `index.html` と `renderer-manifest.json` が生成され、`validate` が `status: ok` を返している。
- レビュー取り込み後、`annotations/review-cycle-state.json` が生成されている。
- `needs_clarification` のコメントにはHTMLコメントスレッド上のagent replyが追加されている。
- コメント反映でユーザー確認が必要な場合は、チャットだけでなくHTMLコメントへ返信している。

## ガード

- 設計として未確定の内容は確定事項と分けて書く。
- レビューコメント機能は必須で有効化する。
- 確認が必要な場合、チャットだけで聞き返さずHTMLコメントへ返信する。
- HTML低レベル実装をこのskillに重複実装しない。
