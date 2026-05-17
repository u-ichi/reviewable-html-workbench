"""Validate generated HTML bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


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
                if isinstance(diagram, str) and not (root / diagram).is_file():
                    errors.append(f"manifest diagram missing: {diagram}")
        else:
            errors.append("manifest outputs.diagrams must be a list")

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
