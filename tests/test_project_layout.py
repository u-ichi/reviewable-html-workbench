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

    def test_codex_marketplace_entry_points_to_plugin_root(self) -> None:
        path = ROOT / ".agents" / "plugins" / "marketplace.json"
        self.assertTrue(path.exists())
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "reviewable-html-workbench-local")

        plugins = payload["plugins"]
        self.assertEqual(len(plugins), 1)
        plugin = plugins[0]
        self.assertEqual(plugin["name"], "reviewable-html-workbench")
        self.assertEqual(plugin["source"], {"source": "local", "path": "./plugins/reviewable-html-workbench"})
        self.assertEqual(plugin["policy"]["installation"], "INSTALLED_BY_DEFAULT")
        self.assertEqual(plugin["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(plugin["category"], "Productivity")

        plugin_link = ROOT / "plugins" / "reviewable-html-workbench"
        self.assertTrue(plugin_link.exists())
        self.assertEqual(plugin_link.resolve(), ROOT)

    def test_codex_manifest_documents_required_interface(self) -> None:
        payload = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for field in ["name", "version", "description", "author", "license", "keywords", "skills", "interface"]:
            self.assertIn(field, payload)
        self.assertEqual(payload["repository"], "https://github.com/u-ichi/reviewable-html-workbench")
        self.assertEqual(payload["homepage"], "https://github.com/u-ichi/reviewable-html-workbench")

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
        self.assertIn("Create a reviewable design doc in HTML", interface["defaultPrompt"])
        self.assertIn("Render this as a visual HTML report", interface["defaultPrompt"])
        self.assertIn("Preview this plan as HTML", interface["defaultPrompt"])

    def test_required_skills_exist(self) -> None:
        for skill in ["visual-html-renderer", "reviewable-design-doc", "plan-preview"]:
            path = ROOT / "skills" / skill / "SKILL.md"
            self.assertTrue(path.exists(), skill)
            text = path.read_text(encoding="utf-8")
            self.assertIn("description:", text)
            self.assertIn("Triggers:", text)
            self.assertIn("使用しない場面:", text)

    def test_review_preview_kill_helper_has_narrow_permission_allow(self) -> None:
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        allow = settings["permissions"]["allow"]

        self.assertIn("Bash(bin/kill-review-preview.sh)", allow)
        self.assertIn("Bash(bin/kill-review-preview.sh *)", allow)
        self.assertIn("Bash(./bin/kill-review-preview.sh)", allow)
        self.assertIn("Bash(./bin/kill-review-preview.sh *)", allow)
        self.assertNotIn("Bash(kill *)", allow)
        self.assertNotIn("Bash(pkill *)", allow)

    def test_cli_module_exists(self) -> None:
        self.assertTrue((ROOT / "scripts" / "html_review_workbench" / "cli.py").exists())

    def test_cli_subcommand_contract_is_stable(self) -> None:
        self.assertEqual(
            set(cli.COMMAND_CONTRACT),
            {
                "build-model",
                "attach-image",
                "render",
                "check-model",
                "preview",
                "plan-preview",
                "plan-preview-stop",
                "ingest-review",
                "add-reply",
                "validate",
                "check-gates",
                "watch-comments",
                "notify-update",
            },
        )
        self.assertEqual(cli.COMMAND_CONTRACT["build-model"]["required_options"], ("--output",))
        self.assertEqual(cli.COMMAND_CONTRACT["attach-image"]["required_options"], ("--model", "--block-id", "--image"))
        self.assertEqual(cli.COMMAND_CONTRACT["render"]["required_options"], ("--model", "--output"))
        self.assertEqual(cli.COMMAND_CONTRACT["check-model"]["required_options"], ("--model",))
        self.assertEqual(cli.COMMAND_CONTRACT["preview"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["plan-preview"]["required_options"], ())
        self.assertEqual(cli.COMMAND_CONTRACT["plan-preview"]["optional_options"], ("--payload", "--ttl", "--mode"))
        self.assertEqual(cli.COMMAND_CONTRACT["plan-preview-stop"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["ingest-review"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["add-reply"]["required_options"], ("--root", "--thread-id", "--body"))
        self.assertEqual(cli.COMMAND_CONTRACT["validate"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["check-gates"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["watch-comments"]["required_options"], ("--root",))
        self.assertEqual(cli.COMMAND_CONTRACT["notify-update"]["required_options"], ("--root",))

        help_text = cli.build_parser().format_help()
        for command in cli.COMMAND_CONTRACT:
            self.assertIn(command, help_text)


if __name__ == "__main__":
    unittest.main()
