# Goal: HTML上の範囲選択コメントをcomments.jsonへ安全に保存できるようにする

## Backlog

- id: 06
- file: `docs/backlog/06-milestone-5-comment-ui-store.md`
- notion:

## Objective

HTML上の範囲選択コメントをcomments.jsonへ安全に保存できるようにする。

## Scope

- `review-comments.js` 実装
- `comment_store.py` 実装
- comments schema対応
- standalone modeのlocalStorage export/import
- review-server modeの`comments.json`保存
- 設計/計画HTML更新
- 06完了直前、07着手前のユーザー確認ゲート

## Stop Conditions

- コメント作成、保存、再読込が自動検証できた時
- Preview URLでユーザー確認が完了した時
- ブラウザ側UI仕様の判断が必要になった時

## Verification

- `python3 -m unittest discover -s tests`
- `python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/comment-ui-review`
- `python3 -m scripts.html_review_workbench.cli preview --root output/tmp/comment-ui-review --mode local`
- Preview URLでのユーザー確認

## Completion Gate

- `Goal implementation done`: implementation / 自動検証が完了し、確認用Preview URLと確認観点を提示できる
- `User review wait`: implementation / 自動検証は完了したが、ユーザー確認が未完了
- `Backlog done`: backlog file と Notion が完了状態に更新されている
- `Session complete`: `Goal implementation done`、ユーザー確認、`Backlog done` のすべてを満たす
- `Approval wait`: commit / push / Notion 更新などの承認ゲートで停止している
