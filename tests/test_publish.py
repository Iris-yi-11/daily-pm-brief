import subprocess
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pm_brief.publish import (
    configure_lark_cli,
    document_has_brief_for_date,
    fetch_document_markdown,
    prepare_publish_file,
    publish_markdown_file,
)


class PublishTests(unittest.TestCase):
    def test_configure_lark_cli_uses_secret_stdin(self):
        with patch("pm_brief.publish.subprocess.run") as run:
            configure_lark_cli("cli_xxx", "secret-value")

        run.assert_called_once_with(
            ["lark-cli", "config", "init", "--app-id", "cli_xxx", "--app-secret-stdin", "--brand", "feishu"],
            input=b"secret-value",
            check=True,
        )

    def test_publish_markdown_file_uses_relative_content_path(self):
        with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            target = root / "report.md"
            target.write_text("# title", encoding="utf-8")
            with patch("pm_brief.publish.subprocess.run") as run:
                publish_markdown_file("https://example.com/wiki/abc", target)

        args = run.call_args.args[0]
        self.assertEqual(args[:6], ["lark-cli", "docs", "+update", "--api-version", "v2", "--as"])
        self.assertIn("append", args)
        self.assertIn(f"@{target.relative_to(Path.cwd()).as_posix()}", args)

    def test_fetch_document_markdown_reads_json_payload(self):
        payload = '{"data":{"document":{"content":"# Daily PM Growth Brief — 2026-07-08"}}}'
        with patch("pm_brief.publish.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=payload)
            content = fetch_document_markdown("https://example.com/wiki/abc")

        self.assertEqual(content, "# Daily PM Growth Brief — 2026-07-08")

    def test_document_has_brief_for_date_matches_heading(self):
        content = "# Daily PM Growth Brief — 2026-07-08\n\nBody"
        self.assertTrue(document_has_brief_for_date(content, date(2026, 7, 8)))
        self.assertFalse(document_has_brief_for_date(content, date(2026, 7, 7)))

    def test_prepare_publish_file_wraps_preserved_report(self):
        with TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "2026-07-05.md"
            report_path.write_text("# Daily PM Growth Brief — 2026-07-05\n\n## Section\n\nBody", encoding="utf-8")

            wrapped = prepare_publish_file(
                report_path,
                {"Preserved existing report": "True", "Fallback mode": "preserved"},
                date(2026, 7, 7),
            )

            content = wrapped.read_text(encoding="utf-8")
            self.assertEqual(wrapped.name, "_publish_today.md")
            self.assertIn("2026-07-07", content)
            self.assertIn("原始日期：2026-07-05", content)
            self.assertIn("## Section", content)

    def test_prepare_publish_file_keeps_report_when_not_preserved(self):
        with TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "2026-07-07.md"
            report_path.write_text("# Daily PM Growth Brief — 2026-07-07", encoding="utf-8")

            result = prepare_publish_file(report_path, {"Preserved existing report": "False"}, date(2026, 7, 7))

            self.assertEqual(result.name, "_publish_today.md")
            self.assertEqual(result.read_text(encoding="utf-8"), "\n\n---\n\n# Daily PM Growth Brief — 2026-07-07\n")


if __name__ == "__main__":
    unittest.main()
