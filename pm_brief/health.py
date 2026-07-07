import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from pm_brief.fetch import fetch_source
from pm_brief.models import Source


SourceHealth = Dict[str, dict]
UNSTABLE_SKIP_GRACE_DAYS = 3


def source_key(name: str, url: str) -> str:
    return f"{name}|{url}"


def load_source_health(path: Path) -> SourceHealth:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_source_health(path: Path, health: SourceHealth) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(health, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def validate_sources(
    sources: Iterable[Source],
    timeout: int = 6,
    max_workers: int = 12,
) -> List[dict]:
    source_list = list(sources)
    if not source_list:
        return []
    worker_count = max(1, min(max_workers, len(source_list)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(lambda source: validate_source(source, timeout=timeout), source_list))


def validate_source(source: Source, timeout: int = 6) -> dict:
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        articles = fetch_source(source, limit=1, timeout=timeout)
        return {
            "name": source.name,
            "url": source.url,
            "ok": bool(articles),
            "article_count": len(articles),
            "error": "" if articles else "no articles returned",
            "checked_at": checked_at,
        }
    except Exception as exc:
        return {
            "name": source.name,
            "url": source.url,
            "ok": False,
            "article_count": 0,
            "error": f"{exc.__class__.__name__}: {exc}",
            "checked_at": checked_at,
        }


def merge_source_health(existing: SourceHealth, results: Iterable[dict], failure_threshold: int = 3) -> SourceHealth:
    result_list = list(results)
    network_outage = _looks_like_network_outage(result_list)
    merged = dict(existing)
    for result in result_list:
        key = source_key(result["name"], result["url"])
        previous = dict(merged.get(key, {}))
        total_successes = int(previous.get("total_successes", 0))
        total_failures = int(previous.get("total_failures", 0))

        if result["ok"]:
            consecutive_failures = 0
            total_successes += 1
            status = "healthy"
            last_success_at = result["checked_at"]
            last_error = ""
        else:
            consecutive_failures = int(previous.get("consecutive_failures", 0))
            if not network_outage:
                consecutive_failures += 1
            total_failures += 1
            status = "unstable" if consecutive_failures >= failure_threshold else "degraded"
            last_success_at = previous.get("last_success_at")
            last_error = result.get("error", "")

        merged[key] = {
            "name": result["name"],
            "url": result["url"],
            "status": status,
            "consecutive_failures": consecutive_failures,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "last_checked_at": result["checked_at"],
            "last_success_at": last_success_at,
            "last_error": last_error,
            "last_article_count": result.get("article_count", 0),
        }
    return merged


def _looks_like_network_outage(results: List[dict]) -> bool:
    failures = [result for result in results if not result.get("ok")]
    if len(failures) < max(2, len(results) // 2 if results else 0):
        return False
    if any(result.get("ok") for result in results):
        return False
    return all(_is_name_resolution_error(result.get("error", "")) for result in failures)


def _is_name_resolution_error(error: str) -> bool:
    normalized = error.lower()
    return "nodename nor servname provided" in normalized or "temporary failure in name resolution" in normalized


def filter_sources_by_health(sources: Iterable[Source], health: SourceHealth, include_unstable: bool = False) -> List[Source]:
    filtered = []
    now = datetime.now(timezone.utc)
    for source in sources:
        entry = health.get(source_key(source.name, source.url), {})
        if (
            not include_unstable
            and entry.get("status") == "unstable"
            and source.failure_policy != "always_try"
            and not _has_recent_success(entry, now)
        ):
            continue
        filtered.append(source)
    return filtered


def _has_recent_success(entry: dict, now: datetime) -> bool:
    last_success_at = entry.get("last_success_at")
    if not last_success_at:
        return False
    try:
        parsed = datetime.fromisoformat(last_success_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed >= now - timedelta(days=UNSTABLE_SKIP_GRACE_DAYS)
