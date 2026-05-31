# plugin開発フロー

## 基本方針

このrepoは、Claude Code plugin と Codex plugin の両方に対応する。agent別の差分はmanifestと必要最小限のadapterに閉じ込め、skill本文とPython scriptを共通化する。

## 開発の進め方

1. **契約を決める**
   - 文書モデルschema
   - comments.json schema
   - preview session manifest schema
   - script CLIの入出力

2. **scriptを先に作る**
   - `render`
   - `preview`
   - `validate`
   - `ingest-review`
   - skill本文にロジックを厚く書かず、scriptを呼ぶ。

3. **fixtureでテストする**
   - 最小の文書モデルから `index.html` が出る
   - Tailscaleなしなら `127.0.0.1` にfallbackする
   - `0.0.0.0` bindを拒否する
   - 確認が必要なコメントにはagent replyが追記される

4. **skillを薄く接続する**
   - `visual-html-renderer` はHTML生成とpreview URL提示まで
   - `reviewable-design-doc` は設計構造化とレビュー取り込みまで

5. **pluginとして検証する**
   - Claude: `claude plugins validate .`
   - Codex: `.codex-plugin/plugin.json` と `skills/*/SKILL.md` の構造検証
   - Codex marketplace: `python3 -m json.tool .agents/plugins/marketplace.json >/dev/null`
   - 共通: `python3 -m unittest discover -s tests`

6. **ローカル導入して実使用する**
   - Claude: `claude --plugin-dir /path/to/reviewable-html-workbench`
   - Codex: `codex plugin marketplace add /path/to/reviewable-html-workbench` で repo-local marketplace を登録する。path に空白があり失敗する場合は、空白を含まない symlink 経由で登録する。

7. **実出力を見て直す**
   - HTML表示
   - range selection comment
   - comments.json取り込み
   - agent reply
   - 再生成後のpreview URL

## 最初のMVP

MVPでは以下だけを完了条件にする。

- 最小文書モデルからHTMLを出せる
- preview URLを提示できる
- comments.jsonを読める
- 確認が必要なコメントにagent replyを書ける
- Claude / Codex 両方のplugin manifestがvalidateできる
