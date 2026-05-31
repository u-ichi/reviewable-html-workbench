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
4. 最初から `document-model.json` を作る。設計本文の下書きや中間成果物として `.md` を作らない。
5. 文書モデルには、要求、制約、アーキテクチャ、代替案、意思決定、未決事項、レビュー観点を、それぞれHTML表現を選んだblockとして入れる。
6. `render` CLIでHTML bundleを生成する。
7. `validate` CLIでHTML bundleを検証する。
8. ユーザー向け最終HTMLでは既定で `preview` CLIを `--mode auto` で起動し、返却JSONの `url` と `stop_command` を最終応答に必ず書く。
9. レビュー完了後は `ingest-review` CLIでコメントを分類し、必要に応じて設計へ反映する。
10. 確認が必要なコメントには、チャットだけでなくHTMLコメントへagent replyを書き戻す。

## 設計資料モデル作成の規約

設計資料作成は、`.md` 原稿をHTMLへ変換する作業ではない。`reviewable-design-doc` は、設計内容を最初からレビュー可能なHTML bundleの情報設計として作る。

- 新規に設計資料を作る場合、最初の保存対象は `output/tmp/<purpose>/document-model.json` または `output/<YYYY-MM-DD>_<name>/document-model.json` にする。
- `.md` ファイルを設計本文の下書き、中間成果物、HTML化対象として作らない。
- 一時的に自然文入力を保存する必要がある場合だけ、`source.txt`, `input.txt`, `source-content.txt` のようなプレーンテキスト名を使う。
- 設計資料の本文は、見出し記号を含む原稿ではなく、`blocks[].title`, `blocks[].type`, `blocks[].content`, `review_required` を持つ文書モデルとして表現する。
- 比較・代替案・評価軸は表、処理・依存・構成はMermaid図、決定・前提・注意はcallout、操作例・ログ・コマンドはコードブロック、レビューしてほしい論点は専用のレビュー観点blockにする。
- 既存資料を取り込む場合も、既存ファイルをそのまま表示へ流し込まず、`visual-html-renderer` のHTML情報設計規約に従って文書モデルへ再構成する。
- `build-model` を使うのは、既存本文やユーザー指定内容から文書モデルを作る場合に限る。新規設計では、agentが設計構造を判断して文書モデルを直接作る。

## CodexでのCLI呼び出し

HTML生成時は、`visual-html-renderer` と同じ共通CLI入口を使う。

```bash
python3 -m scripts.html_review_workbench.cli build-model \
  --text "<existing content when converting an existing source>" \
  --output <document-model.json>

python3 -m scripts.html_review_workbench.cli render \
  --model <document-model.json> \
  --output <output-dir>

python3 -m scripts.html_review_workbench.cli validate \
  --root <output-dir>

python3 -m scripts.html_review_workbench.cli preview \
  --root <output-dir> \
  --mode auto
```

Codex sandbox内で `tailscale ip -4` が設定ファイル読み取りに失敗する場合は、`visual-html-renderer` と同じく `python3 -m scripts.html_review_workbench.preview_host_resolve` で取得したIPv4を `HTML_REVIEW_WORKBENCH_TAILSCALE_IP` に渡してから `preview --mode auto` を起動する。

`preview` が `status: running` を返した場合、レビュー依頼の最終応答に `url` を必ず含める。ファイルパスだけで完了しない。preview server は起動元 agent の親PIDを監視し、その親プロセスが終了すると自動終了するため、通常はsession終了時に追加のlist GCを必要としない。

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
- preview有効時は、レビュー用URLをユーザーへ提示している。
- レビュー取り込み後、`annotations/review-cycle-state.json` が生成されている。
- `needs_clarification` のコメントにはHTMLコメントスレッド上のagent replyが追加されている。
- コメント反映でユーザー確認が必要な場合は、チャットだけでなくHTMLコメントへ返信している。

## ガード

- 設計として未確定の内容は確定事項と分けて書く。
- レビューコメント機能は必須で有効化する。
- 確認が必要な場合、チャットだけで聞き返さずHTMLコメントへ返信する。
- HTML低レベル実装をこのskillに重複実装しない。
