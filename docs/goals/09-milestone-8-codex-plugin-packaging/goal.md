# Goal: Codex pluginとして配布・導入できる形にし、base repo管理方式との統合方針を決める

## Backlog

- id: 09
- file: `docs/backlog/09-milestone-8-codex-plugin-packaging.md`
- notion:

## Objective

Codex pluginとして配布・導入できる形にし、base repo管理方式との統合方針を決める。

## Scope

- Codex plugin packaging
- marketplace登録手順
- base repo統合方針
- versioning/release
- 設計/計画HTML更新

## Stop Conditions

- Codex plugin導入方式とbase repo統合方針が決まった時
- Codex plugin仕様またはbase repo install設計の判断が必要になった時

## Verification

- `python3 -m json.tool .codex-plugin/plugin.json >/dev/null`
- `python3 -m unittest discover -s tests`

## Completion Gate

- `Goal done`: implementation / verification が完了し、backlog close / Session complete gate が完了または承認待ちとして明示されている
- `Backlog done`: backlog file と Notion が完了状態に更新されている
- `Session complete`: `Goal done` と `Backlog done` の両方を満たす
- `Backlog close wait`: implementation / verification は完了したが `/backlog done --from-goal` が未実行
- `Approval wait`: commit / push / Notion 更新などの承認ゲートで停止している
