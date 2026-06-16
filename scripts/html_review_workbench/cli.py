"""Command-line entrypoint for Reviewable HTML Workbench.

The commands are intentionally skeletal in the initial project. Each subcommand
owns a stable contract that skills can call while the implementation grows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.comment_store import CommentStore, CommentStoreError
from scripts.html_review_workbench.image_assets import ImageAssetError, attach_image_to_model
from scripts.html_review_workbench.ingest_review import ReviewIngestionError, ingest_review as run_ingest_review
from scripts.html_review_workbench.model_builder import ModelBuildError, build_model_from_source
from scripts.html_review_workbench.model_quality import check_model_quality
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.preview_server import PreviewConfigurationError, start_preview
from scripts.html_review_workbench.validate_bundle import validate_bundle


COMMAND_CONTRACT: dict[str, dict[str, str | tuple[str, ...]]] = {
    "build-model": {
        "purpose": "Build a document model from natural content.",
        "required_options": ("--output",),
        "optional_options": ("--text", "--input", "--title", "--document-id"),
    },
    "render": {
        "purpose": "Generate an HTML bundle from a document model.",
        "required_options": ("--model", "--output"),
    },
    "check-model": {
        "purpose": "Check whether a document model is ready for final HTML rendering.",
        "required_options": ("--model",),
    },
    "attach-image": {
        "purpose": "Attach a generated image asset to an image-capable block in a document model.",
        "required_options": ("--model", "--block-id", "--image"),
        "optional_options": ("--output",),
    },
    "preview": {
        "purpose": "Start or describe a session-scoped preview runtime.",
        "required_options": ("--root",),
        "optional_options": ("--mode", "--owner-session", "--owner-pid", "--idle-timeout", "--owner-grace"),
    },
    "ingest-review": {
        "purpose": "Read review comments, classify them, write agent replies, and save review-cycle state.",
        "required_options": ("--root",),
        "optional_options": ("--comments", "--state", "--model", "--apply-model"),
    },
    "validate": {
        "purpose": "Validate a generated HTML bundle.",
        "required_options": ("--root",),
    },
    "add-reply": {
        "purpose": "Add an agent reply to a comment thread in comments.json.",
        "required_options": ("--root", "--thread-id", "--body"),
        "optional_options": ("--comments", "--kind", "--author"),
    },
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_model(args: argparse.Namespace) -> int:
    try:
        result = build_model_from_source(
            output_path=Path(args.output),
            text=args.text,
            input_path=Path(args.input) if args.input else None,
            title=args.title,
            document_id=args.document_id,
        )
    except (OSError, ModelBuildError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(result.path)
    return 0


def render(args: argparse.Namespace) -> int:
    index_path = render_bundle(Path(args.model), Path(args.output))
    print(index_path)
    return 0


def check_model(args: argparse.Namespace) -> int:
    result = check_model_quality(Path(args.model))
    print(json.dumps(result.to_payload(), ensure_ascii=False))
    return 0 if result.ok else 1


def attach_image(args: argparse.Namespace) -> int:
    try:
        result = attach_image_to_model(
            model_path=Path(args.model),
            block_id=args.block_id,
            image_path=Path(args.image),
            output_path=Path(args.output) if args.output else None,
        )
    except (OSError, ImageAssetError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": "ok",
                "model": str(result.model_path),
                "block_id": result.block_id,
                "source_path": result.source_path,
            },
            ensure_ascii=False,
        )
    )
    return 0


def preview(args: argparse.Namespace) -> int:
    if args.mode == "off":
        print(json.dumps({"status": "off", "root": args.root, "mode": args.mode}, ensure_ascii=False))
        return 0
    try:
        session = start_preview(
            Path(args.root),
            args.mode,
            owner_session=args.owner_session,
            owner_pid=args.owner_pid,
            idle_timeout=args.idle_timeout,
            owner_grace=args.owner_grace,
        )
    except PreviewConfigurationError as exc:
        print(json.dumps({"status": "failed", "error": str(exc), "root": args.root, "mode": args.mode}, ensure_ascii=False))
        return 2
    print(json.dumps(session.to_payload(), ensure_ascii=False))
    return 0


def ingest_review(args: argparse.Namespace) -> int:
    try:
        result = run_ingest_review(
            Path(args.root),
            comments_path=args.comments,
            state_path=args.state,
            model_path=Path(args.model) if args.model else None,
            apply_model=args.apply_model,
        )
    except (CommentStoreError, ReviewIngestionError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result.payload, ensure_ascii=False))
    return 0


def validate(args: argparse.Namespace) -> int:
    result = validate_bundle(Path(args.root))
    print(json.dumps(result.to_payload(), ensure_ascii=False))
    return 0 if result.ok else 1


def add_reply(args: argparse.Namespace) -> int:
    try:
        store = CommentStore(Path(args.root), args.comments)
        payload = store.read("document")
        document_id = payload["document_id"]
        reply = store.add_reply(
            document_id=document_id,
            thread_id=args.thread_id,
            author=args.author,
            role="agent",
            kind=args.kind,
            body=args.body,
        )
    except CommentStoreError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": "ok",
                "thread_id": args.thread_id,
                "reply_id": reply["id"],
                "thread_status": "needs_user_reply",
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="html-review-workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_model_parser = subparsers.add_parser(
        "build-model",
        help=str(COMMAND_CONTRACT["build-model"]["purpose"]),
        description=str(COMMAND_CONTRACT["build-model"]["purpose"]),
    )
    build_model_parser.add_argument("--text")
    build_model_parser.add_argument("--input")
    build_model_parser.add_argument("--output", required=True)
    build_model_parser.add_argument("--title")
    build_model_parser.add_argument("--document-id")
    build_model_parser.set_defaults(func=build_model)

    render_parser = subparsers.add_parser(
        "render",
        help=str(COMMAND_CONTRACT["render"]["purpose"]),
        description=str(COMMAND_CONTRACT["render"]["purpose"]),
    )
    render_parser.add_argument("--model", required=True)
    render_parser.add_argument("--output", required=True)
    render_parser.set_defaults(func=render)

    check_model_parser = subparsers.add_parser(
        "check-model",
        help=str(COMMAND_CONTRACT["check-model"]["purpose"]),
        description=str(COMMAND_CONTRACT["check-model"]["purpose"]),
    )
    check_model_parser.add_argument("--model", required=True)
    check_model_parser.set_defaults(func=check_model)

    attach_image_parser = subparsers.add_parser(
        "attach-image",
        help=str(COMMAND_CONTRACT["attach-image"]["purpose"]),
        description=str(COMMAND_CONTRACT["attach-image"]["purpose"]),
    )
    attach_image_parser.add_argument("--model", required=True)
    attach_image_parser.add_argument("--block-id", required=True)
    attach_image_parser.add_argument("--image", required=True)
    attach_image_parser.add_argument("--output")
    attach_image_parser.set_defaults(func=attach_image)

    preview_parser = subparsers.add_parser(
        "preview",
        help=str(COMMAND_CONTRACT["preview"]["purpose"]),
        description=str(COMMAND_CONTRACT["preview"]["purpose"]),
    )
    preview_parser.add_argument("--root", required=True)
    preview_parser.add_argument("--mode", choices=["auto", "tailscale", "local", "off"], default="auto")
    preview_parser.add_argument("--owner-session")
    preview_parser.add_argument("--owner-pid", type=int)
    preview_parser.add_argument("--idle-timeout", type=float, default=3600.0)
    preview_parser.add_argument("--owner-grace", type=float, default=300.0)
    preview_parser.set_defaults(func=preview)

    ingest_parser = subparsers.add_parser(
        "ingest-review",
        help=str(COMMAND_CONTRACT["ingest-review"]["purpose"]),
        description=str(COMMAND_CONTRACT["ingest-review"]["purpose"]),
    )
    ingest_parser.add_argument("--root", required=True)
    ingest_parser.add_argument("--comments", default="annotations/comments.json")
    ingest_parser.add_argument("--state", default="annotations/review-cycle-state.json")
    ingest_parser.add_argument("--model")
    ingest_parser.add_argument("--apply-model", action="store_true")
    ingest_parser.set_defaults(func=ingest_review)

    validate_parser = subparsers.add_parser(
        "validate",
        help=str(COMMAND_CONTRACT["validate"]["purpose"]),
        description=str(COMMAND_CONTRACT["validate"]["purpose"]),
    )
    validate_parser.add_argument("--root", required=True)
    validate_parser.set_defaults(func=validate)

    add_reply_parser = subparsers.add_parser(
        "add-reply",
        help=str(COMMAND_CONTRACT["add-reply"]["purpose"]),
        description=str(COMMAND_CONTRACT["add-reply"]["purpose"]),
    )
    add_reply_parser.add_argument("--root", required=True)
    add_reply_parser.add_argument("--thread-id", required=True)
    add_reply_parser.add_argument("--body", required=True)
    add_reply_parser.add_argument("--comments", default="annotations/comments.json")
    add_reply_parser.add_argument("--kind", default="answer")
    add_reply_parser.add_argument("--author", default="agent")
    add_reply_parser.set_defaults(func=add_reply)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
