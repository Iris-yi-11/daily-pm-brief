import time
import unittest
from urllib.error import URLError
from unittest.mock import patch

from pm_brief.fetch import _download_bytes
from pm_brief.fetch import _parse_date
from pm_brief.fetch import fetch_articles
from pm_brief.models import Article, Source


class FetchTests(unittest.TestCase):
    def test_fetch_articles_runs_sources_concurrently(self):
        sources = [
            Source("A", "https://example.com/a", "AI Frontier", 5, "en"),
            Source("B", "https://example.com/b", "AI Frontier", 5, "en"),
            Source("C", "https://example.com/c", "AI Frontier", 5, "en"),
        ]

        def slow_fetch(source, limit, timeout):
            time.sleep(0.2)
            return [Article(source.name, source.url, source, None, "summary")]

        start = time.monotonic()
        with patch("pm_brief.fetch.fetch_source", side_effect=slow_fetch):
            articles = fetch_articles(sources, limit_per_source=1, timeout=1, max_workers=3)
        elapsed = time.monotonic() - start

        self.assertEqual(len(articles), 3)
        self.assertLess(elapsed, 0.45)

    def test_parse_date_accepts_iso_8601_atom_dates(self):
        parsed = _parse_date("2026-07-03T00:00:00Z")

        self.assertEqual(parsed.isoformat(), "2026-07-03T00:00:00+00:00")

    def test_download_bytes_falls_back_to_curl_after_urlopen_failure(self):
        curl_result = type("CompletedProcess", (), {"stdout": b"<rss />"})

        with patch("pm_brief.fetch.urllib.request.urlopen", side_effect=URLError("dns down")):
            with patch("pm_brief.fetch.subprocess.run", return_value=curl_result) as run:
                payload = _download_bytes("https://example.com/feed.xml", timeout=6)

        self.assertEqual(payload, b"<rss />")
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
