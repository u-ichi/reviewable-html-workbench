from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "bin" / "kill-review-preview.sh"


class KillReviewPreviewHelperTest(unittest.TestCase):
    def test_helper_is_executable(self) -> None:
        self.assertTrue(HELPER.exists())
        self.assertTrue(os.access(HELPER, os.X_OK))

    def test_refuses_without_explicit_pid(self) -> None:
        result = subprocess.run(
            [str(HELPER), "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Pass an explicit PID", result.stderr)

    def test_dry_run_accepts_only_review_preview_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_ps = _write_fake_ps(Path(tmp))
            result = subprocess.run(
                [str(HELPER), "--dry-run", "12345"],
                cwd=ROOT,
                env={**os.environ, "REVIEW_PREVIEW_PS": str(fake_ps)},
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("Would stop review preview process: 12345", result.stdout)

    def test_refuses_non_review_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_ps = _write_fake_ps(Path(tmp))
            result = subprocess.run(
                [str(HELPER), "--dry-run", "99999"],
                cwd=ROOT,
                env={**os.environ, "REVIEW_PREVIEW_PS": str(fake_ps)},
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Refusing to stop non-review preview process", result.stderr)


def _write_fake_ps(root: Path) -> Path:
    path = root / "fake-ps"
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ "$1" == "-p" ]]; then
  case "$2" in
    12345)
      echo "python3 -m scripts.html_review_workbench.preview_server --serve 54321 --bind 127.0.0.1 /tmp/review"
      ;;
    99999)
      echo "python3 -m http.server 8000"
      ;;
    *)
      exit 1
      ;;
  esac
elif [[ "$1" == "-axo" ]]; then
  echo " 12345 python3 -m scripts.html_review_workbench.preview_server --serve 54321 --bind 127.0.0.1 /tmp/review"
else
  exit 1
fi
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


if __name__ == "__main__":
    unittest.main()
