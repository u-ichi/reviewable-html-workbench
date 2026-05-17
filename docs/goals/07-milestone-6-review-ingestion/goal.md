# Goal: CodexがHTMLレビューコメントを読み込み、分類・agent reply書き戻し・処理状態保存をfixtureで検証できるようにする

## Backlog

- id: 07
- file: `docs/backlog/07-milestone-6-review-ingestion.md`
- notion:

## Objective

CodexがHTMLレビューコメントを読み込み、分類・agent reply書き戻し・処理状態保存をfixtureで検証できるようにする。

## Scope

- `ingest_review.py` 実装
- comment分類
- agent reply書き戻し
- review-cycle-state
- fixture検証

## Stop Conditions

- コメント取り込み、分類、agent reply追記、state保存がfixtureで検証できた時
- document model反映の判断にユーザー確認が必要になった時

## Verification

- `python3 -m unittest discover -s tests`

## Completion Gate

- `Goal done`: implementation / verification が完了し、backlog close / Session complete gate が完了または承認待ちとして明示されている
- `Backlog done`: backlog file と Notion が完了状態に更新されている
- `Session complete`: `Goal done` と `Backlog done` の両方を満たす
- `Backlog close wait`: implementation / verification は完了したが `/backlog done --from-goal` が未実行
- `Approval wait`: commit / push / Notion 更新などの承認ゲートで停止している
