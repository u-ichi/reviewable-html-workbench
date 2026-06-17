# Codex plugin packaging

## 管理方針

`reviewable-html-workbench` は Codex plugin repo を管理元にする。base repo の `home/skills` / `home/generated/codex-skills` には同名 skill を置かず、必要になった場合だけ薄い adapter skill を追加する。

この repo は plugin root と marketplace root を兼ねる。Codex marketplace loader の既存パターンに合わせるため、`plugins/reviewable-html-workbench` は repo root への symlink として置く。`codex plugin marketplace add <repo>` で `.agents/plugins/marketplace.json` が読まれ、`reviewable-html-workbench` plugin は `source.path: "./plugins/reviewable-html-workbench"` から読み込まれる。

## ローカル登録手順

```bash
codex plugin marketplace add /path/to/reviewable-html-workbench
```

repo path に空白が含まれる環境で `--ref is only supported for git marketplace sources` が出る場合は、空白を含まない symlink を経由する。

```bash
ln -s "/path/with spaces/reviewable-html-workbench" /private/tmp/reviewable-html-workbench
codex plugin marketplace add /private/tmp/reviewable-html-workbench
```

登録後は Codex CLI / UI を再起動し、次の2つの skill が plugin 由来として候補に出ることを確認する。

- `visual-html-renderer`
- `reviewable-design-doc`

この操作は `~/.codex` 側の marketplace 設定と plugin cache を更新する。作業 agent が実行する場合は、ユーザー承認を取ってから実行する。
`~/.codex/skills` 直下へ手動 symlink を作らない。plugin skill は `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/skills/` の copy された実体を読み込み元にする。
古い `~/.codex/skills/visual-html-renderer` / `~/.codex/skills/reviewable-design-doc` symlink が残っている場合は、plugin cache 更新後に撤去して重複読み込みを避ける。

検証済みの発火名は次の通り。

- `reviewable-html-workbench:visual-html-renderer`
- `reviewable-html-workbench:reviewable-design-doc`

## 更新手順

plugin repo を更新したら、次の順で確認する。

```bash
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m unittest discover -s tests
codex plugin marketplace upgrade reviewable-html-workbench-local
```

`upgrade` は登録済み marketplace cache を更新する操作なので、作業 agent が実行する場合はユーザー承認を取る。

## dev mode

ローカル開発中に package cache へ毎回 copy し直さず、現在の checkout を plugin 読み込み元にしたい場合は
`bin/plugin-dev-switch.sh` を使う。

```bash
# Claude / Codex のインストール済み cache をまとめて確認
bin/plugin-dev-switch.sh status

# Claude / Codex のインストール済み cache をまとめて dev に切り替える
bin/plugin-dev-switch.sh dev

# Claude / Codex のインストール済み cache をまとめて package copy に戻す
bin/plugin-dev-switch.sh package
```

`dev` は Claude 側の `~/.claude/plugins/cache/...` をこの repo への symlink に差し替える。
Codex 側は先に `codex plugin add reviewable-html-workbench@reviewable-html-workbench-local --json` で
installed state を作り、その後
`~/.codex/plugins/cache/reviewable-html-workbench-local/reviewable-html-workbench/<version>` は
実ディレクトリのまま保持し、その中の `.codex-plugin`、`skills`、`scripts`、`templates` などを
この repo への symlink に差し替える。Codex は version ディレクトリ自体が symlink だと
installed 判定から外すため、この形にする。これにより、version bump や marketplace upgrade を待たずに
次の agent セッションの skill discovery が checkout 上の `skills/` と manifest を読む。
既存セッションに読み込み済みの skill 一覧は動的更新されないため、切り替え後は新しいセッションで確認する。

## base repo との境界

- plugin repo: skill本文、`agents/openai.yaml`、HTML生成/preview/review取り込み script、fixture test を管理する。
- base repo: 全プロジェクト共通の agent rule / hook / install 管理を続ける。
- adapter が必要な場合: base repo 側には plugin skill を案内する薄い skill だけを置き、処理本体や同名 skill を重複させない。
- 現時点では base repo の `home/skills` / `home/generated/codex-skills`、および live `~/.agents/skills` / `~/.codex/skills` に `visual-html-renderer` と `reviewable-design-doc` の同名 skill は置かない。
- `bin/build-codex-skills.sh` は base repo の `home/skills` から `home/generated/codex-skills` を生成する経路なので、この plugin repo をその配下へコピーしない限り生成物とは衝突しない。
- marketplace policy は `INSTALLED_BY_DEFAULT` にする。`AVAILABLE` だけでは `codex plugin marketplace add` 後に `~/.codex/plugins/cache` へ plugin 実体が作られず、skill discovery に載らない。
- plugin skill は marketplace cache の copy 配置で扱う。`~/.codex/skills` の手動 symlink は使わない。

## release / versioning

- `.codex-plugin/plugin.json` の `version` は semantic versioning とする。
- patch: docs、テスト、後方互換の小修正。
- minor: skill workflow や CLI option の後方互換追加。
- major: document model、comment schema、CLI subcommand contract の非互換変更。
- release tag は `v<version>` とし、tag 前に `python3 -m unittest discover -s tests` と manifest JSON validation を通す。
