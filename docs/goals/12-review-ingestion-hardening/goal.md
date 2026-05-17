# Goal: Review Ingestionの最小縦通し後に、UI検証・JS分割・状態設計・document model反映を安全に強化する

## Backlog

- id: 12
- file: `docs/backlog/12-review-ingestion-hardening.md`
- notion:

## Objective

Review Ingestionの最小縦通し後に、UI検証・JS分割・状態設計・document model反映を安全に強化する。

## Scope

- DOM単位検証方針
- review-comments.js分割
- status/classification整理
- document model反映強化
- 実出力評価への引き継ぎ

## Stop Conditions

- 07の最小縦通しが完了していない時
- Playwright等の新規依存導入判断が必要になった時
- document model反映の仕様判断が必要になった時

## Verification

- `python3 -m unittest discover -s tests`

## Completion Gate

- `Goal done`: implementation / verification が完了し、backlog close / Session complete gate が完了または承認待ちとして明示されている
- `Backlog done`: backlog file と Notion が完了状態に更新されている
- `Session complete`: `Goal done` と `Backlog done` の両方を満たす
- `Backlog close wait`: implementation / verification は完了したが `/backlog done --from-goal` が未実行
- `Approval wait`: commit / push / Notion 更新などの承認ゲートで停止している
