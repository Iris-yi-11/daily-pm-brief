import unittest
from datetime import datetime, timezone

from pm_brief.dedupe import dedupe_articles
from pm_brief.models import Article, Source


class DedupeTests(unittest.TestCase):
    def test_dedupes_by_normalized_url_and_title(self):
        source = Source(
            name="TechCrunch AI",
            url="https://techcrunch.com/category/artificial-intelligence/feed/",
            category="AI Frontier",
            quality=4,
            language="en",
        )
        first = Article(
            title="New AI Agent Platform Launches",
            url="https://example.com/news?id=1&utm_source=rss",
            source=source,
            published_at=datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc),
            summary="A startup launched a new AI agent platform.",
        )
        same_url = Article(
            title="New AI Agent Platform Launches",
            url="https://example.com/news?id=1&utm_campaign=daily",
            source=source,
            published_at=datetime(2026, 6, 30, 2, 0, tzinfo=timezone.utc),
            summary="Duplicate from another campaign URL.",
        )
        same_title = Article(
            title="new ai agent platform launches",
            url="https://mirror.example.com/new-ai-agent-platform-launches",
            source=source,
            published_at=datetime(2026, 6, 30, 3, 0, tzinfo=timezone.utc),
            summary="Duplicate title from another source.",
        )

        deduped = dedupe_articles([first, same_url, same_title])

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].url, first.url)


if __name__ == "__main__":
    unittest.main()
