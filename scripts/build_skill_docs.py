#!/usr/bin/env python3
"""Rebuild shared sections inside skill documentation."""

from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS_DIR = ROOT / "docs" / "skill-fragments"
BEGIN = "<!-- BEGIN SHARED: {name} -->"
END = "<!-- END SHARED: {name} -->"


@dataclass(frozen=True)
class SkillDocTarget:
    path: Path
    fragments: tuple[str, ...]
    variables: dict[str, str]


VISUAL_CLI_COMMANDS = """```bash
python3 -m scripts.html_review_workbench.cli build-model \\
  --text "<content>" \\
  --output <document-model.json>

python3 -m scripts.html_review_workbench.cli attach-image \\
  --model <document-model.json> \\
  --block-id <generated-image-block-id> \\
  --image <generated-image-path>

python3 -m scripts.html_review_workbench.cli check-model \\
  --model <document-model.json>

python3 -m scripts.html_review_workbench.cli render \\
  --model <document-model.json> \\
  --output <output-dir>

python3 -m scripts.html_review_workbench.cli validate \\
  --root <output-dir>

python3 -m scripts.html_review_workbench.cli preview \\
  --root <output-dir> \\
  --mode auto

python3 -m scripts.html_review_workbench.cli publish \\
  --root <rendered-bundle-dir> \\
  --output <publish-output-dir>
```"""


REVIEWABLE_CLI_COMMANDS = """```bash
python3 -m scripts.html_review_workbench.cli build-model \\
  --text "<existing content when converting an existing source>" \\
  --output <document-model.json>

python3 -m scripts.html_review_workbench.cli attach-image \\
  --model <document-model.json> \\
  --block-id <generated-image-block-id> \\
  --image <generated-image-path>

python3 -m scripts.html_review_workbench.cli check-model \\
  --model <document-model.json>

python3 -m scripts.html_review_workbench.cli render \\
  --model <document-model.json> \\
  --output <output-dir>

python3 -m scripts.html_review_workbench.cli validate \\
  --root <output-dir>

python3 -m scripts.html_review_workbench.cli preview \\
  --root <output-dir> \\
  --mode auto
```"""


TARGETS = (
    SkillDocTarget(
        path=ROOT / "skills" / "visual-html-renderer" / "SKILL.md",
        fragments=(
            "md-file-prohibition",
            "mermaid-kinds",
            "repo-root-resolution",
            "cli-commands-core",
            "preview-owner-pid-note",
            "tailscale-sandbox-fallback",
        ),
        variables={
            "skill_path": "skills/visual-html-renderer/SKILL.md",
            "md_file_prohibition_ja": (
                "- 一時入力ファイルが必要な場合も `.md` は使わない。"
                "`source.txt`, `input.txt`, `source-content.txt` のようなプレーンテキスト名を使う。\n"
                "- ユーザーへの進捗・最終報告では、`.md` やMarkdownという語をHTML出力の前提として扱わない。"
            ),
            "cli_commands_core_ja": VISUAL_CLI_COMMANDS,
            "preview_owner_pid_note_ja": (
                "Codex / Claude では preview コマンドを一回限りの shell から起動することがあるため、"
                "標準手順では `--owner-pid` を渡さない。preview server は 24時間アクセスが無い場合に idle timeout で自動停止する。"
            ),
            "tailscale_sandbox_fallback_ja": (
                "Codex sandbox内で `tailscale ip -4` が設定ファイル読み取りに失敗する場合は、"
                "preview本体をsandbox内で起動したまま、IPだけを小さいresolverで先に取得して渡す。\n\n"
                "```bash\n"
                "python3 -m scripts.html_review_workbench.preview_host_resolve\n\n"
                "HTML_REVIEW_WORKBENCH_TAILSCALE_IP=<tailscale-ip> \\\n"
                "  python3 -m scripts.html_review_workbench.cli preview \\\n"
                "    --root <output-dir> \\\n"
                "    --mode auto\n"
                "```"
            ),
        },
    ),
    SkillDocTarget(
        path=ROOT / "skills" / "reviewable-design-doc" / "SKILL.md",
        fragments=(
            "md-file-prohibition",
            "mermaid-kinds",
            "repo-root-resolution",
            "cli-commands-core",
            "preview-owner-pid-note",
            "tailscale-sandbox-fallback",
        ),
        variables={
            "skill_path": "skills/reviewable-design-doc/SKILL.md",
            "md_file_prohibition_ja": (
                "設計資料作成は、`.md` 原稿をHTMLへ変換する作業ではない。"
                "`reviewable-design-doc` は、設計内容を最初からレビュー可能なHTML bundleの情報設計として作る。\n\n"
                "- 新規に設計資料を作る場合、最初の保存対象は `output/tmp/<purpose>/document-model.json` "
                "または `output/<YYYY-MM-DD>_<name>/document-model.json` にする。\n"
                "- `.md` ファイルを設計本文の下書き、中間成果物、HTML化対象として作らない。\n"
                "- 一時的に自然文入力を保存する必要がある場合だけ、"
                "`source.txt`, `input.txt`, `source-content.txt` のようなプレーンテキスト名を使う。"
            ),
            "cli_commands_core_ja": REVIEWABLE_CLI_COMMANDS,
            "preview_owner_pid_note_ja": (
                "Codex / Claude では preview コマンドを一回限りの shell から起動することがあるため、"
                "標準手順では `--owner-pid` を渡さない。preview server は 24時間アクセスが無い場合に idle timeout で自動停止する。"
                "長寿命の所有プロセスが明確に分かる場合だけ `--owner-pid <pid>` を使ってよい。"
                "一回限りの shell の `$$` や `$PPID` は短命プロセスを指すため使わない。"
            ),
            "tailscale_sandbox_fallback_ja": (
                "Codex sandbox内で `tailscale ip -4` が設定ファイル読み取りに失敗する場合は、"
                "`visual-html-renderer` と同じく `python3 -m scripts.html_review_workbench.preview_host_resolve` "
                "で取得したIPv4を `HTML_REVIEW_WORKBENCH_TAILSCALE_IP` に渡してから `preview --mode auto` を起動する。"
            ),
        },
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated skill docs differ")
    args = parser.parse_args()

    changed = False
    for target in TARGETS:
        current = target.path.read_text(encoding="utf-8")
        generated = render_target(current, target)
        if current == generated:
            continue
        changed = True
        if args.check:
            sys.stderr.write(f"skill doc drift: {target.path.relative_to(ROOT)}\n")
            sys.stderr.writelines(
                difflib.unified_diff(
                    current.splitlines(keepends=True),
                    generated.splitlines(keepends=True),
                    fromfile=str(target.path.relative_to(ROOT)),
                    tofile=f"{target.path.relative_to(ROOT)} (generated)",
                )
            )
        else:
            target.path.write_text(generated, encoding="utf-8")

    if args.check and changed:
        return 1
    return 0


def render_target(text: str, target: SkillDocTarget) -> str:
    rendered = text
    for name in target.fragments:
        rendered = replace_fragment(rendered, name, render_fragment(name, target.variables))
    return rendered


def render_fragment(name: str, variables: dict[str, str]) -> str:
    parts = []
    for lang in ("ja", "en"):
        path = FRAGMENTS_DIR / f"{name}.{lang}.md"
        if not path.is_file():
            raise FileNotFoundError(path)
        rendered = apply_variables(path.read_text(encoding="utf-8").rstrip("\n"), variables)
        if rendered:
            parts.append(rendered)
    return "\n\n".join(parts)


def apply_variables(template: str, variables: dict[str, str]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    unresolved = [part.split("}}", 1)[0] for part in rendered.split("{{")[1:] if "}}" in part]
    if unresolved:
        raise ValueError(f"unresolved template variables: {', '.join(sorted(set(unresolved)))}")
    return rendered


def replace_fragment(text: str, name: str, body: str) -> str:
    begin = BEGIN.format(name=name)
    end = END.format(name=name)
    start = text.find(begin)
    if start == -1:
        return text
    end_index = text.find(end, start)
    if end_index == -1:
        raise ValueError(f"missing end marker for shared fragment: {name}")
    end_index += len(end)
    replacement = f"{begin}\n{body}\n{end}"
    return text[:start] + replacement + text[end_index:]


if __name__ == "__main__":
    raise SystemExit(main())
