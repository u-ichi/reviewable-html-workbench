"""Validate generated HTML bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scripts.html_review_workbench.schema_validation import validate


ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_MODEL_SCHEMA_PATH = ROOT / "schemas" / "document-model.schema.json"
COMMENTS_SCHEMA_PATH = ROOT / "schemas" / "comments.schema.json"


@dataclass(frozen=True)
class BundleValidationResult:
    ok: bool
    errors: list[str]
    review_blocks: int

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "review_blocks": self.review_blocks,
        }


def validate_bundle(root: Path) -> BundleValidationResult:
    errors: list[str] = []
    index_path = root / "index.html"
    manifest_path = root / "renderer-manifest.json"

    if not index_path.is_file():
        errors.append("missing index.html")
    if not manifest_path.is_file():
        errors.append("missing renderer-manifest.json")

    html = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    manifest = _read_manifest(manifest_path, errors)
    review_block_count = html.count("data-review-block=")
    if review_block_count == 0:
        errors.append("index.html has no data-review-block attributes")

    if isinstance(manifest, dict):
        _validate_manifest(manifest, root, html, errors)
        _validate_input_model(manifest, errors)

    comments_path = root / "annotations" / "comments.json"
    if comments_path.is_file():
        _validate_json_schema(comments_path, COMMENTS_SCHEMA_PATH, "comments.json", errors)

    return BundleValidationResult(
        ok=not errors,
        errors=errors,
        review_blocks=review_block_count,
    )


def _read_manifest(path: Path, errors: list[str]) -> object:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"renderer-manifest.json is invalid JSON: {exc}")
        return None


def _validate_manifest(manifest: dict[str, object], root: Path, html: str, errors: list[str]) -> None:
    for key in ["schema_version", "renderer_version", "generated_at", "input", "outputs", "review_blocks"]:
        if key not in manifest:
            errors.append(f"manifest missing {key}")

    outputs = manifest.get("outputs")
    if isinstance(outputs, dict):
        index = outputs.get("index")
        if index != "index.html":
            errors.append("manifest outputs.index must be index.html")
        assets = outputs.get("assets")
        if isinstance(assets, list):
            for asset in assets:
                if isinstance(asset, str) and not (root / asset).is_file():
                    errors.append(f"manifest asset missing: {asset}")
        else:
            errors.append("manifest outputs.assets must be a list")
        diagrams = outputs.get("diagrams", [])
        if isinstance(diagrams, list):
            for diagram in diagrams:
                if not isinstance(diagram, str):
                    continue
                diagram_path = root / diagram
                if not diagram_path.is_file():
                    errors.append(f"manifest diagram missing: {diagram}")
                elif not diagram_path.read_text(encoding="utf-8").strip():
                    errors.append(f"manifest diagram is empty: {diagram}")
        else:
            errors.append("manifest outputs.diagrams must be a list")
        images = outputs.get("images", [])
        if isinstance(images, list):
            for image in images:
                if not isinstance(image, str):
                    continue
                image_path = root / image
                if not image_path.is_file():
                    errors.append(f"manifest image missing: {image}")
                elif image_path.stat().st_size == 0:
                    errors.append(f"manifest image is empty: {image}")
                elif f'src="{image}"' not in html:
                    errors.append(f"manifest image not referenced from HTML: {image}")
        else:
            errors.append("manifest outputs.images must be a list")

    review_blocks = manifest.get("review_blocks")
    if not isinstance(review_blocks, list) or not review_blocks:
        errors.append("manifest review_blocks must be a non-empty list")
        return

    for block in review_blocks:
        if not isinstance(block, dict):
            errors.append("manifest review_blocks entries must be objects")
            continue
        block_id = block.get("id")
        if not isinstance(block_id, str) or not block_id:
            errors.append("manifest review block missing id")
            continue
        if f'data-review-block="{block_id}"' not in html:
            errors.append(f"review block missing from HTML: {block_id}")


def _validate_input_model(manifest: dict[str, object], errors: list[str]) -> None:
    input_info = manifest.get("input")
    if not isinstance(input_info, dict) or not isinstance(input_info.get("path"), str):
        return
    model_path = Path(input_info["path"])
    if model_path.is_file():
        _validate_json_schema(model_path, DOCUMENT_MODEL_SCHEMA_PATH, "document model", errors)


def _validate_json_schema(path: Path, schema_path: Path, label: str, errors: list[str]) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is invalid JSON: {exc}")
        return
    for error in validate(payload, schema):
        errors.append(f"{label} schema error at {error.path}: {error.message}")
