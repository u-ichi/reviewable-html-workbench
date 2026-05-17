"""Command-line entrypoint for Reviewable HTML Workbench.

The commands are intentionally skeletal in the initial project. Each subcommand
owns a stable contract that skills can call while the implementation grows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


COMMAND_CONTRACT: dict[str, dict[str, str | tuple[str, ...]]] = {
    "render": {
        "purpose": "Generate an HTML bundle from a document model.",
        "required_options": ("--model", "--output"),
    },
    "preview": {
        "purpose": "Start or describe a session-scoped preview runtime.",
        "required_options": ("--root",),
        "optional_options": ("--mode",),
    },
    "ingest-review": {
        "purpose": "Read review comments and prepare feedback ingestion.",
        "required_options": ("--root",),
        "optional_options": ("--comments",),
    },
    "validate": {
        "purpose": "Validate a generated HTML bundle.",
        "required_options": ("--root",),
    },
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render(args: argparse.Namespace) -> int:
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.html"
    index_path.write_text("<!doctype html><meta charset=\"utf-8\"><title>Reviewable HTML Workbench</title>\n", encoding="utf-8")
    _write_json(output_dir / "renderer-manifest.json", {"status": "placeholder", "model": args.model})
    print(index_path)
    return 0


def preview(args: argparse.Namespace) -> int:
    payload = {
        "status": "not-started",
        "reason": "preview server implementation pending",
        "root": args.root,
        "mode": args.mode,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def ingest_review(args: argparse.Namespace) -> int:
    payload = {
        "status": "not-started",
        "reason": "review ingestion implementation pending",
        "root": args.root,
        "comments": args.comments,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def validate(args: argparse.Namespace) -> int:
    root = Path(args.root)
    required = [root / "index.html", root / "renderer-manifest.json"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="html-review-workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser(
        "render",
        help=str(COMMAND_CONTRACT["render"]["purpose"]),
        description=str(COMMAND_CONTRACT["render"]["purpose"]),
    )
    render_parser.add_argument("--model", required=True)
    render_parser.add_argument("--output", required=True)
    render_parser.set_defaults(func=render)

    preview_parser = subparsers.add_parser(
        "preview",
        help=str(COMMAND_CONTRACT["preview"]["purpose"]),
        description=str(COMMAND_CONTRACT["preview"]["purpose"]),
    )
    preview_parser.add_argument("--root", required=True)
    preview_parser.add_argument("--mode", choices=["auto", "tailscale", "local", "off"], default="auto")
    preview_parser.set_defaults(func=preview)

    ingest_parser = subparsers.add_parser(
        "ingest-review",
        help=str(COMMAND_CONTRACT["ingest-review"]["purpose"]),
        description=str(COMMAND_CONTRACT["ingest-review"]["purpose"]),
    )
    ingest_parser.add_argument("--root", required=True)
    ingest_parser.add_argument("--comments", default="annotations/comments.json")
    ingest_parser.set_defaults(func=ingest_review)

    validate_parser = subparsers.add_parser(
        "validate",
        help=str(COMMAND_CONTRACT["validate"]["purpose"]),
        description=str(COMMAND_CONTRACT["validate"]["purpose"]),
    )
    validate_parser.add_argument("--root", required=True)
    validate_parser.set_defaults(func=validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
