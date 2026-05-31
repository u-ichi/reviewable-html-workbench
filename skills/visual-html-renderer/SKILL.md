---
name: visual-html-renderer
description: |
  HTMLを最終成果物として生成・検証・プレビューしたい時に使う共通レンダラー。文書モデル、直前の成果物、またはユーザー指定内容から、段落・表・リスト・コード・注記・Mermaid図を選んだHTML bundleを生成し、セッション限定のプレビューURLを提示する。Triggers: html出力して, HTMLにして, HTMLで出して, この内容をHTMLで出して, HTMLでプレビューして, HTMLレンダラー, HTML出力を共通化, 図示つきHTML, visual HTML renderer。使用しない場面: 設計内容そのものの作成、Notion投稿だけ、既存HTMLの軽微な見た目修正だけ。
argument-hint: "[document-model.json] [--output output/<date>_<slug>] [--preview auto|tailscale|local|off]"
---

# visual-html-renderer

## 役割

HTML出力系skillの共通レンダラーとして、個別HTML生成ロジックを置き換える。

重い処理は `scripts/html_review_workbench/` のPython実装に委譲し、このskillは入力確認、呼び出し順、ガード、検証を担当する。

## 基本手順

1. 文書モデルとレンダリングオプションを確認する。
2. 文書モデルが未指定の場合は、直前の成果物またはユーザー指定内容から `build-model` で文書モデルを作る。
3. `build-model` は content planner + visual planner として、情報構造と表現方法を選ぶ。
4. `build-model` が画像ブロックを作った場合は、`imagegen` skillで画像を生成し、`attach-image` CLIで文書モデルへ添付する。
5. `render` CLIでHTML bundleを生成する。
6. `validate` CLIでHTML、asset、comment schema、図・画像の非空を検証する。
7. ユーザー向け最終HTMLでは既定で `preview` CLIを `--mode auto` で起動し、返却JSONの `url` と `stop_command` を最終応答に必ず書く。

## HTML情報設計の規約

HTML出力はテキスト変換ではなく、最終HTML bundleの情報設計として扱う。

- 入力本文の記号や行構造をそのまま表示へ流し込まない。
- まず内容の意味、用途、読者、比較軸、時系列、依存関係、操作手順、注意点を読み取り、HTML上の表現を選ぶ。
- 比較は表、手順は番号付きリスト、並列項目はリスト、注意・決定・前提はcallout、処理や依存関係はMermaid図、画面イメージや説明画像が有効な箇所は画像ブロック、コマンドやログはコードブロックにする。
- `build-model` の既存ブロック型で表現が足りない場合、段落へ潰さず、必要なブロック型やレンダリング拡張を検討する。
- 一時入力ファイルが必要な場合も `.md` は使わない。`source.txt`, `input.txt`, `source-content.txt` のようなプレーンテキスト名を使う。
- ユーザーへの進捗・最終報告では、`.md` やMarkdownという語をHTML出力の前提として扱わない。

## 入力モデル未指定時の規約

ユーザーが「html出力して」「HTMLにして」「HTMLで出して」のように自然文で依頼し、`document-model.json` を指定していない場合も、このskillを発火させる。

その場合は、次の順で入力を決める。

1. ユーザーが明示した対象ファイル、本文、直前の成果物をHTML化対象にする。
2. 対象が曖昧で、直前の成果物も特定できない場合だけ、短く確認する。
3. 対象を特定できる場合は、確認で止めずに `build-model` で `output/tmp/<purpose>/document-model.json` を作る。
4. 作成する文書モデルは `schema_version`, `document_id`, `title`, `generated_at`, `blocks` を必ず持つ。
5. 画像ブロックがある場合は画像生成と `attach-image` を完了してから、`render` → `validate` → `preview` まで進める。

`build-model` は入力内容に応じて、段落、表、リスト、コード、callout、Mermaid図、画像ブロックを選ぶ。画像ブロックがある場合、最終HTML出力では `imagegen` skillで画像を生成してから `attach-image` で文書モデルへ添付する。画像生成が外部サービス送信・機密情報・ユーザー承認を要する条件に当たる場合は、該当する承認ゲートに従う。設計判断、要求整理、レビュー観点の作成が主目的の場合は `reviewable-design-doc` を使う。

## CodexでのCLI呼び出し

このskillは、低レベル実装へ直接importせず、repo rootから共通CLIだけを呼ぶ。

```bash
python3 -m scripts.html_review_workbench.cli build-model \
  --text "<content>" \
  --output <document-model.json>

python3 -m scripts.html_review_workbench.cli attach-image \
  --model <document-model.json> \
  --block-id <image-block-id> \
  --image <generated-image-path>

python3 -m scripts.html_review_workbench.cli render \
  --model <document-model.json> \
  --output <output-dir>

python3 -m scripts.html_review_workbench.cli validate \
  --root <output-dir>

python3 -m scripts.html_review_workbench.cli preview \
  --root <output-dir> \
  --mode auto
```

Codex sandbox内で `tailscale ip -4` が設定ファイル読み取りに失敗する場合は、preview本体をsandbox内で起動したまま、IPだけを小さいresolverで先に取得して渡す。

```bash
python3 -m scripts.html_review_workbench.preview_host_resolve

HTML_REVIEW_WORKBENCH_TAILSCALE_IP=<tailscale-ip> \
  python3 -m scripts.html_review_workbench.cli preview \
    --root <output-dir> \
    --mode auto
```

ユーザーが明示的にプレビュー不要と言った場合、または自動テスト・fixture検証で副作用を抑える場合だけ `--mode off` を使う。ユーザー向け成果物では `--mode off` を既定にしない。
成果物はユーザーが直接読む最終HTMLなら `output/<YYYY-MM-DD>_<name>/`、再利用しない検証なら `output/tmp/<purpose>/` に置く。

## Preview URL提示とライフサイクル

- `preview` が `status: running` を返した場合、最終応答に `url` を必ず含める。ファイルパスだけで完了しない。
- `preview` が `status: off` または `status: failed` の場合、URLが無い理由を明示し、可能なら `--mode auto` で再実行してURL提示まで進める。
- preview server は起動元 agent の親PIDを監視し、その親プロセスが終了すると自動終了する。通常はsession終了時に追加のlist GCを必要としない。
- 手動停止が必要な時だけ、返却JSONの `stop_command` を使う。PIDなしで全previewを停止しない。

## 完了時の確認

- `index.html` と `renderer-manifest.json` が生成されている。
- `validate` が `status: ok` を返している。
- preview 有効時は提示URL、bind先、PID、停止方法をユーザーへ伝える。
- preview は `0.0.0.0` にbindしていない。

## ガード

- レンダラーは内容判断を作らない。
- 図示は入力された構造を補助する目的に限定する。
- ブラウザを自動で開かない。URL提示までを責務とする。
- Preview Runtime は `0.0.0.0` にbindしない。
- 外部サービスへ投稿・アップロードする場合は別途承認ゲートを通す。
