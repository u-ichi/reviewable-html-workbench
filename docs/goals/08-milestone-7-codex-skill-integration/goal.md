# Goal: Codex上で2つのskillから共通scriptを呼び、一連のHTMLレビューworkflowを実行できるようにする

## Backlog

- id: 08
- file: `docs/backlog/08-milestone-7-codex-skill-integration.md`
- notion:

## Objective

Codex上で2つのskillから共通scriptを呼び、一連のHTMLレビューworkflowを実行できるようにする。

## Scope

- Codex skill発火
- SKILL.md更新
- openai.yaml同期
- fixture workflow検証
- 設計/計画HTML更新

## Stop Conditions

- Codexで2 skillが実行可能になった時
- Codex plugin discovery仕様の追加調査が必要になった時

## Verification

- `python3 -m unittest discover -s tests`

## Completion Gate

- `Goal done`: implementation / verification が完了し、backlog close / Session complete gate が完了または承認待ちとして明示されている
- `Backlog done`: backlog file と Notion が完了状態に更新されている
- `Session complete`: `Goal done` と `Backlog done` の両方を満たす
- `Backlog close wait`: implementation / verification は完了したが `/backlog done --from-goal` が未実行
- `Approval wait`: commit / push / Notion 更新などの承認ゲートで停止している
