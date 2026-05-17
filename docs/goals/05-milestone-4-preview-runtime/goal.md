# Goal: Codexから利用できるPreview Runtimeを実装し、Tailscale/localhost URLを安全に提示する

## Backlog

- id: 05
- file: `docs/backlog/05-milestone-4-preview-runtime.md`
- notion:

## Objective

Codexから利用できるPreview Runtimeを実装し、Tailscale/localhost URLを安全に提示する。

## Scope

- `preview_server.py` 実装
- Tailscale fallback
- `0.0.0.0` 拒否
- session manifest
- 設計/計画HTML更新

## Stop Conditions

- preview URL提示とmanifest作成が検証できた時
- network bind方針に追加判断が必要になった時

## Verification

- `python3 -m unittest discover -s tests`
- `python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`
- `python3 -m scripts.html_review_workbench.cli preview --root output/tmp/test-render --mode auto`
- `python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`

## Completion Gate

- `Goal done`: implementation / verification が完了し、backlog close / Session complete gate が完了または承認待ちとして明示されている
- `Backlog done`: backlog file と Notion が完了状態に更新されている
- `Session complete`: `Goal done` と `Backlog done` の両方を満たす
- `Backlog close wait`: implementation / verification は完了したが `/backlog done --from-goal` が未実行
- `Approval wait`: commit / push / Notion 更新などの承認ゲートで停止している
