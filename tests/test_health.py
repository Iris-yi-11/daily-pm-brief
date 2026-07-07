import unittest

from pm_brief.health import filter_sources_by_health, merge_source_health
from pm_brief.models import Source


class HealthTests(unittest.TestCase):
    def test_merge_source_health_marks_source_unstable_after_repeated_failures(self):
        existing = {}
        failed_result = {
            "name": "Broken Feed",
            "url": "https://example.com/feed.xml",
            "ok": False,
            "article_count": 0,
            "error": "timeout",
            "checked_at": "2026-07-03T00:00:00+00:00",
        }

        once = merge_source_health(existing, [failed_result], failure_threshold=2)
        twice = merge_source_health(once, [failed_result], failure_threshold=2)

        key = "Broken Feed|https://example.com/feed.xml"
        self.assertEqual(twice[key]["consecutive_failures"], 2)
        self.assertEqual(twice[key]["status"], "unstable")
        self.assertEqual(twice[key]["last_error"], "timeout")

    def test_merge_source_health_resets_failures_after_success(self):
        existing = {
            "Feed|https://example.com/feed.xml": {
                "name": "Feed",
                "url": "https://example.com/feed.xml",
                "consecutive_failures": 2,
                "total_failures": 2,
                "total_successes": 0,
                "status": "unstable",
            }
        }
        success_result = {
            "name": "Feed",
            "url": "https://example.com/feed.xml",
            "ok": True,
            "article_count": 1,
            "error": "",
            "checked_at": "2026-07-03T00:05:00+00:00",
        }

        merged = merge_source_health(existing, [success_result], failure_threshold=2)

        entry = merged["Feed|https://example.com/feed.xml"]
        self.assertEqual(entry["consecutive_failures"], 0)
        self.assertEqual(entry["total_successes"], 1)
        self.assertEqual(entry["status"], "healthy")

    def test_filter_sources_by_health_skips_unstable_sources_by_default(self):
        sources = [
            Source("Stable", "https://example.com/stable.xml", "AI Frontier", 5, "en"),
            Source("Broken", "https://example.com/broken.xml", "AI Frontier", 5, "en"),
        ]
        health = {
            "Broken|https://example.com/broken.xml": {
                "name": "Broken",
                "url": "https://example.com/broken.xml",
                "status": "unstable",
            }
        }

        filtered = filter_sources_by_health(sources, health)

        self.assertEqual([source.name for source in filtered], ["Stable"])

    def test_filter_sources_by_health_keeps_always_try_sources(self):
        sources = [
            Source(
                "Critical",
                "https://example.com/critical.xml",
                "AI Frontier",
                5,
                "en",
                failure_policy="always_try",
            )
        ]
        health = {
            "Critical|https://example.com/critical.xml": {
                "name": "Critical",
                "url": "https://example.com/critical.xml",
                "status": "unstable",
            }
        }

        filtered = filter_sources_by_health(sources, health)

        self.assertEqual([source.name for source in filtered], ["Critical"])

    def test_filter_sources_by_health_keeps_recently_successful_unstable_sources(self):
        sources = [
            Source("Recovering", "https://example.com/recovering.xml", "AI Frontier", 5, "en"),
        ]
        health = {
            "Recovering|https://example.com/recovering.xml": {
                "name": "Recovering",
                "url": "https://example.com/recovering.xml",
                "status": "unstable",
                "last_success_at": "2026-07-05T08:12:00+00:00",
            }
        }

        filtered = filter_sources_by_health(sources, health)

        self.assertEqual([source.name for source in filtered], ["Recovering"])

    def test_merge_source_health_does_not_promote_network_wide_dns_failures_to_unstable(self):
        existing = {
            "Feed A|https://example.com/a.xml": {
                "name": "Feed A",
                "url": "https://example.com/a.xml",
                "consecutive_failures": 2,
                "total_failures": 2,
                "total_successes": 0,
                "status": "degraded",
            }
        }
        results = [
            {
                "name": "Feed A",
                "url": "https://example.com/a.xml",
                "ok": False,
                "article_count": 0,
                "error": "URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>",
                "checked_at": "2026-07-03T00:00:00+00:00",
            },
            {
                "name": "Feed B",
                "url": "https://example.com/b.xml",
                "ok": False,
                "article_count": 0,
                "error": "URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>",
                "checked_at": "2026-07-03T00:00:00+00:00",
            },
        ]

        merged = merge_source_health(existing, results, failure_threshold=3)

        self.assertEqual(merged["Feed A|https://example.com/a.xml"]["consecutive_failures"], 2)
        self.assertEqual(merged["Feed A|https://example.com/a.xml"]["status"], "degraded")
        self.assertEqual(merged["Feed B|https://example.com/b.xml"]["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
