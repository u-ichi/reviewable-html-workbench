from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectLayoutTest(unittest.TestCase):
    def test_plugin_manifests_exist_and_parse(self) -> None:
        for relative in [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]:
            path = ROOT / relative
            self.assertTrue(path.exists(), relative)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "reviewable-html-workbench")
            self.assertEqual(payload["skills"], "./skills/")

    def test_required_skills_exist(self) -> None:
        for skill in ["visual-html-renderer", "reviewable-design-doc"]:
            self.assertTrue((ROOT / "skills" / skill / "SKILL.md").exists(), skill)

    def test_cli_module_exists(self) -> None:
        self.assertTrue((ROOT / "scripts" / "html_review_workbench" / "cli.py").exists())


if __name__ == "__main__":
    unittest.main()
