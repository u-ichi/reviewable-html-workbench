"""render CLI のゲート警告テスト"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class TestRenderGateWarning(unittest.TestCase):
    def test_render_warns_on_blocked_gate(self) -> None:
        """render 後に blocked ゲートの警告が stderr に出力される"""
        from scripts.html_review_workbench.cli import _check_render_gate
        from scripts.html_review_workbench.resolution_gate import GateResult

        result = GateResult(
            gate="blocked",
            blocking_threads=[{"thread_id": "cmt_test1", "status": "needs_user_reply"}],
            resolved_actionable=[],
        )
        with patch("scripts.html_review_workbench.cli.try_check_gate", return_value=result):
            stderr = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = stderr
            try:
                _check_render_gate(Path("/tmp/test"))
            finally:
                sys.stderr = old_stderr
            self.assertIn("WARNING", stderr.getvalue())
            self.assertIn("cmt_test1", stderr.getvalue())

    def test_render_no_warning_on_open_gate(self) -> None:
        """ゲートが open の場合は警告なし"""
        from scripts.html_review_workbench.cli import _check_render_gate
        from scripts.html_review_workbench.resolution_gate import GateResult

        result = GateResult(gate="open", blocking_threads=[], resolved_actionable=[])
        with patch("scripts.html_review_workbench.cli.try_check_gate", return_value=result):
            stderr = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = stderr
            try:
                _check_render_gate(Path("/tmp/test"))
            finally:
                sys.stderr = old_stderr
            self.assertEqual("", stderr.getvalue())

    def test_render_no_warning_on_missing_comments(self) -> None:
        """コメントファイルが無い場合は警告なし"""
        from scripts.html_review_workbench.cli import _check_render_gate

        with patch("scripts.html_review_workbench.cli.try_check_gate", return_value=None):
            _check_render_gate(Path("/tmp/nonexistent"))


if __name__ == "__main__":
    unittest.main()
