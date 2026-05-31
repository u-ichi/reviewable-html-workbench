"""Attach generated image assets to document models."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ImageAssetError(ValueError):
    """Raised when an image asset cannot be attached to a document model."""


@dataclass(frozen=True)
class ImageAttachmentResult:
    model_path: Path
    block_id: str
    source_path: str


def attach_image_to_model(
    *,
    model_path: Path,
    block_id: str,
    image_path: Path,
    output_path: Path | None = None,
) -> ImageAttachmentResult:
    if not image_path.is_file():
        raise ImageAssetError(f"image file not found: {image_path}")
    target_model_path = output_path or model_path
    model = json.loads(model_path.read_text(encoding="utf-8"))
    block = _find_image_block(model, block_id)

    model_assets_dir = target_model_path.parent / "assets" / "images"
    model_assets_dir.mkdir(parents=True, exist_ok=True)
    destination = _unique_asset_path(model_assets_dir / _asset_filename(block_id, image_path))
    shutil.copy2(image_path, destination)
    relative_source = destination.relative_to(target_model_path.parent).as_posix()

    image = block.setdefault("image", {})
    image["source_path"] = relative_source
    image["generation_status"] = "generated"
    image["generated_at"] = datetime.now(timezone.utc).isoformat()
    if "alt" not in image:
        image["alt"] = block.get("title") or block_id
    if "prompt" not in image:
        image["prompt"] = block.get("content") or block_id

    target_model_path.parent.mkdir(parents=True, exist_ok=True)
    target_model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ImageAttachmentResult(
        model_path=target_model_path,
        block_id=block_id,
        source_path=relative_source,
    )


def _find_image_block(model: dict[str, Any], block_id: str) -> dict[str, Any]:
    for block in model.get("blocks", []):
        if block.get("id") == block_id:
            if block.get("type") != "image":
                raise ImageAssetError(f"block is not an image block: {block_id}")
            return block
    raise ImageAssetError(f"image block not found: {block_id}")


def _asset_filename(block_id: str, image_path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", block_id).strip("-") or "generated-image"
    suffix = image_path.suffix.lower() or ".png"
    return f"{stem}{suffix}"


def _unique_asset_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ImageAssetError(f"could not choose unique image asset path for: {path}")
