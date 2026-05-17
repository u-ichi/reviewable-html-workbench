---
id: 5
title: "Milestone 4: Preview Runtime"
status: バックログ
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

- [ ] `preview --mode auto` がURLとPIDを返す。
- [ ] Tailscale IPv4が取れない場合は `127.0.0.1` にfallbackする。
- [ ] `0.0.0.0` bindが拒否される。
- [ ] `output/tmp/html-preview-sessions/*.json` にsession manifestが作成される。
- [ ] Preview Runtime仕様変更が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [ ] `preview_server.py` を実装する。
- [ ] 空きport選択を実装する。
- [ ] `tailscale ip -4` 検出とfallbackを実装する。
- [ ] session manifestの読み書きを実装する。
- [ ] stop方法を出力する。

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
- goal: ""
- state: ""
- final_receipt: ""

## 後回し (Deferred)

(空)

## 進捗ログ

### 2026-05-17

- 初期作成。

## 成果物

（完了時に記載）
