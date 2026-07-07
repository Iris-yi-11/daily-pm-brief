import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from pm_brief.health import source_key
from pm_brief.models import Article, Source


FeedCache = Dict[str, dict]


def load_feed_cache(path: Path) -> FeedCache:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_feed_cache(path: Path, cache: FeedCache) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def update_feed_cache(
    existing: FeedCache,
    articles: Iterable[Article],
    fetched_at: datetime,
    retention_days: int = 7,
) -> FeedCache:
    merged = dict(existing)
    cutoff = fetched_at - timedelta(days=retention_days)
    grouped: Dict[str, List[Article]] = {}
    for article in articles:
        key = source_key(article.source.name, article.source.url)
        grouped.setdefault(key, []).append(article)

    for key, source_articles in grouped.items():
        source = source_articles[0].source
        merged[key] = {
            "name": source.name,
            "url": source.url,
            "category": source.category,
            "quality": source.quality,
            "language": source.language,
            "fetched_at": fetched_at.isoformat(),
            "articles": [
                _serialize_article(article)
                for article in source_articles
                if article.published_at is None or article.published_at >= cutoff
            ],
        }
    return merged


def cached_articles_for_sources(
    cache: FeedCache,
    sources: Iterable[Source],
    max_age_days: int = 7,
) -> List[Article]:
    now = datetime.now(timezone.utc)
    articles: List[Article] = []
    for source in sources:
        entry = cache.get(source_key(source.name, source.url))
        if not entry:
            continue
        fetched_at = _parse_datetime(entry.get("fetched_at"))
        if fetched_at is None or fetched_at < now - timedelta(days=max_age_days):
            continue
        for item in entry.get("articles", []):
            article = _deserialize_article(item, source)
            if article is not None:
                articles.append(article)
    return articles


def _serialize_article(article: Article) -> dict:
    return {
        "title": article.title,
        "url": article.url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary": article.summary,
    }


def _deserialize_article(item: dict, source: Source):
    title = item.get("title")
    url = item.get("url")
    if not title or not url:
        return None
    return Article(
        title=title,
        url=url,
        source=source,
        published_at=_parse_datetime(item.get("published_at")),
        summary=item.get("summary", ""),
    )


def _parse_datetime(value: str):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
