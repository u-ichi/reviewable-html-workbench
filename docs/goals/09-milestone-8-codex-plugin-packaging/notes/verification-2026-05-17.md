# Verification: backlog 09 Codex Plugin Packaging

## Commands

- `python3 -m json.tool .codex-plugin/plugin.json >/dev/null`: passed
- `python3 -m json.tool .agents/plugins/marketplace.json >/dev/null`: passed
- `python3 -m json.tool .claude-plugin/plugin.json >/dev/null`: passed
- `python3 -m unittest tests.test_project_layout`: passed, 6 tests
- `python3 -m unittest discover -s tests`: passed, 30 tests
- `CODEX_HOME=/private/tmp/codex-plugin-home.qGJhjx codex plugin marketplace add /private/tmp/rhw-marketplace-qGJhjx`: passed
- `codex exec --sandbox read-only ...`: after marketplace registration and plugin enabled config, both skills returned `no` with the old `AVAILABLE` + `source.path: "."` marketplace shape
- `python3 -m json.tool .agents/plugins/marketplace.json >/dev/null`: passed after switching to `INSTALLED_BY_DEFAULT` + `./plugins/reviewable-html-workbench`
- `python3 -m unittest discover -s tests`: passed, 30 tests after marketplace shape change
- `codex exec --sandbox read-only ... browser/google-calendar`: passed as a control; existing plugin skills returned `yes`
- `codex exec --sandbox read-only ... visual-html-renderer/reviewable-design-doc`: passed after materializing `~/.codex/skills` symlinks; both returned `yes`
- `codex exec --sandbox read-only ... 図示つきHTMLレポート`: returned `reviewable-html-workbench:visual-html-renderer`
- `codex exec --sandbox read-only ... レビュー可能な設計資料をHTMLで`: returned `reviewable-html-workbench:reviewable-design-doc`

## Notes

- Direct marketplace add with the Google Drive path failed with `--ref is only supported for git marketplace sources`.
- The same repo registered successfully when passed through a path without spaces via `/private/tmp/rhw-marketplace-qGJhjx`.
- User environment registration was added to `~/.codex/config.toml`, but the old marketplace entry did not produce plugin cache or skill discovery.
- The marketplace entry now follows the known installed plugin pattern: `INSTALLED_BY_DEFAULT` and `source.path: "./plugins/reviewable-html-workbench"`.
- Codex CLI v0.130.0 local marketplace registration still did not materialize the plugin skills automatically, so `~/.codex/skills/visual-html-renderer` and `~/.codex/skills/reviewable-design-doc` were symlinked to this plugin repo.
- New Codex processes now expose both skills and resolve trigger prompts with `reviewable-html-workbench:` namespace.
