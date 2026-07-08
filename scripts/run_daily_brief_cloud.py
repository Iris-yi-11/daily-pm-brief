#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pm_brief.publish import (
    configure_lark_cli,
    document_has_brief_for_date,
    fetch_document_markdown,
    prepare_publish_file,
    publish_markdown_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the daily PM brief in cloud CI and publish to Feishu.")
    parser.add_argument("--config", default="config/sources.json")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--archive", default="data/archive.jsonl")
    parser.add_argument("--doc-url", default=os.getenv("LARK_DOC_URL", ""))
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--skip-publish", action="store_true")
    args = parser.parse_args()

    brief_day = datetime.now(ZoneInfo(args.timezone)).date()
    brief_date = brief_day.isoformat()
    doc_url = args.doc_url
    app_id = os.getenv("LARK_APP_ID", "")
    app_secret = os.getenv("LARK_APP_SECRET", "")

    if not args.skip_publish:
        if not doc_url:
            raise SystemExit("LARK_DOC_URL is required unless --skip-publish is used.")
        if not app_id or not app_secret:
            raise SystemExit("LARK_APP_ID and LARK_APP_SECRET are required for Feishu publishing.")
        configure_lark_cli(app_id, app_secret)
        existing_content = _fetch_existing_content(doc_url, brief_day)
        if existing_content is not None and document_has_brief_for_date(existing_content, brief_day):
            print(f"Brief already published for {brief_date}; skipping generation.")
            return 0

    if not args.skip_validate:
        subprocess.run(
            [sys.executable, "scripts/validate_sources.py", "--config", args.config],
            cwd=PROJECT_ROOT,
            check=False,
        )

    generated = subprocess.run(
        [
            sys.executable,
            "-m",
            "pm_brief.cli",
            "--config",
            args.config,
            "--output-dir",
            args.output_dir,
            "--archive",
            args.archive,
            "--date",
            brief_date,
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report_path = _extract_report_path(generated.stdout)
    status = _read_status(PROJECT_ROOT / args.output_dir / "status.md")
    publish_path = prepare_publish_file(report_path, status, brief_day)

    if not args.skip_publish:
        publish_markdown_file(doc_url, publish_path)

    print(report_path)
    return 0


def _extract_report_path(stdout: str) -> Path:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError("pm_brief.cli did not print a report path")
    path = Path(lines[-1])
    return path if path.is_absolute() else (PROJECT_ROOT / path)


def _read_status(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    status = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            status[key.strip()] = value.strip()
    return status


def _fetch_existing_content(doc_url: str, brief_day) -> Optional[str]:
    try:
        return fetch_document_markdown(doc_url)
    except subprocess.CalledProcessError as exc:
        print(
            f"Warning: failed to fetch existing Feishu content before publishing {brief_day.isoformat()}: {exc}",
            file=sys.stderr,
        )
        return None


if __name__ == "__main__":
    raise SystemExit(main())
