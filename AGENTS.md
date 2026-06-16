# reviewable-html-workbench

## 概要

HTMLを最終成果物にするagent workflow向けの共通plugin。図示つきHTML生成、Preview Runtime、HTML上のレビューコメント、コメント取り込み、agent返信、設計反映を扱う。

Claude Code / Codex CLI の両方で使えるように、plugin manifest は agent 別に持ち、skill本文とscript実装は共通化する。

## 技術スタック

- Python 3.11+
- 標準ライブラリ優先
- HTML / CSS / JavaScript
- Claude Code plugin (`.claude-plugin/plugin.json`)
- Codex plugin (`.codex-plugin/plugin.json`)
- Agent Skills (`skills/*/SKILL.md`)

## 開発コマンド（自動テスト・構造検証）

以下は自動化された構造検証であり、機能の「動作確認」ではない。

```bash
# 自動テスト（コード正当性の検証）
python3 -m unittest discover -s tests

# Claude plugin manifest 検証
claude plugins validate .

# JSON syntax 検証
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null

# CLI skeleton 確認
python3 -m scripts.html_review_workbench.cli --help
```

## 動作確認（実シナリオ検証）

このシステムの利用者は agent であり、Python CLI を直接叩く人間はいない。CLI は agent のツールである。「動作確認」とは CLI の入出力が正しい JSON を返すことではなく、agent がユーザーのワークフロー内で機能を正しく使えることを意味する。

自動テスト pass は動作確認の前提条件であり、動作確認そのものではない。

実シナリオ検証の手順は各 skill の SKILL.md「実シナリオ検証」セクションに記載。

## ディレクトリ構成

- `.claude-plugin/` Claude Code plugin manifest
- `.codex-plugin/` Codex plugin manifest
- `skills/visual-html-renderer/` HTML生成・図示・Preview Runtime用skill
- `skills/reviewable-design-doc/` レビュー可能な設計資料・コメント取り込み用skill
- `scripts/html_review_workbench/` 両skillから呼ぶ共通実装
- `templates/` HTML/CSS/JSテンプレート
- `tests/` scriptとplugin構成の検証
- `docs/` 設計・開発フロー

## プロジェクト固有の規約

- `SKILL.md` は薄く保ち、重い処理は `scripts/html_review_workbench/` に置く。
- Claude / Codex 差分は manifest と必要最小限のadapterに閉じ込める。
- コメントの確認質問はチャットだけで返さず、HTMLのコメントスレッドへ agent reply として書き戻す。
- Preview Runtime は Tailscale IPv4 を優先し、fallback は `127.0.0.1`。`0.0.0.0` bindは禁止。
- 外部アップロード型の図式レンダラーは承認なしに使わない。
- git commit 時は必ず `.claude-plugin/plugin.json` と `.codex-plugin/plugin.json` の
  `version` フィールドを semver に従って更新する。バージョン更新なしの commit は禁止。

  | 変更種別 | bump | 例 |
  |----------|------|----|
  | バグ修正・表示改善・リファクタ・ドキュメント修正 | patch (0.2.0 → 0.2.1) | CSS 修正、テスト追加 |
  | 新機能・新 skill 追加・既存機能の拡張 | minor (0.2.0 → 0.3.0) | 新しい skill、テンプレート追加 |
  | 破壊的変更・既存 skill の入出力仕様変更 | major (0.2.0 → 1.0.0) | skill の引数変更、既存テンプレート構造の破壊 |

  迷ったら patch 側に倒す。
