# Reviewable HTML Workbench — 開発ハンドオフ仕様書

## 概要

エージェントが生成した技術文書（設計書・調査レポート・比較表・手順書・ログ・図）を、人間がレビュー・コメントする業務文書ビューア。

静的 HTML / CSS / 少量の vanilla JS で動作。外部 CDN・Web フォント・画像ホスティングに依存しない。

---

## ファイル構成

```
design_handoff/
├── README.md              ← 本ファイル（実装仕様書）
├── Reviewable Workbench.html  ← メインHTML（分割ソース版）
├── workbench.css          ← 全スタイル定義
├── workbench.js           ← インタラクション（vanilla JS）
└── standalone.html        ← 自己完結版（オフライン確認用）
```

---

## 1. カラートークン

### サーフェス / インク（warm neutral）

| トークン       | Light         | Dark          | 用途               |
|---------------|---------------|---------------|--------------------|
| `--bg-app`    | `#efece5`     | `#131519`     | アプリ背景          |
| `--bg-rail`   | `#f4f2ec`     | `#171a1f`     | サイドレール背景     |
| `--paper`     | `#fdfcf9`     | `#1c1f24`     | 用紙面（白カード）   |
| `--paper-2`   | `#f7f5f0`     | `#20242a`     | メタ・ヘッダ地       |
| `--ink`       | `#232019`     | `#e7e3da`     | 主テキスト          |
| `--ink-2`     | `#5f5b51`     | `#a6a299`     | 副テキスト          |
| `--ink-3`     | `#8d887d`     | `#7d7a72`     | 補助テキスト        |
| `--ink-faint` | `#b3aea3`     | `#5b5851`     | 最淡テキスト        |
| `--line-1`    | `#e6e2d8`     | `#2c2f35`     | 淡い罫線           |
| `--line-2`    | `#d6d1c5`     | `#393d44`     | 標準罫線           |
| `--line-3`    | `#c4bdae`     | `#4a4e56`     | 濃い罫線           |

### 構造アクセント

| トークン         | Light       | Dark        |
|-----------------|-------------|-------------|
| `--brand`       | `#2f6093`   | `#6ea4dc`   |
| `--brand-soft`  | `#e8eff7`   | `#1f2d3c`   |

### レビュー状態色（3色相で識別）

| 状態     | メイン色     | 背景色        | 罫線色        |
|---------|-------------|--------------|--------------|
| 未対応   | `--open`    | `--open-bg`  | `--open-line` |
|         | `#2f6fb0`   | `#e9f1f9`    | `#bcd6ee`     |
| 返信あり | `--reply`   | `--reply-bg` | `--reply-line`|
|         | `#a9772a`   | `#f7efdc`    | `#e6cf9b`     |
| 解決済み | `--resolved`| `--resolved-bg`| `--resolved-line`|
|         | `#3f8a5c`   | `#e9f1ea`    | `#bcd9c5`     |

### コードサーフェス（ライトモードでも濃紺）

| トークン         | 値          |
|-----------------|-------------|
| `--code-bg`     | `#1d2127`   |
| `--code-bg-2`   | `#23282f`   |
| `--code-ink`    | `#d7d3c8`   |
| `--code-ink-2`  | `#8b9099`   |
| `--code-blue`   | `#82b4e6`   |
| `--code-green`  | `#8fce9b`   |
| `--code-amber`  | `#e6c074`   |
| `--code-pink`   | `#e08fa8`   |

---

## 2. タイポグラフィ・スケール

フォントは**システムフォントのみ**。明朝体・Web フォント不使用。

```css
--font-sans:  -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
              "Hiragino Kaku Gothic ProN", "Yu Gothic", "Yu Gothic UI", Meiryo, sans-serif;
--font-serif: /* sans と同一（明朝体不使用）*/
--font-mono:  ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace;
```

| レベル   | サイズ  | ウェイト | 行間   | 用途                  |
|---------|--------|---------|-------|----------------------|
| H1      | 30px   | 700     | 1.18  | 文書タイトル            |
| H2      | 21px   | 700     | 1.25  | セクション見出し         |
| H3      | 16px   | 650     | —     | サブ見出し              |
| H4      | 15px   | 650     | —     | サブサブ見出し（ink-2色）|
| Body    | 15px   | 400     | 1.72  | 本文                   |
| Lead    | 17px   | 400     | 1.55  | リード・デッキ           |
| Small   | 13px   | 400     | —     | 補助テキスト・コメント本文|
| Caption | 12px   | 600+    | —     | ラベル・メタデータ       |
| Mono    | 12-13px| 500     | —     | コード・数値・日時       |

compact 密度では `--fs-body` が 14px に縮小。

---

## 3. スペーシング・スケール

```
--sp-1:  4px
--sp-2:  8px
--sp-3: 12px
--sp-4: 16px
--sp-5: 24px
--sp-6: 32px
--sp-7: 48px
--sp-8: 64px
```

密度トークン（`[data-density]` で切替）:

| トークン       | comfortable | compact |
|---------------|-------------|---------|
| `--line`      | 1.72        | 1.55    |
| `--block-gap` | 22px        | 15px    |
| `--pad-card`  | 18px        | 13px    |
| `--row-pad`   | 11px 14px   | 7px 12px|

---

## 4. ボーダー / シャドウ方針

### 角丸

| 用途                    | トークン    | 値     |
|------------------------|-----------|--------|
| インラインタグ / pip     | `--r-xs`  | 2px    |
| ボタン / 入力 / セル     | `--r-sm`  | 4px    |
| カード / コメント / 表   | `--r-md`  | 6px    |
| 用紙面 / コンテナ        | `--r-lg`  | 8px    |
| ピル / バッジ            | `--r-pill`| 999px  |

### シャドウ

| トークン   | 用途                      |
|-----------|--------------------------|
| `--sh-1`  | カード・用紙面の最小限の影    |
| `--sh-2`  | FAB・軽い浮き             |
| `--sh-3`  | ポップオーバー・選択中（唯一の強い影）|

**原則**: 境界は罫線で作り、影は階層を示すときだけ使う。派手なドロップシャドウ・大きな角丸・グラデーションの多用は避ける。

---

## 5. レビューブロックの状態別デザイン

### 本文ハイライト（`.cx[data-state]`）

| 状態       | 背景          | 下線             | その他            |
|-----------|--------------|-----------------|------------------|
| `open`    | `--open-bg`  | 2px solid 青     | cx-num バッジ表示  |
| `reply`   | `--reply-bg` | 2px solid 琥珀   | cx-num バッジ表示  |
| `resolved`| transparent  | 1px dashed 緑罫線 | cx-num バッジ表示  |

### コメントカード（`.cmt[data-cstate]`）

| 状態       | 左ボーダー      | 不透明度 | 特記                    |
|-----------|----------------|---------|------------------------|
| `open`    | 3px `--open`   | 1.0     | 返信入力 + 解決ボタン表示 |
| `reply`   | 3px `--reply`  | 1.0     | スレッド表示             |
| `resolved`| 3px `--resolved`| 0.78   | 解決者バナー表示          |

### 状態バッジ（`.cmt-state`）

各状態色の `bg` 地に `color` のテキスト。6px ドット + ラベル。pill 型。

### 視覚ヒエラルキー

- **未対応** = 主張（塗り＋実線）
- **返信あり** = 進行中（塗り＋実線、別色相）
- **解決済み** = 後退（塗りなし＋破線、低不透明度）

文言の追加に頼らず、**色相 + 塗りの有無 + 不透明度**で状態差を表現する。

---

## 6. ブロック別デザイン仕様

### 大きな比較表

- 先頭列（比較軸）と見出し行を `position: sticky` で固定
- 推奨列は緑の淡い塗りで縦に追える（`col.pick`）
- 評価は 5 段階 pip（6px 丸）: good=緑 / mid=琥珀 / low=赤
- コストは `font-variant-numeric: tabular-nums` で桁揃え
- `min-width: 720px` + 横スクロール

### Callout

- 26px アイコン枠 + 本文の 2 カラム grid
- info=青 / warn=琥珀 / success=緑
- 左 3px ボーダー + 淡い地色。角丸 6px

### Code / Log ブロック

- ライトモードでも濃紺サーフェス
- 行番号 + 最小限のシンタックスカラー
- Log: INFO=青 / OK=緑 / WARN=琥珀 / ERROR=ピンク
- WARN/ERROR 行に薄い地色

### Diagram Fallback

- 破線枠 + `DIAGRAM FALLBACK` バッジで失敗を明示
- box/arrow の簡易フローを CSS flex で表示
- 原本定義（mermaid 等）をモノスペースで併記

### Generated Image

- 斜めストライプのプレースホルダ
- mono ラベルで寸法・ファイル名を表記
- 差し替え前提を明示

---

## 7. レイアウト / レスポンシブ

### デスクトップ 3 カラム

```
≥1180px: 232px(目次) | 1fr(用紙) | 332px(コメント)
```

- 用紙面: 白カード、`border-radius: 8px`、`box-shadow: --sh-1`
- 本文の可読幅: `max-width: 72ch`（最大化モードでは解除）
- 表・コード・図は用紙幅いっぱいに breakout

### タブレット

```
901–1180px: 目次を隠し 1fr(用紙) | 320px(コメント)
```

### モバイル

```
≤900px: 1 カラム。コメントレールを非表示。
```

- インラインスレッド（該当ブロック直下の折りたたみ）に切替
- 表は横スクロール継続（先頭列 sticky）

---

## 8. モード切替

### 最大化モード（Focus）

- 目次・コメントレールを非表示
- `doc-shell` を `max-width: 1480px` に拡張
- 本文 `max-width` を解除（`none`）
- レビューハイライトを非表示（背景透明・下線なし・cx-num 非表示）
- トグルボタン: `#focusToggle[aria-pressed]`
- CSS class: `.canvas.is-focus`

### 公開プレビュー（Published）

- トップバーを非表示
- 目次・コメントレールを非表示
- すべてのレビュー要素を非表示（ハイライト・バッジ・状態表示・byline）
- `doc-shell` を `max-width: 1180px`（標準）/ `1480px`（最大化）
- フローティングバー（`.pub-exit`）で標準/最大化切替・書き出し・戻る操作
- CSS class: `body.is-published`
- 公開内「最大化」: `.is-published .canvas.is-focus`

### ダークモード

- `html[data-theme="dark"]` で全トークンを差し替え
- コードブロックは Light/Dark で共通の濃紺サーフェス

### レビューフィルタ

- `all`: すべて表示
- `hide-resolved`: 解決済みカード・ハイライトを非表示
- `only-open`: 未対応のみ表示
- CSS class: `.canvas.hide-resolved` / `.canvas.only-open`

---

## 9. 自動章番号

`.prose.autonum` クラスで CSS カウンタによる自動採番:

```css
h2 → "1." "2." "3." …
h3 → "1.1" "1.2" "2.1" …
h4 → "1.1.1" "1.1.2" "2.1.1" …
```

- h2 は `counter-reset: h3 0 h4 0`
- h3 は `counter-reset: h4 0`
- `::before` 擬似要素でモノスペース表示
- h2 番号: `--ink-faint` 色 / h3 番号: `--brand` 色 / h4 番号: `--ink-3` 色

---

## 10. インタラクション（JS）

### コメントカード配置（Docs 方式）

- 各カードを対応するハイライトの `offsetTop` に `position: absolute` で整列
- 衝突時は下方向にスタック（`cursor` 変数で管理）
- スクロール・リサイズ時に `requestAnimationFrame` で再計算

### ハイライト ↔ カード連動

- ハイライトクリック → 対応カードに `.is-active`、スクロール
- カードクリック → 対応ハイライトに `.is-active`
- active 状態: カードに `box-shadow: --sh-3` + 左にずれ、ハイライトに `box-shadow` リング

### 状態変更

- 「解決」ボタン → `state` を `resolved` に変更、カード再描画
- 「再オープン」ボタン → `state` を `open` に戻す
- 「送信」ボタン → スレッドに返信追加、`open` → `reply` に遷移

### 公開用 HTML 書き出し

- `buildPublishedDoc()` でクローン → レビュー要素除去 → CSS インライン化
- Blob URL でダウンロード（`.html` ファイル）

---

## 11. 実装上の注意

1. **テーマ・密度はルート属性で切替**: `<html data-theme="light|dark" data-density="comfortable|compact">`
2. **レビュー状態は data 属性**: `.cx[data-state="open|reply|resolved"]` / `.cmt[data-cstate="open|reply|resolved"]`
3. **フォーカスリング**: `--focus-ring` で統一（`box-shadow` ベース）
4. **数値は等幅**: `font-variant-numeric: tabular-nums` + `--font-mono`
5. **アクセシビリティ**: `role="tablist"` / `aria-selected` / `aria-pressed` / `aria-label` を使用
6. **キーボード**: 目次リンク + Tab 移動。Escape で公開プレビュー解除
