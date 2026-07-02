from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = (
    "md-file-prohibition",
    "repo-root-resolution",
    "preview-owner-pid-note",
    "tailscale-sandbox-fallback",
    "cli-commands-core",
    "mermaid-kinds",
)
SKILL_PATHS = (
    ROOT / "skills/visual-html-renderer/SKILL.md",
    ROOT / "skills/reviewable-design-doc/SKILL.md",
)


class SkillDocsGenerationTest(unittest.TestCase):
    def test_each_fragment_has_ja_and_en_files(self) -> None:
        for name in FRAGMENTS:
            self.assertTrue((ROOT / "docs/skill-fragments" / f"{name}.ja.md").is_file())
            self.assertTrue((ROOT / "docs/skill-fragments" / f"{name}.en.md").is_file())

    def test_ja_fragments_are_nonempty(self) -> None:
        for name in FRAGMENTS:
            text = (ROOT / "docs/skill-fragments" / f"{name}.ja.md").read_text(encoding="utf-8")
            self.assertTrue(text.strip(), f"{name}.ja.md must contain shared text")

    def test_en_fragments_are_present_but_may_be_empty(self) -> None:
        for name in FRAGMENTS:
            self.assertTrue((ROOT / "docs/skill-fragments" / f"{name}.en.md").is_file())

    def test_generator_check_detects_no_drift(self) -> None:
        subprocess.run(
            [sys.executable, "scripts/build_skill_docs.py", "--check"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_generator_rewrite_is_idempotent(self) -> None:
        before = {path: path.read_text(encoding="utf-8") for path in SKILL_PATHS}
        subprocess.run([sys.executable, "scripts/build_skill_docs.py"], cwd=ROOT, check=True)
        after = {path: path.read_text(encoding="utf-8") for path in SKILL_PATHS}
        self.assertEqual(before, after)

    def test_shared_markers_cover_expected_fragments(self) -> None:
        for path in SKILL_PATHS:
            text = path.read_text(encoding="utf-8")
            for name in FRAGMENTS:
                self.assertIn(f"<!-- BEGIN SHARED: {name} -->", text)
                self.assertIn(f"<!-- END SHARED: {name} -->", text)

    def test_generator_preserves_non_shared_regions(self) -> None:
        before = {path: _without_shared_regions(path.read_text(encoding="utf-8")) for path in SKILL_PATHS}
        subprocess.run([sys.executable, "scripts/build_skill_docs.py"], cwd=ROOT, check=True)
        after = {path: _without_shared_regions(path.read_text(encoding="utf-8")) for path in SKILL_PATHS}
        self.assertEqual(before, after)

    def test_generated_skills_still_satisfy_codex_integration_pins(self) -> None:
        subprocess.run([sys.executable, "scripts/build_skill_docs.py"], cwd=ROOT, check=True)
        visual = (ROOT / "skills/visual-html-renderer/SKILL.md").read_text(encoding="utf-8")
        reviewable = (ROOT / "skills/reviewable-design-doc/SKILL.md").read_text(encoding="utf-8")

        for needle in (
            "使用しない場面",
            "python3 -m scripts.html_review_workbench.cli build-model",
            "python3 -m scripts.html_review_workbench.cli attach-image",
            "python3 -m scripts.html_review_workbench.cli check-model",
            "python3 -m scripts.html_review_workbench.cli render",
            "python3 -m scripts.html_review_workbench.cli validate",
            "python3 -m scripts.html_review_workbench.cli preview",
            "renderer repo root",
            "24時間アクセスが無い場合",
            "--owner-pid",
            "`build-model` は最終HTMLモデルを作るplannerではない",
        ):
            self.assertIn(needle, visual)

        self.assertLess(visual.index("cli attach-image"), visual.index("cli check-model"))
        self.assertLess(visual.index("cli check-model"), visual.index("cli render"))
        self.assertLess(visual.index("cli render"), visual.index("cli validate"))
        self.assertLess(visual.index("cli validate"), visual.index("cli preview"))

        for needle in (
            "使用しない場面",
            "python3 -m scripts.html_review_workbench.cli build-model",
            "python3 -m scripts.html_review_workbench.cli attach-image",
            "python3 -m scripts.html_review_workbench.cli check-model",
            "python3 -m scripts.html_review_workbench.cli render",
            "python3 -m scripts.html_review_workbench.cli validate",
            "python3 -m scripts.html_review_workbench.cli preview",
            "renderer repo root",
            "24時間アクセスが無い場合",
            "--owner-pid",
            "source-capture draft",
        ):
            self.assertIn(needle, reviewable)

        self.assertLess(reviewable.index("cli attach-image"), reviewable.index("cli check-model"))
        self.assertLess(reviewable.index("cli check-model"), reviewable.index("cli render"))
        self.assertLess(reviewable.index("cli render"), reviewable.index("cli validate"))
        self.assertLess(reviewable.index("cli validate"), reviewable.index("cli preview"))

    def test_shared_marker_free_diff_matches_baseline(self) -> None:
        for path in SKILL_PATHS:
            relative = path.relative_to(ROOT).as_posix()
            baseline = subprocess.check_output(
                ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
            ).decode("utf-8")
            current = path.read_text(encoding="utf-8")
            self.assertEqual(_without_shared_marker_lines(baseline), _without_shared_marker_lines(current))


def _without_shared_regions(text: str) -> str:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    in_shared = False
    for line in lines:
        if line.startswith("<!-- BEGIN SHARED: "):
            in_shared = True
            output.append(line)
            continue
        if line.startswith("<!-- END SHARED: "):
            in_shared = False
            output.append(line)
            continue
        if not in_shared:
            output.append(line)
    return "".join(output)


def _without_shared_marker_lines(text: str) -> str:
    return "".join(
        line
        for line in text.splitlines(keepends=True)
        if not line.startswith("<!-- BEGIN SHARED: ") and not line.startswith("<!-- END SHARED: ")
    )


if __name__ == "__main__":
    unittest.main()
