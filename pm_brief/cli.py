import argparse
import re
from datetime import date
from pathlib import Path

from pm_brief.build import generate_brief
from pm_brief.candidates import load_candidate_articles


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Daily PM Growth Brief.")
    parser.add_argument("--config", default="config/sources.json", help="Path to source config JSON.")
    parser.add_argument("--output-dir", default="reports", help="Directory for Markdown reports.")
    parser.add_argument("--archive", default="data/archive.jsonl", help="Path to archive JSONL.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Brief date, YYYY-MM-DD.")
    parser.add_argument("--candidates-file", help="Optional JSON file with web-researched candidate articles.")
    parser.add_argument(
        "--fail-on-insufficient",
        action="store_true",
        help="Exit non-zero when the run preserved an old report or produced too little fresh content.",
    )
    parser.add_argument("--min-candidates", type=int, default=20, help="Minimum fresh candidates for a healthy run.")
    parser.add_argument("--min-must-reads", type=int, default=2, help="Minimum Must Read items for a healthy run.")
    parser.add_argument("--min-ai-watch", type=int, default=2, help="Minimum AI Product Watch items for a healthy run.")
    parser.add_argument("--min-marketplace", type=int, default=2, help="Minimum Marketplace items for a healthy run.")
    args = parser.parse_args()

    candidate_articles = load_candidate_articles(Path(args.candidates_file)) if args.candidates_file else []
    output_path = generate_brief(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir),
        archive_path=Path(args.archive),
        brief_date=date.fromisoformat(args.date),
        candidate_articles=candidate_articles,
    )
    print(output_path)
    if args.fail_on_insufficient:
        status = _read_status(Path(args.output_dir) / "status.md")
        preserved = status.get("Preserved existing report", "").lower() == "true"
        candidate_count = int(status.get("Candidate count", "0") or 0)
        must_read_count = int(status.get("Must Read count", "0") or 0)
        ai_watch_count = int(status.get("AI Product Watch count", "0") or 0)
        marketplace_count = int(status.get("Marketplace count", "0") or 0)
        if (
            preserved
            or candidate_count < args.min_candidates
            or must_read_count < args.min_must_reads
            or ai_watch_count < args.min_ai_watch
            or marketplace_count < args.min_marketplace
        ):
            print(
                "Insufficient fresh brief: "
                f"preserved={preserved}, candidates={candidate_count}, must_reads={must_read_count}, "
                f"ai_watch={ai_watch_count}, marketplace={marketplace_count}"
            )
            return 2
    return 0


def _read_status(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    status = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"- ([^:]+):\s*(.*)", line)
        if match:
            status[match.group(1)] = match.group(2)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
