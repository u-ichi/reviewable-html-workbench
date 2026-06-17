from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/plugin-dev-switch.sh"


class PluginDevSwitchTest(unittest.TestCase):
    def test_switch_operates_on_claude_and_codex_entries_together(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            claude_entry = _make_claude_cache(home)
            codex_entry = _make_codex_cache(home, "1.8.0")
            codex_dev_entry = _codex_dev_entry(home)
            codex_package_entry = _make_codex_cache(home, _codex_repo_version())

            result = _run(home, "dev")
            self.assertIn("claude: switched to dev", result.stdout)
            self.assertIn("codex: switched to dev", result.stdout)
            self.assertEqual(claude_entry.resolve(), ROOT)
            self.assertFalse(codex_entry.exists())
            self.assertTrue(codex_dev_entry.is_dir())
            self.assertEqual((codex_dev_entry / "skills").resolve(), ROOT / "skills")
            self.assertEqual(
                (codex_dev_entry / ".codex-plugin").resolve(),
                ROOT / ".codex-plugin",
            )
            self.assertEqual(
                (codex_dev_entry / ".rhw-plugin-dev-mode").read_text(encoding="utf-8").strip(),
                str(ROOT),
            )
            self.assertFalse((claude_entry.parent / "1.8.0.bak").exists())
            self.assertFalse((codex_entry.parent / "1.8.0.bak").exists())
            self.assertTrue(_backup_entry(home, "claude").is_dir())
            self.assertTrue(_backup_entry(home, "codex", "1.8.0").is_dir())
            self.assertTrue(_backup_entry(home, "codex", _codex_repo_version()).is_dir())

            result = _run(home, "status")
            self.assertIn("claude: dev", result.stdout)
            self.assertIn("codex: dev", result.stdout)

            result = _run(home, "package")
            self.assertIn("claude: switched to package", result.stdout)
            self.assertIn("codex: switched to package", result.stdout)
            self.assertTrue(claude_entry.is_dir())
            self.assertFalse(codex_entry.exists())
            self.assertTrue(codex_package_entry.is_dir())
            self.assertFalse(_backup_entry(home, "claude").exists())
            self.assertTrue(_backup_entry(home, "codex", "1.8.0").is_dir())
            self.assertFalse(_backup_entry(home, "codex", _codex_repo_version()).exists())

    def test_status_reports_missing_targets_without_switching_only_one_side(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _make_codex_cache(home, "1.8.0")

            result = _run(home, "status")
            self.assertIn("claude: not installed", result.stdout)
            self.assertIn("codex: package", result.stdout)

    def test_dev_fails_if_one_side_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _make_codex_cache(home, "1.8.0")

            result = _run(home, "dev", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("claude plugin", result.stderr)

    def test_status_migrates_legacy_bak_out_of_codex_version_scan_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex_entry = _make_codex_cache(home, "1.8.0")
            legacy = codex_entry.parent / "1.8.0.bak"
            codex_entry.rename(legacy)
            codex_entry.symlink_to(ROOT)

            result = _run(home, "status")
            self.assertIn("codex: stale dev", result.stdout)
            self.assertFalse(legacy.exists())
            self.assertTrue(_backup_entry(home, "codex", "1.8.0").is_dir())

    def test_codex_dev_runs_plugin_add_before_switching_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _make_claude_cache(home)
            _make_codex_cache(home, "1.8.0")
            bin_dir = home / "bin"
            bin_dir.mkdir()
            codex = bin_dir / "codex"
            log = home / "codex.log"
            codex.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$HOME/codex.log\"\n",
                encoding="utf-8",
            )
            codex.chmod(0o755)

            result = _run(home, "dev", skip_codex_add=False, path_prefix=bin_dir)

            self.assertIn("codex: switched to dev", result.stdout)
            self.assertIn(
                "plugin add reviewable-html-workbench@reviewable-html-workbench-local --json",
                log.read_text(encoding="utf-8"),
            )

    def test_codex_package_without_current_backup_runs_plugin_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _make_claude_cache(home)
            dev_entry = _codex_dev_entry(home)
            dev_entry.mkdir(parents=True)
            (dev_entry / ".rhw-plugin-dev-mode").write_text(str(ROOT) + "\n", encoding="utf-8")
            bin_dir = home / "bin"
            bin_dir.mkdir()
            codex = bin_dir / "codex"
            log = home / "codex.log"
            version = _codex_repo_version()
            codex.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$HOME/codex.log\"\n"
                f"mkdir -p \"$HOME/.codex/plugins/cache/reviewable-html-workbench-local/reviewable-html-workbench/{version}\"\n",
                encoding="utf-8",
            )
            codex.chmod(0o755)

            result = _run(home, "package", skip_codex_add=False, path_prefix=bin_dir)

            self.assertIn("codex: switched to package", result.stdout)
            self.assertTrue(dev_entry.is_dir())
            self.assertFalse((dev_entry / ".rhw-plugin-dev-mode").exists())
            self.assertIn(
                "plugin add reviewable-html-workbench@reviewable-html-workbench-local --json",
                log.read_text(encoding="utf-8"),
            )


def _make_claude_cache(home: Path) -> Path:
    entry = home / ".claude/plugins/cache/reviewable-html-workbench-local/reviewable-html-workbench/1.8.0"
    entry.mkdir(parents=True)
    (entry / "marker.txt").write_text("package\n", encoding="utf-8")
    installed = home / ".claude/plugins/installed_plugins.json"
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_text(
        json.dumps(
            {
                "plugins": {
                    "reviewable-html-workbench@reviewable-html-workbench-local": [
                        {"installPath": str(entry)}
                    ]
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return entry


def _make_codex_cache(home: Path, version: str) -> Path:
    entry = home / f".codex/plugins/cache/reviewable-html-workbench-local/reviewable-html-workbench/{version}"
    entry.mkdir(parents=True)
    (entry / "marker.txt").write_text("package\n", encoding="utf-8")
    return entry


def _backup_entry(home: Path, target: str, version: str = "1.8.0") -> Path:
    cache_root = home / f".{target}/plugins/cache/reviewable-html-workbench-local"
    return cache_root / f".rhw-plugin-dev-switch-backups/{target}/{version}"


def _codex_dev_entry(home: Path) -> Path:
    version = _codex_repo_version()
    return home / f".codex/plugins/cache/reviewable-html-workbench-local/reviewable-html-workbench/{version}"


def _codex_repo_version() -> str:
    return json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]


def _run(
    home: Path,
    *args: str,
    check: bool = True,
    skip_codex_add: bool = True,
    path_prefix: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    if skip_codex_add:
        env["RHW_PLUGIN_DEV_SWITCH_SKIP_CODEX_ADD"] = "1"
    else:
        env.pop("RHW_PLUGIN_DEV_SWITCH_SKIP_CODEX_ADD", None)
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


if __name__ == "__main__":
    unittest.main()
