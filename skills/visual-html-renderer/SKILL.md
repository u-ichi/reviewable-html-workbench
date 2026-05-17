---
name: visual-html-renderer
description: |
  HTMLを最終成果物として生成・検証・プレビューしたい時に使う共通レンダラー。文書モデルを受け取り、説明に有効な図・画像・表現を使ってHTML bundleを生成し、セッション限定のプレビューURLを提示する。Triggers: HTMLレンダラー, HTML出力を共通化, 図示つきHTML, visual HTML renderer。使用しない場面: 設計内容そのものの作成、Notion投稿だけ、既存HTMLの軽微な見た目修正だけ。
argument-hint: "[document-model.json] [--output output/<date>_<slug>] [--preview auto|tailscale|local|off]"
---

# visual-html-renderer

## 役割

HTML出力系skillの共通レンダラーとして、個別HTML生成ロジックを置き換える。

重い処理は `scripts/html_review_workbench/` のPython実装に委譲し、このskillは入力確認、呼び出し順、ガード、検証を担当する。

## 基本手順

1. 文書モデルとレンダリングオプションを確認する。
2. 図示・画像化した方が理解しやすいブロックを抽出する。
3. `render` CLIでHTML bundleを生成する。
4. `validate` CLIでHTML、asset、comment schema、図の非空を検証する。
5. preview が有効なら `preview` CLIでサーバーを起動し、URLと停止方法を提示する。

## CodexでのCLI呼び出し

このskillは、低レベル実装へ直接importせず、repo rootから共通CLIだけを呼ぶ。

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

プレビュー不要、または自動起動を避ける検証では `--mode off` を使う。
成果物はユーザーが直接読む最終HTMLなら `output/<YYYY-MM-DD>_<name>/`、再利用しない検証なら `output/tmp/<purpose>/` に置く。

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
