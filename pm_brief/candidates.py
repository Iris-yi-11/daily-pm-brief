import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pm_brief.models import Article, Source


def load_candidate_articles(path: Path) -> List[Article]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [_article_from_candidate(item) for item in payload]


def _article_from_candidate(item: dict) -> Article:
    source = Source(
        name=item["source"],
        url=item.get("source_url", item["url"]),
        category=item["category"],
        quality=int(item.get("quality", 4)),
        language=item.get("language", "en"),
    )
    return Article(
        title=item["title"],
        url=item["url"],
        source=source,
        published_at=_parse_datetime(item.get("published_at")),
        summary=item.get("summary", ""),
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
