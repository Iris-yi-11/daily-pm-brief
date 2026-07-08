import io
import unittest
from datetime import date
from unittest.mock import patch

from scripts import run_daily_brief_cloud


class RunDailyBriefCloudTests(unittest.TestCase):
    def test_fetch_existing_content_returns_none_on_fetch_failure(self):
        stderr = io.StringIO()
        with patch("scripts.run_daily_brief_cloud.fetch_document_markdown", side_effect=run_daily_brief_cloud.subprocess.CalledProcessError(1, ["lark-cli"])):
            with patch("sys.stderr", stderr):
                result = run_daily_brief_cloud._fetch_existing_content("https://example.com/wiki/abc", date(2026, 7, 8))

        self.assertIsNone(result)
        self.assertIn("failed to fetch existing Feishu content", stderr.getvalue())

    def test_main_skips_generation_when_today_already_published(self):
        with patch("scripts.run_daily_brief_cloud.configure_lark_cli") as configure:
            with patch("scripts.run_daily_brief_cloud._fetch_existing_content", return_value="# Daily PM Growth Brief — 2026-07-08\n"):
                with patch("scripts.run_daily_brief_cloud.document_has_brief_for_date", return_value=True):
                    with patch("scripts.run_daily_brief_cloud.subprocess.run") as run:
                        with patch("scripts.run_daily_brief_cloud.datetime") as fake_datetime:
                            fake_datetime.now.return_value.date.return_value = date(2026, 7, 8)
                            with patch(
                                "sys.argv",
                                [
                                    "run_daily_brief_cloud.py",
                                    "--doc-url",
                                    "https://example.com/wiki/abc",
                                ],
                            ):
                                with patch.dict(
                                    "os.environ",
                                    {"LARK_APP_ID": "cli_xxx", "LARK_APP_SECRET": "secret"},
                                    clear=False,
                                ):
                                    result = run_daily_brief_cloud.main()

        self.assertEqual(result, 0)
        configure.assert_called_once()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
