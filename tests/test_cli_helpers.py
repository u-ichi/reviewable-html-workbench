from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


class CliHelpersTest(unittest.TestCase):
    def test_fail_preserves_status_error_extra_key_order(self) -> None:
        from scripts.html_review_workbench.cli import _fail

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = _fail(ValueError("bad config"), root="/tmp/root", mode="local")

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stdout.getvalue().strip(),
            '{"status": "failed", "error": "bad config", "root": "/tmp/root", "mode": "local"}',
        )

    def test_active_session_base_url_returns_none_for_malformed_manifest(self) -> None:
        from scripts.html_review_workbench.cli import active_session_base_url

        with patch(
            "scripts.html_review_workbench.preview_server.find_active_session",
            return_value={"bind": "127.0.0.1", "port": "8000"},
        ):
            self.assertIsNone(active_session_base_url(Path("/tmp/root")))

    def test_active_session_base_url_builds_http_url(self) -> None:
        from scripts.html_review_workbench.cli import active_session_base_url

        with patch(
            "scripts.html_review_workbench.preview_server.find_active_session",
            return_value={"bind": "127.0.0.1", "port": 8000},
        ):
            self.assertEqual(active_session_base_url(Path("/tmp/root")), "http://127.0.0.1:8000")

    def test_watch_comments_no_session_keeps_failed_json_shape(self) -> None:
        import argparse

        from scripts.html_review_workbench.cli import watch_comments

        stdout = io.StringIO()
        with patch("scripts.html_review_workbench.cli.active_session_base_url", return_value=None):
            with redirect_stdout(stdout):
                exit_code = watch_comments(argparse.Namespace(root="/tmp/root", url=None))

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"status": "failed", "error": "no active preview session found"},
        )


if __name__ == "__main__":
    unittest.main()
