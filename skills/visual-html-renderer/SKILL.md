---
name: visual-html-renderer
description: |
  HTMLを最終成果物にする時の共通レンダラー。文書モデルを受け取り、説明に有効な図・画像・表現を使ってHTMLを生成し、セッション限定のプレビューURLを提示する。Triggers: HTMLレンダラー, HTML出力を共通化, 図示つきHTML, visual HTML renderer。
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

## ガード

- レンダラーは内容判断を作らない。
- 図示は入力された構造を補助する目的に限定する。
- ブラウザを自動で開かない。URL提示までを責務とする。
- Preview Runtime は `0.0.0.0` にbindしない。
- 外部サービスへ投稿・アップロードする場合は別途承認ゲートを通す。
