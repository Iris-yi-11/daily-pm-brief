import email.utils
import html
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from pm_brief.models import Article, Source


USER_AGENT = "DailyPMGrowthBrief/0.1 (+local personal learning automation)"


def fetch_articles(
    sources: Iterable[Source],
    limit_per_source: int = 8,
    timeout: int = 20,
    max_workers: int = 8,
) -> List[Article]:
    source_list = list(sources)
    if not source_list:
        return []
    worker_count = max(1, min(max_workers, len(source_list)))
    articles: List[Article] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for source_articles in executor.map(lambda source: _fetch_source_safe(source, limit_per_source, timeout), source_list):
            articles.extend(source_articles)
    return articles


def _fetch_source_safe(source: Source, limit: int, timeout: int) -> List[Article]:
    try:
        return fetch_source(source, limit=limit, timeout=timeout)
    except Exception as exc:
        return [
            Article(
                title=f"[Fetch warning] {source.name}",
                url=source.url,
                source=source,
                published_at=datetime.now(timezone.utc),
                summary=f"自动抓取该来源失败：{exc.__class__.__name__}: {exc}",
            )
        ]


def fetch_source(source: Source, limit: int = 8, timeout: int = 20) -> List[Article]:
    data = _download_bytes(source.url, timeout=timeout)
    root = ET.fromstring(data)
    if root.tag.endswith("rss"):
        return _parse_rss(root, source, limit)
    return _parse_atom(root, source, limit)


def _download_bytes(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception as urllib_error:
        return _read_url_with_curl(url, timeout=timeout, previous_error=urllib_error)


def _read_url_with_curl(url: str, timeout: int, previous_error: Exception) -> bytes:
    try:
        result = subprocess.run(
            [
                "curl",
                "--location",
                "--silent",
                "--show-error",
                "--max-time",
                str(max(timeout, 10)),
                "--user-agent",
                USER_AGENT,
                url,
            ],
            check=True,
            capture_output=True,
            timeout=max(timeout, 10) + 3,
        )
    except Exception as curl_error:
        raise RuntimeError(f"urllib failed: {previous_error}; curl fallback failed: {curl_error}") from curl_error
    if not result.stdout:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"urllib failed: {previous_error}; curl fallback returned empty body: {stderr}")
    return result.stdout


def _parse_rss(root: ET.Element, source: Source, limit: int) -> List[Article]:
    items = root.findall("./channel/item")
    articles = []
    for item in items[:limit]:
        title = _clean_text(_find_text(item, "title"))
        url = _clean_text(_find_text(item, "link"))
        summary = _clean_text(_find_text(item, "description"))
        published_at = _parse_date(_find_text(item, "pubDate"))
        if title and url:
            articles.append(Article(title=title, url=url, source=source, published_at=published_at, summary=summary))
    return articles


def _parse_atom(root: ET.Element, source: Source, limit: int) -> List[Article]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("./atom:entry", ns) or root.findall("./entry")
    articles = []
    for entry in entries[:limit]:
        title = _clean_text(_find_text(entry, "title"))
        url = _atom_link(entry)
        summary = _clean_text(_find_text(entry, "summary") or _find_text(entry, "content"))
        published_at = _parse_date(_find_text(entry, "published") or _find_text(entry, "updated"))
        if title and url:
            articles.append(Article(title=title, url=url, source=source, published_at=published_at, summary=summary))
    return articles


def _find_text(node: ET.Element, local_name: str) -> str:
    for child in node:
        if child.tag.split("}")[-1] == local_name:
            return child.text or ""
    return ""


def _atom_link(entry: ET.Element) -> str:
    for child in entry:
        if child.tag.split("}")[-1] == "link":
            href = child.attrib.get("href")
            if href:
                return href
    return ""


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return None


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()
