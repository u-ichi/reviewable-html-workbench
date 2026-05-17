---
id: 6
title: "Milestone 5: Comment UI and Store"
status: バックログ
notion_url: ""
notion_id: ""
parent_notion_url: ""
tags: ["milestone", "comments", "ui"]
assignee: ""
created: 2026-05-17
updated: 2026-05-17
---

# 06: Milestone 5: Comment UI and Store

## 概要

HTML上で範囲選択コメントを作成し、thread / reply / statusを持つ `comments.json` として保存できるようにする。

## ゴール条件

- [ ] HTML上で範囲選択コメントを作成できる。
- [ ] `comments.json` にcomment threadが保存される。
- [ ] agent reply / statusをschemaとして保持できる。
- [ ] 保存先が成果物ディレクトリ外へ出ない。
- [ ] コメントUI/保存仕様が `docs/design.html` と `docs/development-plan.html` に反映されている。

## やること

- [ ] `templates/review-comments.js` を実装する。
- [ ] Selection APIからblock id、選択テキスト、前後文脈を取得する。
- [ ] `comment_store.py` を実装する。
- [ ] standalone modeのlocalStorage export/importを実装する。
- [ ] review-server modeで `comments.json` を正本にする。

## 開発計画・設計同期ルール

- コメントschema、UI動作、保存先制約が変わったら `docs/design.html` を更新する。
- Comment UI milestoneの順序や完了条件が変わったら `docs/development-plan.html` を更新する。

## Goal 実行

- goal-ready: true
- objective: "HTML上の範囲選択コメントをcomments.jsonへ安全に保存できるようにする"
- scope:
  - "review-comments.js実装"
  - "comment_store.py実装"
  - "comments schema対応"
  - "設計/計画HTML更新"
- stop_conditions:
  - "コメント作成、保存、再読込が検証できた時"
  - "ブラウザ側UI仕様の判断が必要になった時"
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
