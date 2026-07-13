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
    prepare_prepend_file,
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

    def test_publish_markdown_file_prepends_by_default(self):
        with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            target = root / "report.md"
            target.write_text("# Daily PM Growth Brief — 2026-07-09", encoding="utf-8")
            with patch("pm_brief.publish.subprocess.run") as run:
                publish_markdown_file("https://example.com/wiki/abc", target, existing_content="# Daily PM Growth Brief — 2026-07-08")

        args = run.call_args.args[0]
        self.assertEqual(args[:6], ["lark-cli", "docs", "+update", "--api-version", "v2", "--as"])
        self.assertIn("overwrite", args)
        self.assertIn(f"@{(target.parent / '_publish_prepend.md').relative_to(Path.cwd()).as_posix()}", args)

    def test_publish_markdown_file_can_append_when_requested(self):
        with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            target = root / "report.md"
            target.write_text("# title", encoding="utf-8")
            with patch("pm_brief.publish.subprocess.run") as run:
                publish_markdown_file("https://example.com/wiki/abc", target, placement="append")

        args = run.call_args.args[0]
        self.assertIn("append", args)
        self.assertIn(f"@{target.relative_to(Path.cwd()).as_posix()}", args)

    def test_prepare_prepend_file_places_new_brief_before_existing_content(self):
        with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            target = root / "report.md"
            target.write_text("\n\n---\n\n# Daily PM Growth Brief — 2026-07-09\n\nNew", encoding="utf-8")

            result = prepare_prepend_file(target, "# Daily PM Growth Brief — 2026-07-08\n\nOld")

            content = result.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# Daily PM Growth Brief — 2026-07-09"))
            self.assertLess(content.index("2026-07-09"), content.index("2026-07-08"))
            self.assertIn("---", content)

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
