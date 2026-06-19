"""Plan diagram source extraction for rendered HTML bundles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DIAGRAM_KINDS = frozenset({"flow", "sequence", "state", "architecture", "matrix", "timeline", "concept"})


@dataclass(frozen=True)
class PlannedDiagram:
    block_id: str
    kind: str
    source: str
    relative_path: str

    def to_manifest(self) -> dict[str, str]:
        return {
            "block_id": self.block_id,
            "kind": self.kind,
            "source": self.relative_path,
        }


def plan_diagrams(blocks: list[dict[str, Any]]) -> dict[str, PlannedDiagram]:
    plans: dict[str, PlannedDiagram] = {}
    for block in blocks:
        if not _is_diagram_candidate(block):
            continue
        block_id = str(block["id"])
        source = _diagram_source(block)
        if not source:
            continue
        relative_path = f"assets/diagrams/{_safe_filename(block_id)}.mmd"
        plans[block_id] = PlannedDiagram(
            block_id=block_id,
            kind=_classify_diagram(block, source),
            source=source,
            relative_path=relative_path,
        )
    return plans


def write_diagram_sources(output_dir: Path, diagrams: dict[str, PlannedDiagram]) -> list[str]:
    if not diagrams:
        return []

    written: list[str] = []
    for diagram in diagrams.values():
        path = output_dir / diagram.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(diagram.source.rstrip() + "\n", encoding="utf-8")
        written.append(diagram.relative_path)
    return written


def _is_diagram_candidate(block: dict[str, Any]) -> bool:
    return block.get("type") == "diagram" or isinstance(block.get("diagram_source"), str) or isinstance(block.get("diagram"), dict)


def _diagram_source(block: dict[str, Any]) -> str:
    diagram = block.get("diagram")
    if isinstance(diagram, dict) and isinstance(diagram.get("source"), str):
        return diagram["source"]
    source = block.get("diagram_source", block.get("content", ""))
    return source if isinstance(source, str) else ""


def _classify_diagram(block: dict[str, Any], source: str) -> str:
    explicit_kind = block.get("diagram_kind")
    if isinstance(explicit_kind, str) and explicit_kind in DIAGRAM_KINDS:
        return explicit_kind

    text = " ".join(
        part.lower()
        for part in [str(block.get("title", "")), str(block.get("content", "")), source]
        if part
    )
    if any(keyword in text for keyword in ["gantt", "timeline", "journey"]):
        return "timeline"
    if any(keyword in text for keyword in ["quadrantchart", "matrix", "table"]):
        return "matrix"
    if any(keyword in text for keyword in ["c4context", "erdiagram", "classdiagram", "architecture"]):
        return "architecture"
    if any(keyword in text for keyword in ["statediagram"]):
        return "state"
    if any(keyword in text for keyword in ["sequencediagram"]):
        return "sequence"
    if any(keyword in text for keyword in ["flowchart", "graph "]):
        return "flow"
    return "concept"


def _safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return slug or "diagram"
