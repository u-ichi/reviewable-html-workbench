---
name: plan-preview
description: |
  Plan Mode の `<proposed_plan>` を出す直前に、計画の段階・依存関係・検証観点を一時HTMLで視覚確認したい時に使う agent-internal skill。plugin配布だけで発火し、ユーザーにCLI実行を求めず、agentが `plan-preview` CLIでセッション限定URLを作り、本文に自然に差し込む。Triggers: planをグラフィカルに見たい, planを図で確認したい, graphical plan review, proposed_planをプレビューして, 計画URLを入れて。使用しない場面: 通常の最終HTML生成、レビュー可能な設計資料作成、コメント取り込み、恒久成果物の公開、外部アップロードが必要な図式化。
argument-hint: "[plan-preview-payload.json]"
strict_procedure: true
---

# plan-preview

## 役割

Plan Mode で正式な `<proposed_plan>` を提示する直前に、同じ計画内容を一時HTML previewとして出す。

このskillは利用者が手でコマンドを打つためのものではない。agentが計画本文を組み立てた段階で `plan-preview` CLIを呼び、返却JSONの `url` を `<proposed_plan>` 内へ自然に入れる。

## Strict procedure profile

- Strictness: strict-procedure。Plan Mode の正式な実装基準は `<proposed_plan>` 本文であり、previewは判断補助として扱う。
- Hard gates: 外部サービス送信、shared state変更、永続ファイル出力、hook追加は行わない。
- Forcing function: `plan-preview` CLI、TTL付き一時ディレクトリ、`Plan preview: <url>` 行、失敗時の明示。
- Completion receipt: `<proposed_plan>` 内に preview URL または `Plan preview: unavailable (<reason>)` を含める。

## 発火条件

次のいずれかに当たる場合、このskillを使う。

- ユーザーが plan のグラフィカル表示、図示、preview URL、graphical plan review を求めている。
- 計画に phase、依存関係、並列worker、検証層、リスク・前提の分岐があり、文字だけでは確認しづらい。
- plugin利用者の体験として、Plan Mode の本文に自然にURLが入っていることが求められている。

## 使用しない場面

- 最終成果物としてHTMLを生成する場合。これは `visual-html-renderer` を使う。
- レビュー可能な設計資料を作り、HTML上のコメントを取り込む場合。これは `reviewable-design-doc` を使う。
- planとは無関係な説明資料、恒久公開資料、Notion投稿、外部アップロードが必要な図式化。

## 入力payload

agentは `<proposed_plan>` に入れる直前の計画を、次のJSON objectへ要約する。

```json
{
  "title": "Plan Preview",
  "summary": "この計画で何を達成するか",
  "phases": [
    {"title": "Phase 1", "detail": "調査と境界確認"}
  ],
  "key_changes": [
    "CLIを追加する",
    "skill metadataを追加する"
  ],
  "flow": [
    {"from": "計画作成", "to": "preview生成", "label": "agent内部"}
  ],
  "test_plan": [
    "unit test",
    "CLI smoke"
  ],
  "assumptions": [
    "hookは初期版では追加しない"
  ]
}
```

外部画像URL、外部asset、機密情報、未確定のsecret値はpayloadに入れない。

## CLI手順

1. renderer repo root を作業ディレクトリにする。現在のチャットやworkspaceのcwdをrepo rootとして扱わない。
2. payloadを標準入力で渡して、次を実行する。preview は `auto` mode を既定にし、Tailscale IPv4 を検出できる場合は Tailscale URL を優先する。

```bash
python3 -m scripts.html_review_workbench.cli plan-preview --payload - --ttl 1800 --mode auto
```

3. 成功したら返却JSONの `url` を `<proposed_plan>` 本文に入れる。推奨表記:

```text
Plan preview: http://<tailscale-ip-or-127.0.0.1>:<port>/index.html
```

Codex sandbox内で Tailscale 検出に失敗する場合は、IPだけを先に取得して `HTML_REVIEW_WORKBENCH_TAILSCALE_IP=<tailscale-ip>` を渡してから `plan-preview --mode auto` を起動する。

4. 失敗しても計画提示を止めない。代わりに短い理由を入れる。

```text
Plan preview: unavailable (<short reason>)
```

5. `stop_command` はagent用の後片付け手段であり、通常はユーザーに実行させない。TTLで自動終了する。

## 計画本文との関係

- 正式な実装基準は `<proposed_plan>` のテキスト。previewだけに存在する項目を作らない。
- preview URLは本文の冒頭または末尾ではなく、計画の確認に自然な位置へ置く。
- preview作成のために計画を短縮しない。HTML上は要約表示でも、本文では実施範囲、非範囲、検証条件を明示する。
- previewの生成に失敗した場合でも、`<proposed_plan>` 自体は成立させる。

## 禁止事項

- ユーザーに CLI を実行させない。
- Plan Mode の前にhookを自動追加しない。
- `output/` やplugin cacheにpreview成果物を残さない。
- 外部アップロードを使わない。
- Preview Runtime は `auto` mode で Tailscale IPv4 を優先し、検出できない場合だけ `127.0.0.1` にfallbackする。
- preview URLを正式な実装基準として扱わない。
