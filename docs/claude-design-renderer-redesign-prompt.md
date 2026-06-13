# Claude Design 用プロンプト: Reviewable HTML Workbench 描画改善

このファイルは、Reviewable HTML Workbench の描画デザイン改善案を Claude Design に作らせるための投入プロンプトです。
実装はまだ行わず、返ってきた内容を Codex / Claude Code の改修計画へ引き渡す前提で使います。

## 使い方

1. このファイルの「投入プロンプト」を Claude Design に渡す。
2. Claude Design の出力は `docs/claude-design-renderer-redesign-handoff-template.md` の構成で作らせる。
3. 返ってきた報告を `docs/claude-design-renderer-redesign-handoff.md` などの作業用ファイルに保存する。
4. その報告をもとに、実装側で `templates/`, `scripts/html_review_workbench/`, `tests/` の改修計画を立てる。

## 投入プロンプト

あなたは Claude Design として、Reviewable HTML Workbench の生成HTMLの描画デザインを改善するための設計案を作ってください。
今回は実装しません。実装者がそのまま改修計画へ分解できる、具体的で検証可能なデザイン報告を作ることが目的です。

### 対象リポジトリ

Reviewable HTML Workbench は、agent workflow 向けに reviewable な HTML bundle を生成する plugin です。
次の相対パスを中心に確認してください。

- `README.md`
- `AGENTS.md`
- `docs/design.html`
- `docs/development-plan.html`
- `skills/visual-html-renderer/SKILL.md`
- `schemas/document-model.schema.json`
- `scripts/html_review_workbench/render.py`
- `scripts/html_review_workbench/validate_bundle.py`
- `templates/report.html.j2`
- `templates/style.css`
- `templates/review-comments.js`
- `tests/test_renderer_bundle.py`
- `tests/fixtures/minimal_document_model.json`

### 現行仕様として必ず守ること

- 生成経路は `document-model.json` から `python3 -m scripts.html_review_workbench.cli render` で HTML bundle を作る。
- `scripts/html_review_workbench/render.py` は `templates/style.css` を生成先の `assets/style.css` へコピーする。見た目改善は生成済みHTMLだけでなく `templates/style.css` 側へ戻せる設計にする。
- 最終レンダリングで実用上使う block type は `html`, `callout`, `diagram`, `image` を中心にする。
- `section`, `text`, `table` は最終モデルでは原則使わない。表は `html` block 内の `<table>` として設計する。
- `html` block は raw insert される。外部入力をそのまま流し込む設計にしない。
- `callout` block は escape されるため、HTMLタグ前提の見た目設計にしない。
- review comment UI は `data-review-block`, `data-block-type`, `data-review-required`、`.review-comment-highlight`, `.review-comment-badge` を使う。レビュー対象の視認性を落とさない。
- Preview Runtime は `0.0.0.0` bind 禁止。外部アップロード型の図式レンダラーや外部送信は承認なしに使わない。
- 標準ライブラリ優先のプロジェクトなので、重いフロントエンドフレームワーク追加を前提にしない。追加が必要な場合は、理由、代替案、影響範囲を書く。

### デザイン改善の目的

現在の生成HTMLを、レビューしやすく、読みやすく、実装しやすい成果物へ改善してください。
優先する体験は次の通りです。

- 長い技術文書、設計文書、比較表、手順、ログ、図を読みやすい。
- レビューコメントが付いた箇所、返信済み、解決済みの状態が迷わず分かる。
- table-heavy な文書でも横にはみ出しにくく、比較軸を追いやすい。
- スキャンしやすい密度を保ち、業務文書として落ち着いた見た目にする。
- 生成HTMLが単なるMarkdown風の紙面ではなく、HTMLならではの情報設計になる。
- モバイル幅でも崩れず、デスクトップ幅では余白を無駄にしない。
- 実装者が `templates/style.css` と renderer / tests の変更へ自然に分解できる。

### 評価観点

少なくとも次の状態を想定して、現行デザインの課題と改善案を出してください。

- 通常の本文ブロック
- 大きな比較表
- 3階層程度のリスト
- コードブロックとログ
- callout
- diagram fallback
- generated image
- コメント未対応の review block
- コメントありの review block
- 返信済みの review block
- 解決済みの highlight / badge
- 狭い画面幅
- 印刷またはPDF化される可能性

### 成果物形式

出力は `docs/claude-design-renderer-redesign-handoff-template.md` の見出し構成に従ってください。
テンプレートの空欄を埋める形にし、見出し名はできるだけ変えないでください。

特に次を必ず含めてください。

- 現行UIの問題を、該当ファイル、CSS selector、renderer挙動に紐づけて書く。
- 改善後の情報設計を、header、document body、review block、table、callout、code、diagram/image、comment state ごとに書く。
- 色、余白、文字サイズ、border、状態表現を、CSS custom properties と selector 単位で提案する。
- `templates/style.css` だけでできる変更と、`templates/report.html.j2` / `render.py` / `review-comments.js` の変更が必要なものを分ける。
- test に落とすべき acceptance criteria を書く。特に `tests/test_renderer_bundle.py` に足すべき CSS / HTML assertion を具体化する。
- 実装順序を、リスクの低い順に 3から6段階で提案する。
- やらないこと、後回しにすること、判断が必要な未決事項を書く。

### 出力ルール

- 抽象的な美観の話だけで終わらせない。必ず実装対象ファイルと selector / HTML構造へ接続する。
- 既存の review comment 機能を壊す提案はしない。壊れる可能性がある場合はリスクと保護用の検証を明記する。
- 一色だけで構成された単調な配色や、装飾過多の landing page 風デザインにしない。
- UI説明文を本文内に増やす方向で解決しない。見た目と構造で読み取れるようにする。
- 外部サービス、CDN、Web font、画像ホスティングに依存しない。
- 変更案に絶対パスを書かない。リポジトリ相対パスだけを使う。
- 不明点は推測で埋めず、最後の「未決事項」に分離する。

### 最終出力

最終出力は報告本文だけにしてください。
実装用の差分やコマンド実行は行わないでください。
ファイルに書ける環境なら `docs/claude-design-renderer-redesign-handoff.md` に保存してください。
ファイルに書けない場合は、同じ内容をそのままチャットに出してください。
