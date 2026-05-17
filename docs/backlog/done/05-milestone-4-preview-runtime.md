---
id: 5
title: "Milestone 4: Preview Runtime"
status: 完了
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "preview", "tailscale"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 05: Milestone 4: Preview Runtime

## 概要

HTML生成後にセッション限定サーバーを起動し、Tailscale IPv4優先、fallback `127.0.0.1` のpreview URLを提示できるようにする。

## ゴール条件

- [x] `preview --mode auto` がURLとPIDを返す。
- [x] Tailscale IPv4が取れない場合は `127.0.0.1` にfallbackする。
- [x] `0.0.0.0` bindが拒否される。
- [x] `output/tmp/html-preview-sessions/*.json` にsession manifestが作成される。
- [x] Preview Runtime仕様変更が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [x] `preview_server.py` を実装する。
- [x] 空きport選択を実装する。
- [x] `tailscale ip -4` 検出とfallbackを実装する。
- [x] session manifestの読み書きを実装する。
- [x] stop方法を出力する。

## 開発計画・設計同期ルール

- bind方針、session manifest、server停止方法が変わったら `docs/design.html` を更新する。
- Preview Runtimeの検証手順が変わったら `docs/development-plan.html` を更新する。

## Goal 実行

- goal-ready: true
- objective: "Codexから利用できるPreview Runtimeを実装し、Tailscale/localhost URLを安全に提示する"
- scope:
  - "preview_server.py実装"
  - "Tailscale fallback"
  - "0.0.0.0拒否"
  - "session manifest"
  - "設計/計画HTML更新"
- stop_conditions:
  - "preview URL提示とmanifest作成が検証できた時"
  - "network bind方針に追加判断が必要になった時"
- verification:
  - "python3 -m unittest discover -s tests"
- goal: "docs/goals/05-milestone-4-preview-runtime/goal.md"
- state: "docs/goals/05-milestone-4-preview-runtime/state.yaml"
- final_receipt: "docs/goals/05-milestone-4-preview-runtime/notes/verification-2026-05-17.md"

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。
- 作業開始。作業設計: Preview Runtime本体、CLI接続、session manifest、0.0.0.0拒否、設計/計画同期を進める。
- 実装: `preview_server.py` にbind選択、空きport選択、`python3 -m http.server` 起動、session manifest書き込み、停止コマンド出力を追加。`cli.py` の `preview` subcommand と接続。
- テスト: `tests/test_preview_server.py` を追加し、Tailscaleなしfallback、`0.0.0.0` 拒否、manifest / URL / PID出力を検証。
- 設計同期: `docs/design.html` と `docs/development-plan.html` にmanifest項目、PID、停止コマンド出力を反映。
- 検証: `python3 -m unittest discover -s tests`、`python3 -m scripts.html_review_workbench.cli render --model tests/fixtures/minimal_document_model.json --output output/tmp/test-render`、`python3 -m scripts.html_review_workbench.cli preview --root output/tmp/test-render --mode auto`、`python3 -m scripts.html_review_workbench.cli validate --root output/tmp/test-render`、`rg -n "Preview Runtime|html-preview-sessions|0.0.0.0|stop_command|URLとPID" docs/design.html docs/development-plan.html` が通過。
- 状態: implementation / verification は完了。`/backlog done 05 --from-goal docs/goals/05-milestone-4-preview-runtime` 待ち。
- 完了: `docs/goals/05-milestone-4-preview-runtime/notes/verification-2026-05-17.md` を final receipt として backlog を完了へ更新。

## 成果物

- `scripts/html_review_workbench/preview_server.py`: session-scoped preview server、bind選択、manifest書き込み。
- `scripts/html_review_workbench/cli.py`: `preview` subcommand を実装へ接続。
- `tests/test_preview_server.py`: fallback、unsafe bind拒否、URL/PID/manifest出力を検証。
- `docs/design.html` / `docs/development-plan.html`: Preview Runtime契約を同期。
