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
from scripts.html_review_workbench.plan_preview import (
    PlanPreviewError,
    create_plan_preview,
    read_payload as read_plan_preview_payload,
    stop_plan_preview,
)
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.preview_server import (
    DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    PreviewConfigurationError,
    start_preview,
)
from scripts.html_review_workbench.resolution_gate import check_gate as run_check_gate
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
    "plan-preview": {
        "purpose": "Create an ephemeral localhost preview for a proposed plan.",
        "required_options": (),
        "optional_options": ("--payload", "--ttl", "--mode"),
    },
    "plan-preview-stop": {
        "purpose": "Stop and clean up an ephemeral plan preview.",
        "required_options": ("--root",),
        "optional_options": ("--pid",),
    },
    "ingest-review": {
        "purpose": "Read review comments, classify them, and save review-cycle state.",
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
    "check-gates": {
        "purpose": "Check whether the resolution gate is open or blocked by unresolved clarification threads.",
        "required_options": ("--root",),
        "optional_options": ("--comments", "--state"),
    },
    "watch-comments": {
        "purpose": "Stream comment change events from a running preview server via SSE.",
        "required_options": ("--root",),
        "optional_options": ("--url",),
    },
    "notify-update": {
        "purpose": "Notify the preview server that the document has been updated.",
        "required_options": ("--root",),
        "optional_options": ("--url", "--message"),
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
    output_path = Path(args.output)
    index_path = render_bundle(Path(args.model), output_path)
    print(index_path)
    _check_render_gate(output_path)
    return 0


def _check_render_gate(output_dir: Path) -> None:
    """Print a stderr warning if the resolution gate is blocked."""
    import sys

    try:
        result = run_check_gate(output_dir)
    except Exception:
        return
    if result.gate == "blocked":
        thread_ids = [t["thread_id"] for t in result.blocking_threads]
        count = len(thread_ids)
        ids_str = ", ".join(thread_ids)
        print(
            f"WARNING: Resolution gate is blocked by {count} unresolved "
            f"clarification thread(s): {ids_str}. "
            f"Do not proceed with design changes.",
            file=sys.stderr,
        )


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


def plan_preview(args: argparse.Namespace) -> int:
    try:
        payload = read_plan_preview_payload(args.payload)
        result = create_plan_preview(payload, ttl=args.ttl, mode=args.mode)
    except (OSError, PreviewConfigurationError, PlanPreviewError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result.to_payload(), ensure_ascii=False))
    return 0


def plan_preview_stop(args: argparse.Namespace) -> int:
    try:
        result = stop_plan_preview(Path(args.root), pid=args.pid)
    except (OSError, PlanPreviewError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc), "root": args.root}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
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
    root = Path(args.root)
    try:
        store = CommentStore(root, args.comments)
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
    _publish_comment_updated(root, args.thread_id)
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


def _publish_comment_updated(root: Path, thread_id: str) -> None:
    """Notify an active preview session that comments changed."""
    from scripts.html_review_workbench.preview_server import find_active_session
    from scripts.html_review_workbench.watch_comments import post_event

    session = find_active_session(root.resolve())
    if session is None:
        return
    bind = session.get("bind")
    port = session.get("port")
    if not isinstance(bind, str) or not isinstance(port, int):
        return
    try:
        post_event(
            f"http://{bind}:{port}",
            "comment_updated",
            {"source": "agent", "thread_id": thread_id},
        )
    except (ConnectionRefusedError, ConnectionResetError, OSError, ValueError, json.JSONDecodeError):
        return


def check_gates(args: argparse.Namespace) -> int:
    result = run_check_gate(
        Path(args.root),
        comments_path=args.comments,
        state_path=args.state,
    )
    print(json.dumps(result.to_payload(), ensure_ascii=False))
    return 0


def watch_comments(args: argparse.Namespace) -> int:
    from scripts.html_review_workbench.watch_comments import run_watch
    from scripts.html_review_workbench.preview_server import find_active_session
    root = Path(args.root).resolve()
    url = args.url
    if not url:
        session = find_active_session(root)
        if session is None:
            print(json.dumps({"status": "failed", "error": "no active preview session found"}, ensure_ascii=False))
            return 2
        url = f"http://{session['bind']}:{session['port']}"
    return run_watch(url, root=root)


def notify_update(args: argparse.Namespace) -> int:
    from scripts.html_review_workbench.watch_comments import send_notify
    from scripts.html_review_workbench.preview_server import find_active_session
    root = Path(args.root).resolve()
    url = args.url
    if not url:
        session = find_active_session(root)
        if session is None:
            print(json.dumps({"status": "failed", "error": "no active preview session found"}, ensure_ascii=False))
            return 2
        url = f"http://{session['bind']}:{session['port']}"
    return send_notify(url, message=args.message)


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
    preview_parser.add_argument("--idle-timeout", type=float, default=DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS)
    preview_parser.add_argument("--owner-grace", type=float, default=300.0)
    preview_parser.set_defaults(func=preview)

    plan_preview_parser = subparsers.add_parser(
        "plan-preview",
        help=str(COMMAND_CONTRACT["plan-preview"]["purpose"]),
        description=str(COMMAND_CONTRACT["plan-preview"]["purpose"]),
    )
    plan_preview_parser.add_argument("--payload", default="-")
    plan_preview_parser.add_argument("--ttl", type=float, default=1800.0)
    plan_preview_parser.add_argument("--mode", choices=["auto", "tailscale", "local"], default="auto")
    plan_preview_parser.set_defaults(func=plan_preview)

    plan_preview_stop_parser = subparsers.add_parser(
        "plan-preview-stop",
        help=str(COMMAND_CONTRACT["plan-preview-stop"]["purpose"]),
        description=str(COMMAND_CONTRACT["plan-preview-stop"]["purpose"]),
    )
    plan_preview_stop_parser.add_argument("--root", required=True)
    plan_preview_stop_parser.add_argument("--pid", type=int)
    plan_preview_stop_parser.set_defaults(func=plan_preview_stop)

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

    check_gates_parser = subparsers.add_parser(
        "check-gates",
        help=str(COMMAND_CONTRACT["check-gates"]["purpose"]),
        description=str(COMMAND_CONTRACT["check-gates"]["purpose"]),
    )
    check_gates_parser.add_argument("--root", required=True)
    check_gates_parser.add_argument("--comments", default="annotations/comments.json")
    check_gates_parser.add_argument("--state", default="annotations/review-cycle-state.json")
    check_gates_parser.set_defaults(func=check_gates)

    watch_comments_parser = subparsers.add_parser(
        "watch-comments",
        help=str(COMMAND_CONTRACT["watch-comments"]["purpose"]),
        description=str(COMMAND_CONTRACT["watch-comments"]["purpose"]),
    )
    watch_comments_parser.add_argument("--root", required=True)
    watch_comments_parser.add_argument("--url")
    watch_comments_parser.set_defaults(func=watch_comments)

    notify_update_parser = subparsers.add_parser(
        "notify-update",
        help=str(COMMAND_CONTRACT["notify-update"]["purpose"]),
        description=str(COMMAND_CONTRACT["notify-update"]["purpose"]),
    )
    notify_update_parser.add_argument("--root", required=True)
    notify_update_parser.add_argument("--url")
    notify_update_parser.add_argument("--message", default="")
    notify_update_parser.set_defaults(func=notify_update)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
