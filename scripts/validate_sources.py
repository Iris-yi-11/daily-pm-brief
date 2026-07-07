#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pm_brief.config import load_config, load_sources, resolve_config_path
from pm_brief.health import load_source_health, merge_source_health, validate_sources, write_source_health


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate configured RSS sources and update source health.")
    parser.add_argument("--config", default="config/sources.json", help="Path to source config JSON.")
    parser.add_argument("--health", help="Path to source health JSON. Defaults to config source_health_path.")
    parser.add_argument("--timeout", type=int, help="Per-source timeout in seconds. Defaults to config fetch_timeout_seconds.")
    parser.add_argument("--max-workers", type=int, help="Concurrent source checks. Defaults to config max_fetch_workers.")
    parser.add_argument("--failure-threshold", type=int, help="Consecutive failures before unstable. Defaults to config source_failure_threshold.")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    health_path = Path(args.health) if args.health else resolve_config_path(config_path, config.get("source_health_path", "data/source_health.json"))
    timeout = args.timeout or int(config.get("fetch_timeout_seconds", 6))
    max_workers = args.max_workers or int(config.get("max_fetch_workers", 12))
    failure_threshold = args.failure_threshold or int(config.get("source_failure_threshold", 3))

    sources = load_sources(config)
    existing = load_source_health(health_path)
    results = validate_sources(sources, timeout=timeout, max_workers=max_workers)
    ok_count = sum(1 for result in results if result["ok"])
    failed = [result for result in results if not result["ok"]]
    global_network_failure = bool(results) and ok_count == 0 and _looks_like_global_network_failure(failed)
    if global_network_failure:
        health = existing
    else:
        health = merge_source_health(existing, results, failure_threshold=failure_threshold)
        write_source_health(health_path, health)
    unstable_count = sum(1 for entry in health.values() if entry.get("status") == "unstable")

    print(f"Checked sources: {len(results)}")
    print(f"Healthy this run: {ok_count}")
    print(f"Failed this run: {len(failed)}")
    print(f"Unstable total: {unstable_count}")
    print(f"Health file: {health_path}")
    if global_network_failure:
        print("Global network failure suspected; source health file was not updated.")
    if failed:
        print("Failed sources:")
        for result in failed:
            print(f"- {result['name']}: {result['error']}")
    return 0 if ok_count else 1


def _looks_like_global_network_failure(failed: list[dict]) -> bool:
    if not failed:
        return False
    transient_markers = (
        "nodename nor servname provided",
        "name or service not known",
        "temporary failure in name resolution",
        "could not resolve host",
        "network is unreachable",
        "curl fallback failed",
    )
    errors = [str(result.get("error", "")).lower() for result in failed]
    return all(any(marker in error for marker in transient_markers) for error in errors)


if __name__ == "__main__":
    raise SystemExit(main())
