# Reviewable HTML Workbench

[![Test](https://github.com/u-ichi/reviewable-html-workbench/actions/workflows/test.yml/badge.svg)](https://github.com/u-ichi/reviewable-html-workbench/actions/workflows/test.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A Claude Code / Codex CLI plugin that lets you review agent-generated HTML documents with inline comments — and have the agent read those comments, reply, and improve the document in the next iteration.

![Overview](docs/images/overview.png)

## Overview

Agent workflows produce reports, design documents, and comparison tables — but turning those outputs into something you actually trust requires back-and-forth review. Chat-based feedback loses context: "fix the table in section 3" works once, but doesn't scale when you have dozens of comments across a long document.

Reviewable HTML Workbench solves this by putting the review conversation **inside the document itself**:

1. **Generate** — The agent produces an HTML bundle with structured sections, diagrams, and images.
2. **Review** — You open the preview, select any text or image, and leave a comment right where the issue is.
3. **Ingest** — The agent reads your comments, classifies each one, and writes replies explaining what it will change.
4. **Improve** — The agent updates the document, re-renders, and you see the changes in context.
5. **Repeat** — Keep commenting and refining until the document is ready.

Comments are attached to exact document ranges and persisted as structured JSON, so nothing is lost between iterations. When you're satisfied, export the final document as a single self-contained HTML file.

The plugin includes two skills. `visual-html-renderer` creates, validates, renders, and previews visual HTML documents. `reviewable-design-doc` builds review-ready design documents and ingests review comments back into the agent workflow — including agent replies, comment classification, and review-cycle state tracking.

## Features

- **Inline Review Comments**: select any text or image in the preview to leave a comment. Comments are highlighted in the document with margin cards showing status, replies, and threading.
- **Review Ingestion**: the agent reads `annotations/comments.json`, classifies each comment (actionable, clarification, already addressed, etc.), writes agent replies, and tracks review-cycle state — so the review conversation stays structured across iterations.
- **Publish & Download**: switch to a clean reading view with no review UI, then download a single self-contained HTML file with all CSS and images embedded. The exported file auto-detects OS light/dark theme.
- **Document Model**: schema-driven document input for predictable HTML generation.
- **HTML Rendering**: produces `index.html`, copied assets, and `renderer-manifest.json`.
- **Preview Server with Tailscale**: starts a session-scoped preview server, preferring Tailscale IPv4 and falling back to `127.0.0.1`; `0.0.0.0` bind is rejected.
- **Dark/Light Theme**: UI support for theme switching in rendered review documents.
- **Diagram + Image Support**: stores Mermaid sources, renders fallback diagrams, and attaches generated image assets to document model blocks.

## Installation

### Claude Code

Add the GitHub repository as a plugin marketplace and install:

```bash
claude plugin marketplace add u-ichi/reviewable-html-workbench
claude plugin install reviewable-html-workbench
```

Alternatively, clone the repository and install locally:

```bash
git clone https://github.com/u-ichi/reviewable-html-workbench.git
cd reviewable-html-workbench
claude plugins install .
```

For local development, run Claude Code with this plugin directory:

```bash
claude --plugin-dir /path/to/reviewable-html-workbench
```

### Codex CLI

Add the GitHub repository as a plugin marketplace and install:

```bash
codex plugin marketplace add u-ichi/reviewable-html-workbench
codex plugin install reviewable-html-workbench
```

Or clone and register locally:

```bash
git clone https://github.com/u-ichi/reviewable-html-workbench.git
codex plugin marketplace add ./reviewable-html-workbench
```

## Quick Start

The plugin is used by agents inside Claude Code or Codex CLI. A typical workflow:

### 1. Agent generates the document

The agent creates a document model, renders it to HTML, and starts a preview server:

```bash
python3 -m scripts.html_review_workbench.cli build-model \
  --text "Write a short reviewable design note." \
  --title "Example Design Note" \
  --document-id example-design-note \
  --output output/tmp/example/document-model.json

python3 -m scripts.html_review_workbench.cli render \
  --model output/tmp/example/document-model.json \
  --output output/tmp/example/bundle

python3 -m scripts.html_review_workbench.cli preview \
  --root output/tmp/example/bundle --mode auto
```

The agent shares the preview URL with you.

### 2. You review in the browser

Open the preview URL, select any text or image, and leave comments directly in the document. Comments are saved to `annotations/comments.json`.

### 3. Agent reads and replies

Tell the agent you've added comments. The agent ingests them, reads each comment in context, and writes replies back to the same comment threads:

```bash
python3 -m scripts.html_review_workbench.cli ingest-review \
  --root output/tmp/example/bundle

python3 -m scripts.html_review_workbench.cli add-reply \
  --root output/tmp/example/bundle \
  --thread-id <comment-id> \
  --body "Reply text based on the comment content and document context"
```

You see the agent's replies in the browser, in the same comment thread where you left your review.

### 4. Iterate

The agent updates the document based on your feedback, re-renders, and you continue reviewing until the document is ready.

## Skills

| Skill | Purpose | Trigger examples |
|---|---|---|
| `visual-html-renderer` | Generate, validate, and preview final HTML bundles from document models. | `html出力して`, `HTMLにして`, `HTMLで出して`, `この内容をHTMLで出して`, `HTMLでプレビューして`, `HTMLレンダラー`, `HTML出力を共通化`, `図示つきHTML`, `visual HTML renderer` |
| `reviewable-design-doc` | Create review-ready design documents and ingest review comments back into the workflow. | `レビュー可能な設計資料`, `設計資料をHTMLで`, `design doc`, `reviewable design doc`, `レビュー終わったので確認して`, `コメントを反映して` |

## CLI Reference

All commands are exposed through:

```bash
python3 -m scripts.html_review_workbench.cli <command>
```

| Command | Description |
|---|---|
| `build-model` | Build a document model from natural content. |
| `render` | Generate an HTML bundle from a document model. |
| `check-model` | Check whether a document model is ready for final HTML rendering. |
| `attach-image` | Attach a generated image asset to an image-capable block in a document model. |
| `preview` | Start or describe a session-scoped preview runtime. |
| `ingest-review` | Read review comments, classify them, write agent replies, and save review-cycle state. |
| `validate` | Validate a generated HTML bundle. |
| `add-reply` | Add an agent reply to a comment thread in `comments.json`. |

## Schemas

The workbench is schema-driven:

- `schemas/document-model.schema.json`
- `schemas/comments.schema.json`
- `schemas/preview-session.schema.json`

These schemas define the rendered document model, persisted review comments, and preview session metadata.

## Development

Requirements:

- Python 3.11+
- No Python package dependencies for the core runtime
- Standard library tests with `unittest`

Run tests:

```bash
PYTHONPYCACHEPREFIX="$PWD/tmp/python-pycache" python3 -m unittest discover -s tests
```

Validate plugin manifests:

```bash
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
```

Validate the Claude Code plugin manifest:

```bash
claude plugins validate .
```

Check the CLI entrypoint:

```bash
python3 -m scripts.html_review_workbench.cli --help
```

## License

MIT

<details>
<summary>日本語</summary>

Reviewable HTML Workbench は、Claude Code / Codex CLI 向けの HTML レビュー用プラグインです。agent が生成した設計資料・調査レポート・比較表を HTML で出力し、本文の任意の箇所にレビューコメントを書き込めます。agent はそのコメントを読み取り、返信し、内容を改善して再出力します。コメントと改善を繰り返して、ドキュメントを一緒に磨き上げるワークフローを実現します。

完成したら、レビュー要素を除いた読者向けの HTML を 1 ファイルでダウンロードできます（CSS・画像埋め込み済み、OS テーマ自動検知対応）。

2つの skill を含みます。

- `visual-html-renderer`: HTML生成、図示、Preview Runtime、bundle検証。
- `reviewable-design-doc`: レビュー可能な設計資料作成、コメント取り込み、agent返信、設計反映。

インストール:

```bash
# Claude Code（GitHub から直接）
claude plugin marketplace add u-ichi/reviewable-html-workbench
claude plugin install reviewable-html-workbench

# Codex CLI（GitHub から直接）
codex plugin marketplace add u-ichi/reviewable-html-workbench
```

テストは次のコマンドで実行します。

```bash
PYTHONPYCACHEPREFIX="$PWD/tmp/python-pycache" python3 -m unittest discover -s tests
```

</details>
