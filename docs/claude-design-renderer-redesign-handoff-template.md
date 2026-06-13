# Claude Design 引き渡しテンプレート: Reviewable HTML Workbench 描画改善

このテンプレートは、Claude Design が描画改善案を返す時の報告形式です。
実装者はこの内容をもとに、改修計画、backlog、test 追加、実装順序を作ります。

## 1. 状態

- Tool status:
- Task status:
- 確認した範囲:
- 確認できなかった範囲:
- 実装は行ったか: いいえ

## 2. 入力要約

- 対象:
- 主な利用者:
- 主な利用シーン:
- 重要な制約:
- 既存の描画経路:

## 3. 現行UIの診断

| 領域 | 現行の問題 | 根拠ファイル / selector | 影響 | 優先度 |
|---|---|---|---|---|
| header |  |  |  |  |
| document body |  |  |  |  |
| review block |  |  |  |  |
| table |  |  |  |  |
| callout |  |  |  |  |
| code / log |  |  |  |  |
| diagram / image |  |  |  |  |
| comment state |  |  |  |  |
| responsive |  |  |  |  |
| print / PDF |  |  |  |  |

## 4. 改善後のデザイン方針

### 4.1 目指す読後体験

- 

### 4.2 情報密度

- 

### 4.3 視線誘導

- 

### 4.4 レビュー状態の見せ方

- 

### 4.5 避けるデザイン

- 

## 5. 具体的なUI仕様

### 5.1 ページ全体

- 対象 selector:
- 変更内容:
- 理由:
- 実装メモ:

### 5.2 Header / metadata

- 対象 selector:
- 変更内容:
- 理由:
- 実装メモ:

### 5.3 Review block

- 対象 selector:
- 変更内容:
- 通常状態:
- コメントあり:
- 返信済み:
- 解決済み:
- 実装メモ:

### 5.4 Table

- 対象 selector:
- 変更内容:
- wide table:
- dense table:
- mobile:
- 実装メモ:

### 5.5 Callout

- 対象 selector:
- 変更内容:
- 種別を増やす必要:
- 実装メモ:

### 5.6 Code / log

- 対象 selector:
- 変更内容:
- 長い行:
- コピーや横スクロール:
- 実装メモ:

### 5.7 Diagram / generated image

- 対象 selector:
- 変更内容:
- fallback:
- image attached:
- 実装メモ:

### 5.8 Review comment UI

- 対象 selector:
- 変更内容:
- badge:
- highlight:
- resolved:
- keyboard / focus:
- 実装メモ:

### 5.9 Responsive

- breakpoint:
- mobile:
- tablet:
- desktop:
- wide desktop:

### 5.10 Print / PDF

- 対象 selector:
- 変更内容:
- page break:
- color fallback:

## 6. CSS token 案

| token | value | 用途 | 既存 token からの変更 |
|---|---|---|---|
| `--bg` |  |  |  |
| `--panel` |  |  |  |
| `--text` |  |  |  |
| `--muted` |  |  |  |
| `--line` |  |  |  |
| `--accent` |  |  |  |
| `--comment` |  |  |  |
| `--callout` |  |  |  |

追加 token:

| token | value | 用途 | 理由 |
|---|---|---|---|
|  |  |  |  |

## 7. 変更対象ファイル別の提案

| ファイル | 変更種別 | 具体変更 | 期待効果 | リスク | 検証 |
|---|---|---|---|---|---|
| `templates/style.css` |  |  |  |  |  |
| `templates/report.html.j2` |  |  |  |  |  |
| `templates/review-comments.js` |  |  |  |  |  |
| `scripts/html_review_workbench/render.py` |  |  |  |  |  |
| `tests/test_renderer_bundle.py` |  |  |  |  |  |
| `tests/fixtures/minimal_document_model.json` |  |  |  |  |  |

## 8. Renderer / schema 拡張が必要な項目

| 項目 | 必要性 | 変更対象 | 後方互換性 | 代替案 |
|---|---|---|---|---|
|  |  |  |  |  |

## 9. 実装順序案

1. 
2. 
3. 
4. 
5. 

各段階の完了条件:

| 段階 | 完了条件 | 検証 |
|---|---|---|
| 1 |  |  |
| 2 |  |  |
| 3 |  |  |
| 4 |  |  |
| 5 |  |  |

## 10. 受け入れ条件

- 

## 11. 検証計画

### 11.1 自動テスト

```bash
PYTHONPYCACHEPREFIX="$PWD/tmp/python-pycache" python3 -m unittest discover -s tests
```

追加すべき assertion:

- 

### 11.2 Renderer CLI

```bash
python3 -m scripts.html_review_workbench.cli check-model --model <document-model.json>
python3 -m scripts.html_review_workbench.cli render --model <document-model.json> --output <output-dir>
python3 -m scripts.html_review_workbench.cli validate --root <output-dir>
python3 -m scripts.html_review_workbench.cli preview --root <output-dir> --mode auto
```

確認観点:

- 

### 11.3 ブラウザ目視確認

| viewport | 確認項目 | 合格条件 |
|---|---|---|
| 375px |  |  |
| 768px |  |  |
| 1440px |  |  |
| wide desktop |  |  |

## 12. サンプル構造

必要なら、改善後の見た目を確認するための最小 `document-model.json` または `html` block 例を書く。

```json
{}
```

## 13. やらないこと

- 

## 14. 未決事項

| 論点 | なぜ未決か | 判断者 | 判断期限 |
|---|---|---|---|
|  |  |  |  |

## 15. 実装者への引き渡しメモ

- 最初に触るべきファイル:
- 先に追加すべき test:
- 壊しやすい機能:
- 実装後に必ず見る生成物:
- commit を分ける場合の候補:
