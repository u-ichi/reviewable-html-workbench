from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CodexSkillIntegrationTest(unittest.TestCase):
    def test_skill_docs_pin_cli_workflows(self) -> None:
        visual = (ROOT / "skills/visual-html-renderer/SKILL.md").read_text(encoding="utf-8")
        reviewable = (ROOT / "skills/reviewable-design-doc/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("python3 -m scripts.html_review_workbench.cli build-model", visual)
        self.assertIn("python3 -m scripts.html_review_workbench.cli attach-image", visual)
        self.assertIn("python3 -m scripts.html_review_workbench.cli check-model", visual)
        self.assertIn("python3 -m scripts.html_review_workbench.cli render", visual)
        self.assertIn("python3 -m scripts.html_review_workbench.cli validate", visual)
        self.assertIn("python3 -m scripts.html_review_workbench.cli preview", visual)
        self.assertIn("renderer repo root", visual)
        self.assertIn("作業ディレクトリにして実行する", visual)
        self.assertIn("現在のチャットやworkspaceのcwdをrepo rootとして扱わない", visual)
        self.assertIn("代替HTMLを作らず", visual)
        self.assertIn("source-capture draft", visual)
        self.assertLess(visual.index("cli attach-image"), visual.index("cli check-model"))
        self.assertLess(visual.index("cli check-model"), visual.index("cli render"))
        self.assertLess(visual.index("cli attach-image"), visual.index("cli render"))
        self.assertLess(visual.index("cli render"), visual.index("cli validate"))
        self.assertLess(visual.index("cli validate"), visual.index("cli preview"))

        self.assertIn("python3 -m scripts.html_review_workbench.cli render", reviewable)
        self.assertIn("python3 -m scripts.html_review_workbench.cli attach-image", reviewable)
        self.assertIn("python3 -m scripts.html_review_workbench.cli check-model", reviewable)
        self.assertIn("python3 -m scripts.html_review_workbench.cli validate", reviewable)
        self.assertIn("python3 -m scripts.html_review_workbench.cli preview", reviewable)
        self.assertIn("python3 -m scripts.html_review_workbench.cli ingest-review", reviewable)
        self.assertIn("renderer repo root", reviewable)
        self.assertIn("作業ディレクトリにして実行する", reviewable)
        self.assertIn("現在のチャットやworkspaceのcwdをrepo rootとして扱わない", reviewable)
        self.assertIn("代替HTMLを作らず", reviewable)
        self.assertIn("source-capture draft", reviewable)
        self.assertLess(reviewable.index("cli attach-image"), reviewable.index("cli check-model"))
        self.assertLess(reviewable.index("cli check-model"), reviewable.index("cli render"))
        self.assertLess(reviewable.index("cli attach-image"), reviewable.index("cli render"))
        self.assertLess(reviewable.index("cli render"), reviewable.index("cli validate"))
        self.assertLess(reviewable.index("cli validate"), reviewable.index("cli preview"))
        self.assertLess(reviewable.index("cli preview"), reviewable.index("cli ingest-review"))

    def test_openai_metadata_matches_skill_docs(self) -> None:
        visual = _read_simple_yaml(ROOT / "skills/visual-html-renderer/agents/openai.yaml")
        reviewable = _read_simple_yaml(ROOT / "skills/reviewable-design-doc/agents/openai.yaml")

        self.assertEqual(visual["entrypoint"], "python3 -m scripts.html_review_workbench.cli")
        self.assertEqual(visual["working_directory"], "plugin_root")
        self.assertEqual(visual["workflow"], ["attach-image", "check-model", "render", "validate", "preview"])
        self.assertIn("html出力して", visual["trigger_examples"])
        self.assertIn("HTMLにして", visual["trigger_examples"])
        self.assertIn("HTMLで出して", visual["trigger_examples"])
        self.assertIn("図示つきHTML", visual["trigger_examples"])

        self.assertEqual(reviewable["entrypoint"], "python3 -m scripts.html_review_workbench.cli")
        self.assertEqual(reviewable["working_directory"], "plugin_root")
        self.assertEqual(reviewable["workflow"], ["attach-image", "check-model", "render", "validate", "preview", "ingest-review"])
        self.assertIn("コメントを反映して", reviewable["trigger_examples"])

    def test_visual_skill_handles_natural_html_output_request_without_model_argument(self) -> None:
        visual = (ROOT / "skills/visual-html-renderer/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("html出力して", visual)
        self.assertIn("文書モデルが未指定の場合", visual)
        self.assertIn("HTML情報設計", visual)
        self.assertIn("HTML表現設計フェーズ", visual)
        self.assertIn("rendererブロック対応表", visual)
        self.assertIn("一時入力ファイルが必要な場合も `.md` は使わない", visual)
        self.assertIn("`build-model` は最終HTMLモデルを作るplannerではない", visual)
        self.assertIn("`section` / `text` / `table`", visual)
        self.assertIn("attach-image", visual)
        self.assertIn("render` → `validate` → `preview", visual)
        self.assertIn("返却JSONの `url`", visual)
        self.assertNotIn("--owner-pid $$", visual)

    def test_reviewable_design_doc_builds_model_and_reports_preview_url(self) -> None:
        reviewable = (ROOT / "skills/reviewable-design-doc/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("最初から `document-model.json` を作る", reviewable)
        self.assertIn("`.md` を作らない", reviewable)
        self.assertIn("`.md` 原稿をHTMLへ変換する作業ではない", reviewable)
        self.assertIn("現行rendererに専用描画がない", reviewable)
        self.assertIn("source-capture draft", reviewable)
        self.assertIn("返却JSONの `url`", reviewable)
        self.assertNotIn("--owner-pid $$", reviewable)

    def test_same_fixture_keeps_artifact_structure_across_skill_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            visual_output = tmp_dir / "visual"
            reviewable_output = tmp_dir / "reviewable"
            model = ROOT / "tests/fixtures/minimal_document_model.json"

            _run_cli("render", "--model", str(model), "--output", str(visual_output))
            _run_cli("validate", "--root", str(visual_output))
            _run_cli("preview", "--root", str(visual_output), "--mode", "off")

            _run_cli("render", "--model", str(model), "--output", str(reviewable_output))
            _run_cli("validate", "--root", str(reviewable_output))
            _run_cli("preview", "--root", str(reviewable_output), "--mode", "off")
            (reviewable_output / "annotations").mkdir()
            shutil.copyfile(
                ROOT / "tests/fixtures/minimal_comments.json",
                reviewable_output / "annotations/comments.json",
            )
            _run_cli("ingest-review", "--root", str(reviewable_output))

            self.assertEqual(_artifact_paths(visual_output), _artifact_paths(reviewable_output, ignore_annotations=True))
            state = json.loads((reviewable_output / "annotations/review-cycle-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["summary"]["total"], 1)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scripts.html_review_workbench.cli", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def _artifact_paths(root: Path, *, ignore_annotations: bool = False) -> list[str]:
    paths: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if ignore_annotations and relative.startswith("annotations/"):
            continue
        paths.append(relative)
    return sorted(paths)


def _read_simple_yaml(path: Path) -> dict[str, object]:
    result: dict[str, object] = {}
    current_list: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current_list:
            value = result[current_list]
            if not isinstance(value, list):
                raise AssertionError(f"expected list field: {current_list}")
            value.append(line[4:])
            continue
        current_list = None
        if line.endswith(":"):
            key = line[:-1]
            result[key] = []
            current_list = key
            continue
        key, value = line.split(": ", 1)
        result[key] = value
    return result


if __name__ == "__main__":
    unittest.main()
