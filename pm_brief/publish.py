import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Dict, Optional


def configure_lark_cli(app_id: str, app_secret: str, brand: str = "feishu") -> None:
    subprocess.run(
        ["lark-cli", "config", "init", "--app-id", app_id, "--app-secret-stdin", "--brand", brand],
        input=app_secret.encode("utf-8"),
        check=True,
    )


def fetch_document_markdown(doc_url: str, as_identity: str = "bot") -> str:
    result = subprocess.run(
        [
            "lark-cli",
            "docs",
            "+fetch",
            "--api-version",
            "v2",
            "--as",
            as_identity,
            "--doc",
            doc_url,
            "--doc-format",
            "markdown",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    return payload.get("data", {}).get("document", {}).get("content", "")


def document_has_brief_for_date(content: str, brief_date: date) -> bool:
    pattern = rf"(?m)^# Daily PM Growth Brief — {re.escape(brief_date.isoformat())}$"
    return re.search(pattern, content) is not None


def publish_markdown_file(
    doc_url: str,
    markdown_path: Path,
    as_identity: str = "bot",
    placement: str = "prepend",
    existing_content: Optional[str] = None,
) -> None:
    if placement not in {"prepend", "append"}:
        raise ValueError("placement must be 'prepend' or 'append'")
    command = "append"
    content_path = markdown_path
    if placement == "prepend":
        command = "overwrite"
        existing = existing_content if existing_content is not None else fetch_document_markdown(doc_url, as_identity=as_identity)
        content_path = prepare_prepend_file(markdown_path, existing)
    relative_path = content_path.relative_to(Path.cwd())
    subprocess.run(
        [
            "lark-cli",
            "docs",
            "+update",
            "--api-version",
            "v2",
            "--as",
            as_identity,
            "--doc",
            doc_url,
            "--command",
            command,
            "--doc-format",
            "markdown",
            "--content",
            f"@{relative_path.as_posix()}",
        ],
        check=True,
    )


def prepare_prepend_file(markdown_path: Path, existing_content: str) -> Path:
    target = markdown_path.parent / "_publish_prepend.md"
    new_content = _strip_leading_separator(markdown_path.read_text(encoding="utf-8").strip())
    existing = (existing_content or "").strip()
    parts = [new_content]
    if existing:
        parts.extend(["---", existing])
    target.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    return target


def _strip_leading_separator(content: str) -> str:
    lines = content.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].strip() == "---":
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def prepare_publish_file(report_path: Path, status: Dict[str, str], brief_date: date) -> Path:
    preserved = status.get("Preserved existing report", "").lower() == "true"
    fallback_mode = status.get("Fallback mode", "none")
    wrapper_path = report_path.parent / "_publish_today.md"
    if not preserved:
        wrapper_path.write_text("\n\n---\n\n" + report_path.read_text(encoding="utf-8").strip() + "\n", encoding="utf-8")
        return wrapper_path

    report_lines = report_path.read_text(encoding="utf-8").splitlines()
    while report_lines and not report_lines[0].strip():
        report_lines.pop(0)
    if report_lines and report_lines[0].startswith("# "):
        report_lines = report_lines[1:]
        while report_lines and not report_lines[0].strip():
            report_lines.pop(0)

    source_label = report_path.stem
    wrapper_path.write_text(
        "\n".join(
            [
                "",
                "",
                "---",
                "",
                f"# Daily PM Growth Brief — {brief_date.isoformat()}",
                "",
                f"> 说明：今日自动更新已执行，但本次运行走到了 `{fallback_mode}` 回退链路，当前保留上一份高质量简报（原始日期：{source_label}）。",
                "",
                *report_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return wrapper_path
