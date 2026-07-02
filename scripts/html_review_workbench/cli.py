"""Command-line entrypoint for Reviewable HTML Workbench.

The commands are intentionally skeletal in the initial project. Each subcommand
owns a stable contract that skills can call while the implementation grows.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
from scripts.html_review_workbench.publish import PublishError, publish_bundle
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.preview_server import (
    DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    PreviewConfigurationError,
    start_preview,
)
from scripts.html_review_workbench.resolution_gate import check_gate as run_check_gate
from scripts.html_review_workbench.resolution_gate import try_check_gate
from scripts.html_review_workbench.validate_bundle import validate_bundle


def _fail(exc: Exception, **extra: object) -> int:
    payload = {"status": "failed", "error": str(exc)}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))
    return 2


def active_session_base_url(root: Path) -> str | None:
    from scripts.html_review_workbench.preview_server import find_active_session

    session = find_active_session(root.resolve())
    if session is None:
        return None
    bind = session.get("bind")
    port = session.get("port")
    if not isinstance(bind, str) or not isinstance(port, int):
        return None
    return f"http://{bind}:{port}"


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
        return _fail(exc)
    print(result.path)
    return 0


def render(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    index_path = render_bundle(Path(args.model), output_path)
    print(index_path)
    _check_render_gate(output_path)
    return 0


def publish(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.output:
        output = Path(args.output)
    else:
        output = root.parent / f"{root.name}-published"
    try:
        result = publish_bundle(root, output)
    except (OSError, PublishError) as exc:
        return _fail(exc)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _check_render_gate(output_dir: Path) -> None:
    """Print a stderr warning if the resolution gate is blocked."""
    import sys

    result = try_check_gate(output_dir)
    if result is None:
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
        return _fail(exc)
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
        return _fail(exc, root=args.root, mode=args.mode)
    print(json.dumps(session.to_payload(), ensure_ascii=False))
    return 0


def plan_preview(args: argparse.Namespace) -> int:
    try:
        payload = read_plan_preview_payload(args.payload)
        result = create_plan_preview(payload, ttl=args.ttl, mode=args.mode)
    except (OSError, PreviewConfigurationError, PlanPreviewError) as exc:
        return _fail(exc)
    print(json.dumps(result.to_payload(), ensure_ascii=False))
    return 0


def plan_preview_stop(args: argparse.Namespace) -> int:
    try:
        result = stop_plan_preview(Path(args.root), pid=args.pid)
    except (OSError, PlanPreviewError) as exc:
        return _fail(exc, root=args.root)
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
        return _fail(exc)
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
        return _fail(exc)
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
    from scripts.html_review_workbench.watch_comments import post_event

    url = active_session_base_url(root)
    if url is None:
        return
    try:
        post_event(
            url,
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
    root = Path(args.root).resolve()
    url = args.url
    if not url:
        url = active_session_base_url(root)
        if url is None:
            print(json.dumps({"status": "failed", "error": "no active preview session found"}, ensure_ascii=False))
            return 2
    return run_watch(url, root=root)


def notify_update(args: argparse.Namespace) -> int:
    from scripts.html_review_workbench.watch_comments import send_notify
    root = Path(args.root).resolve()
    url = args.url
    if not url:
        url = active_session_base_url(root)
        if url is None:
            print(json.dumps({"status": "failed", "error": "no active preview session found"}, ensure_ascii=False))
        return 2
    return send_notify(url, message=args.message)


@dataclass(frozen=True)
class _CommandArg:
    flag: str
    required: bool = False
    kwargs: dict[str, object] | None = None


@dataclass(frozen=True)
class _CommandSpec:
    name: str
    purpose: str
    args: tuple[_CommandArg, ...]
    handler: Callable[[argparse.Namespace], int]


def _build_command_contract(specs: tuple[_CommandSpec, ...]) -> dict[str, dict[str, str | tuple[str, ...]]]:
    contract: dict[str, dict[str, str | tuple[str, ...]]] = {}
    for spec in specs:
        command: dict[str, str | tuple[str, ...]] = {
            "purpose": spec.purpose,
            "required_options": tuple(arg.flag for arg in spec.args if arg.required),
        }
        optional_options = tuple(arg.flag for arg in spec.args if not arg.required)
        if optional_options:
            command["optional_options"] = optional_options
        contract[spec.name] = command
    return contract


_COMMAND_SPECS: tuple[_CommandSpec, ...] = (
    _CommandSpec(
        "build-model",
        "Build a document model from natural content.",
        (
            _CommandArg("--text"),
            _CommandArg("--input"),
            _CommandArg("--output", required=True),
            _CommandArg("--title"),
            _CommandArg("--document-id"),
        ),
        build_model,
    ),
    _CommandSpec(
        "render",
        "Generate an HTML bundle from a document model.",
        (
            _CommandArg("--model", required=True),
            _CommandArg("--output", required=True),
        ),
        render,
    ),
    _CommandSpec(
        "check-model",
        "Check whether a document model is ready for final HTML rendering.",
        (_CommandArg("--model", required=True),),
        check_model,
    ),
    _CommandSpec(
        "attach-image",
        "Attach a generated image asset to an image-capable block in a document model.",
        (
            _CommandArg("--model", required=True),
            _CommandArg("--block-id", required=True),
            _CommandArg("--image", required=True),
            _CommandArg("--output"),
        ),
        attach_image,
    ),
    _CommandSpec(
        "preview",
        "Start or describe a session-scoped preview runtime.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--mode", kwargs={"choices": ["auto", "tailscale", "local", "off"], "default": "auto"}),
            _CommandArg("--owner-session"),
            _CommandArg("--owner-pid", kwargs={"type": int}),
            _CommandArg(
                "--idle-timeout",
                kwargs={"type": float, "default": DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS},
            ),
            _CommandArg("--owner-grace", kwargs={"type": float, "default": 300.0}),
        ),
        preview,
    ),
    _CommandSpec(
        "plan-preview",
        "Create an ephemeral localhost preview for a proposed plan.",
        (
            _CommandArg("--payload", kwargs={"default": "-"}),
            _CommandArg("--ttl", kwargs={"type": float, "default": 1800.0}),
            _CommandArg("--mode", kwargs={"choices": ["auto", "tailscale", "local"], "default": "auto"}),
        ),
        plan_preview,
    ),
    _CommandSpec(
        "plan-preview-stop",
        "Stop and clean up an ephemeral plan preview.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--pid", kwargs={"type": int}),
        ),
        plan_preview_stop,
    ),
    _CommandSpec(
        "ingest-review",
        "Read review comments, classify them, and save review-cycle state.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--comments", kwargs={"default": "annotations/comments.json"}),
            _CommandArg("--state", kwargs={"default": "annotations/review-cycle-state.json"}),
            _CommandArg("--model"),
            _CommandArg("--apply-model", kwargs={"action": "store_true"}),
        ),
        ingest_review,
    ),
    _CommandSpec(
        "validate",
        "Validate a generated HTML bundle.",
        (_CommandArg("--root", required=True),),
        validate,
    ),
    _CommandSpec(
        "add-reply",
        "Add an agent reply to a comment thread in comments.json.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--thread-id", required=True),
            _CommandArg("--body", required=True),
            _CommandArg("--comments", kwargs={"default": "annotations/comments.json"}),
            _CommandArg("--kind", kwargs={"default": "answer"}),
            _CommandArg("--author", kwargs={"default": "agent"}),
        ),
        add_reply,
    ),
    _CommandSpec(
        "check-gates",
        "Check whether the resolution gate is open or blocked by unresolved clarification threads.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--comments", kwargs={"default": "annotations/comments.json"}),
            _CommandArg("--state", kwargs={"default": "annotations/review-cycle-state.json"}),
        ),
        check_gates,
    ),
    _CommandSpec(
        "watch-comments",
        "Stream comment change events from a running preview server via SSE.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--url"),
        ),
        watch_comments,
    ),
    _CommandSpec(
        "notify-update",
        "Notify the preview server that the document has been updated.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--url"),
            _CommandArg("--message", kwargs={"default": ""}),
        ),
        notify_update,
    ),
    _CommandSpec(
        "publish",
        "Create a clean standalone HTML from a rendered bundle with review UI stripped.",
        (
            _CommandArg("--root", required=True),
            _CommandArg("--output"),
        ),
        publish,
    ),
)


COMMAND_CONTRACT = _build_command_contract(_COMMAND_SPECS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="html-review-workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for spec in _COMMAND_SPECS:
        command_parser = subparsers.add_parser(
            spec.name,
            help=spec.purpose,
            description=spec.purpose,
        )
        for arg in spec.args:
            command_parser.add_argument(arg.flag, required=arg.required, **(arg.kwargs or {}))
        command_parser.set_defaults(func=spec.handler)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
