import re
from typing import Iterable, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pm_brief.models import Article


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "spm"}


def dedupe_articles(articles: Iterable[Article]) -> List[Article]:
    seen_urls = set()
    seen_titles = set()
    deduped: List[Article] = []
    for article in articles:
        url_key = normalize_url(article.url)
        title_key = normalize_title(article.title)
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        deduped.append(article)
    return deduped


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            urlencode(query),
            "",
        )
    )


def normalize_title(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", title.lower())
    return re.sub(r"\s+", " ", normalized).strip()
