from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.html_review_workbench import cli


ROOT = Path(__file__).resolve().parents[1]


class ProjectLayoutTest(unittest.TestCase):
    def test_plugin_manifests_exist_and_parse(self) -> None:
        for relative in [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]:
            path = ROOT / relative
            self.assertTrue(path.exists(), relative)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "reviewable-html-workbench")
            self.assertEqual(payload["skills"], "./skills/")

    def test_codex_manifest_documents_required_interface(self) -> None:
        payload = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for field in ["name", "version", "description", "author", "license", "keywords", "skills", "interface"]:
            self.assertIn(field, payload)

        interface = payload["interface"]
        for field in [
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "defaultPrompt",
            "brandColor",
        ]:
            self.assertIn(field, interface)

        self.assertTrue(interface["defaultPrompt"])
        self.assertIn("Write", interface["capabilities"])

    def test_required_skills_exist(self) -> None:
        for skill in ["visual-html-renderer", "reviewable-design-doc"]:
            path = ROOT / "skills" / skill / "SKILL.md"
            self.assertTrue(path.exists(), skill)
            text = path.read_text(encoding="utf-8")
            self.assertIn("description:", text)
            self.assertIn("Triggers:", text)
            self.assertIn("使用しない場面:", text)

    def test_cli_module_exists(self) -> None:
        self.assertTrue((ROOT / "scripts" / "html_review_workbench" / "cli.py").exists())

    def test_cli_subcommand_contract_is_stable(self) -> None:
        self.assertEqual(
            set(cli.COMMAND_CONTRACT),
            {"render", "preview", "ingest-review", "validate"},
        )
        self.assertEqual(cli.COMMAND_CONTRACT["render"]["required_options"], ("--model", "--output"))
        self.assertEqual(cli.COMMAND_CONTRACT["preview"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["ingest-review"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["validate"]["required_options"], ("--root",))

        help_text = cli.build_parser().format_help()
        for command in cli.COMMAND_CONTRACT:
            self.assertIn(command, help_text)


if __name__ == "__main__":
    unittest.main()
