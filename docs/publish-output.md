# publish コマンド出力仕様

## 概要

`publish` コマンドは、render 済み HTML バンドルからレビュー UI を除去した
**公開用 standalone HTML** を生成する。

出力は単一の `index.html` ファイル。外部アセット（CSS・画像・JS）への参照を持たず、
ファイル単体で完結する。publicar 等の配信サービスや、メール添付、ローカル閲覧に
そのまま使える。

## CLI

```bash
python3 -m scripts.html_review_workbench.cli publish \
  --root <rendered-bundle-dir> \
  --output <publish-output-dir>
```

- `--root`: render 済みバンドルのディレクトリ（`index.html` と `assets/style.css` を含む）
- `--output`: 出力先ディレクトリ（省略時は `<root>/../<root-name>-published/`）

出力 JSON: `{"status": "ok", "output": "<出力ファイルパス>"}`
エラー時: `{"status": "failed", "error": "<エラーメッセージ>"}`

## 入力要件

render 済みバンドルに以下が必要:

| ファイル | 必須 | 用途 |
|---------|------|------|
| `index.html` | 必須 | renderer が生成した HTML。`<article class="doc-main">` を含む |
| `assets/style.css` | 必須 | CSS。インライン化して出力に埋め込む |
| `assets/*.png` 等 | 任意 | 画像。base64 data URI に変換して埋め込む |

## 出力 HTML の構造

```html
<!DOCTYPE html>
<html lang="ja" data-density="compact">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>文書タイトル</title>
  <!-- OG / Twitter メタタグ -->
  <meta property="og:title" content="文書タイトル">
  <meta property="og:description" content="本文冒頭 200 文字">
  <meta property="og:type" content="article">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="文書タイトル">
  <meta name="twitter:description" content="本文冒頭 200 文字">
  <style>
    /* style.css の全内容 */
    /* published export overrides */
    html,body{background:var(--bg-app);}
    .canvas{overflow:visible;height:auto;min-height:100vh;}
    /* ダークモード override */
    @media(prefers-color-scheme:dark){:root{--bg-app:#131519;...}}
  </style>
</head>
<body class="is-published">
  <main class="canvas">
    <div class="doc-shell">
      <div class="doc-grid">
        <article class="doc-main">
          <!-- 本文コンテンツ（レビュー要素除去済み） -->
        </article>
      </div>
    </div>
  </main>
</body>
</html>
```

## 入力から保持するもの

| 属性 | 保持方法 |
|------|---------|
| `lang` | `<html>` 要素の `lang` 属性をそのまま保持 |
| `data-density` | `<html>` 要素の `data-density` 属性をそのまま保持 |
| focus 状態 | 入力の `<main class="canvas is-focus">` があれば `is-focus` クラスを保持 |
| `<h1 class="doc-title">` | 文書タイトルとして `<title>` と OG/Twitter メタタグに反映 |
| 本文コンテンツ | `<article class="doc-main">` 内の全コンテンツ（下記の除去対象を除く） |

## 除去するもの

### data 属性

レビュー用の data 属性を全て除去:

| 属性 | 用途（入力側） |
|------|--------------|
| `data-review-block` | ブロック識別子 |
| `data-review-required` | レビュー必須フラグ |
| `data-block-type` | ブロック種別 |

### DOM 要素

| 要素 | 用途（入力側） |
|------|--------------|
| `<div class="byline">` | 作成者・エージェント名 |
| `<span class="doc-status ...">` | 文書ステータス（Draft 等） |

### 入力 HTML から取り込まない要素

以下は `<article class="doc-main">` の外にあるため、出力に含まれない:

| 要素 | 用途（入力側） |
|------|--------------|
| `<header class="topbar">` | ツールバー（フィルタ・テーマ切替等） |
| `<nav class="toc">` | 目次 |
| `<aside class="cmt-rail">` | コメントレール |
| `<div class="pub-exit">` | 公開プレビューモード操作バー |
| `<script src="...">` | review-comments.js |

## CSS の処理

1. `assets/style.css` の全内容を `<style>` タグとしてインライン化
2. published export override を追加（背景色・canvas overflow・最小高さ）
3. `@media(prefers-color-scheme:dark)` でダークモード CSS 変数を追加

ダークモードは OS の設定（`prefers-color-scheme`）に自動追従する。
`data-theme` 属性によるテーマ切替（入力側の機能）は出力に含まれない。

## 画像の処理

`<img src="...">` の画像ファイルを読み取り、base64 data URI に変換して埋め込む。

- 対象: `<article>` 内の `<img>` タグ
- MIME タイプ: ファイル拡張子から自動判定
- 既に `data:` URI の画像はスキップ
- ファイルが存在しない場合は元の `src` を維持

## メタタグの生成

| タグ | 値の取得元 |
|------|-----------|
| `<title>` | `<h1 class="doc-title">` のテキスト内容 |
| `og:title` / `twitter:title` | 同上 |
| `og:description` / `twitter:description` | 本文先頭の `<p>` から最大 200 文字 |
| `og:type` | 固定値 `article` |
| `twitter:card` | 固定値 `summary` |

## 外部依存

なし。Python 標準ライブラリ（`re`, `base64`, `mimetypes`, `html`, `pathlib`）のみ使用。

## 制約

- renderer が出力する既知の HTML 構造に依存する。手動で作成した HTML は対象外
- `<article class="doc-main">` が存在しない場合はエラー
- JS による動的コンテンツ（コメントスレッドの展開等）は静的な HTML としてのみ出力される
- `review-comments.js` の `buildPublishedDoc()` とは独立した実装。除去対象の差異が生じた場合は本モジュール側を更新する
