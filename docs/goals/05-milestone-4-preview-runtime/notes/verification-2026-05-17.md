# Verification Receipt: Preview Runtime

## 実装結果

- `scripts/html_review_workbench/preview_server.py` に preview runtime を実装。
- `scripts/html_review_workbench/cli.py` の `preview` subcommand を実装へ接続。
- `tests/test_preview_server.py` を追加。
- `docs/design.html` と `docs/development-plan.html` を Preview Runtime 契約に同期。

## 検証結果

- `python3 -m unittest discover -s tests`: 17 tests passed.
- `python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`: `output/tmp/test-render/index.html` generated.
- `python3 -m scripts.html_review_workbench.cli preview --root output/tmp/test-render --mode auto`: `127.0.0.1` fallback, URL, PID, manifest, stop command returned.
- `python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`: `{"ok": true, "errors": [], "review_blocks": 1}`.
- `rg -n "Preview Runtime|html-preview-sessions|0.0.0.0|stop_command|URLとPID" docs/design.html docs/development-plan.html`: matched expected docs updates.

## Runtime Cleanup

- Preview process `40520` was stopped after verification.

## 状態

- implementation / verification complete.
- backlog close / commit gate / Session complete gate remains.
