import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pm_brief.build import build_brief, generate_brief, write_latest_copy, write_status
from pm_brief.models import Article, ScoredArticle, ScoreBreakdown, Source


class BuildBriefTests(unittest.TestCase):
    def test_must_reads_exclude_low_priority_items(self):
        source = Source(
            name="Retail Dive",
            url="https://www.retaildive.com/feeds/news/",
            category="E-commerce & Marketplace",
            quality=4,
            language="en",
        )
        strong = ScoredArticle(
            article=Article(
                title="Marketplace launches AI seller analytics workflow",
                url="https://example.com/strong",
                source=source,
                published_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
                summary="A marketplace launched AI workflow analytics for sellers.",
            ),
            score=ScoreBreakdown(impact=5, novelty=4, source_quality=4, pm_relevance=5, actionability=4, total=4.35),
            keywords=["Marketplace", "Seller Tools", "AI Analytics"],
        )
        weak = ScoredArticle(
            article=Article(
                title="Consumer spending changes during the week",
                url="https://example.com/weak",
                source=source,
                published_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
                summary="A general macro update without platform or seller product implications.",
            ),
            score=ScoreBreakdown(impact=2, novelty=1, source_quality=4, pm_relevance=2, actionability=1, total=2.05),
            keywords=[],
        )

        brief = build_brief([strong, weak], date(2026, 6, 30))

        self.assertEqual([item.article.url for item in brief.must_reads], ["https://example.com/strong"])

    def test_must_reads_include_medium_quality_actionable_items(self):
        source = Source(
            name="Digiday",
            url="https://digiday.com/feed/",
            category="E-commerce & Marketplace",
            quality=4,
            language="en",
        )
        medium = ScoredArticle(
            article=Article(
                title="Retail media networks expand creator marketing tools for advertisers",
                url="https://example.com/retail-media",
                source=source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="Retail media platforms add creator marketing workflows and measurement tools.",
            ),
            score=ScoreBreakdown(impact=3, novelty=3, source_quality=4, pm_relevance=4, actionability=3, total=3.05),
            keywords=["Retail Media", "Marketplace"],
        )

        brief = build_brief([medium], date(2026, 7, 3))

        self.assertEqual([item.article.url for item in brief.must_reads], ["https://example.com/retail-media"])

    def test_marketplace_signals_include_relevant_lower_scored_items(self):
        source = Source(
            name="Retail Dive",
            url="https://www.retaildive.com/feeds/news/",
            category="E-commerce & Marketplace",
            quality=4,
            language="en",
        )
        item = ScoredArticle(
            article=Article(
                title="Target expands marketplace with new brand additions",
                url="https://example.com/target-marketplace",
                source=source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="Target adds more brands to its marketplace assortment.",
            ),
            score=ScoreBreakdown(impact=3, novelty=2, source_quality=4, pm_relevance=3, actionability=2, total=2.65),
            keywords=["Marketplace"],
        )

        brief = build_brief([item], date(2026, 7, 3))

        self.assertEqual([signal.article.url for signal in brief.marketplace_signals], ["https://example.com/target-marketplace"])

    def test_write_latest_copy_creates_stable_today_markdown(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            daily_report = output_dir / "2026-06-30.md"
            daily_report.write_text("# Daily PM Growth Brief\n\n今日内容", encoding="utf-8")

            latest_path = write_latest_copy(daily_report, output_dir)

            self.assertEqual(latest_path, output_dir / "today.md")
            self.assertEqual(latest_path.read_text(encoding="utf-8"), "# Daily PM Growth Brief\n\n今日内容")

    def test_write_status_records_run_health(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            status_path = write_status(
                output_dir=output_dir,
                status={
                    "brief_date": "2026-07-01",
                    "output_path": "reports/2026-07-01.md",
                    "source_count": 42,
                    "fetched_article_count": 120,
                    "candidate_count": 90,
                    "scored_count": 80,
                    "must_read_count": 3,
                    "ai_watch_count": 3,
                    "marketplace_count": 2,
                    "failed_sources": ["Example Feed"],
                },
            )

            content = status_path.read_text(encoding="utf-8")

            self.assertIn("Daily PM Growth Brief Status", content)
            self.assertIn("Brief date: 2026-07-01", content)
            self.assertIn("Source count: 42", content)
            self.assertIn("Failed sources: Example Feed", content)

    def test_generate_brief_uses_configured_fetch_options(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "sources.json"
            config_path.write_text(
                '{"fetch_timeout_seconds": 3, "max_fetch_workers": 12, "sources": [], "lookback_days": 4, "limit_per_source": 8}',
                encoding="utf-8",
            )

            with patch("pm_brief.build.fetch_articles", return_value=[]) as fetch_articles:
                generate_brief(config_path, root / "reports", root / "data" / "archive.jsonl", date(2026, 7, 1))

            fetch_articles.assert_called_once()
            self.assertEqual(fetch_articles.call_args.kwargs["timeout"], 3)
            self.assertEqual(fetch_articles.call_args.kwargs["max_workers"], 12)

    def test_generate_brief_uses_candidate_articles_when_feed_fetch_fails(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "sources.json"
            config_path.write_text(
                '{"fetch_timeout_seconds": 3, "sources": [{"name":"Broken","url":"https://example.com/rss","category":"AI Frontier","quality":5,"language":"en"}], "lookback_days": 4, "limit_per_source": 8}',
                encoding="utf-8",
            )
            broken_source = Source("Broken", "https://example.com/rss", "AI Frontier", 5, "en")
            candidate_source = Source("OpenAI Blog", "https://openai.com/blog/rss.xml", "AI Frontier", 5, "en")
            warning = Article(
                title="[Fetch warning] Broken",
                url="https://example.com/rss",
                source=broken_source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="network failed",
            )
            candidate = Article(
                title="OpenAI launches agent workflow analytics for merchants",
                url="https://example.com/agent-workflow",
                source=candidate_source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="A new AI agent workflow helps merchants analyze data and execute growth actions.",
            )

            with patch("pm_brief.build.fetch_articles", return_value=[warning]):
                output_path = generate_brief(
                    config_path,
                    root / "reports",
                    root / "data" / "archive.jsonl",
                    date(2026, 7, 3),
                    candidate_articles=[candidate],
                )

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("OpenAI launches agent workflow analytics for merchants", content)
            self.assertIn("Candidate article count: 1", (root / "reports" / "status.md").read_text(encoding="utf-8"))

    def test_generate_brief_preserves_previous_today_when_all_fetches_fail(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "sources.json"
            config_path.write_text(
                '{"sources": [{"name":"Broken","url":"https://example.com/rss","category":"AI Frontier","quality":5,"language":"en"}], "lookback_days": 4, "limit_per_source": 8}',
                encoding="utf-8",
            )
            reports = root / "reports"
            reports.mkdir()
            previous = reports / "today.md"
            previous.write_text("# Daily PM Growth Brief — 2026-07-02\n\n上一份有效简报", encoding="utf-8")
            broken_source = Source("Broken", "https://example.com/rss", "AI Frontier", 5, "en")
            warning = Article(
                title="[Fetch warning] Broken",
                url="https://example.com/rss",
                source=broken_source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="network failed",
            )

            with patch("pm_brief.build.fetch_articles", return_value=[warning]):
                output_path = generate_brief(config_path, reports, root / "data" / "archive.jsonl", date(2026, 7, 3))

            self.assertEqual(output_path, reports / "today.md")
            self.assertEqual(previous.read_text(encoding="utf-8"), "# Daily PM Growth Brief — 2026-07-02\n\n上一份有效简报")
            self.assertIn("Preserved existing report: True", (reports / "status.md").read_text(encoding="utf-8"))

    def test_generate_brief_falls_back_to_recent_archive_when_live_fetches_fail(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "sources.json"
            config_path.write_text(
                '{"sources": [{"name":"AWS Machine Learning Blog","url":"https://aws.amazon.com/blogs/machine-learning/feed/","category":"AI Frontier","quality":4,"language":"en"}], "lookback_days": 4, "limit_per_source": 8}',
                encoding="utf-8",
            )
            reports = root / "reports"
            archive_path = root / "data" / "archive.jsonl"
            archive_path.parent.mkdir(parents=True)
            archive_path.write_text(
                '\n'.join(
                    [
                        '{"date":"2026-07-02","title":"Recent AI workflow launch","url":"https://example.com/ai","source":"AWS Machine Learning Blog","category":"AI Frontier","score":3.2,"published_at":"2026-07-02T10:00:00+00:00"}',
                        '{"date":"2026-07-02","title":"Marketplace seller analytics update","url":"https://example.com/market","source":"Retail Dive","category":"E-commerce & Marketplace","score":3.0,"published_at":"2026-07-02T11:00:00+00:00"}',
                    ]
                )
                + '\n',
                encoding="utf-8",
            )
            broken_source = Source("Broken", "https://example.com/rss", "AI Frontier", 5, "en")
            warning = Article(
                title="[Fetch warning] Broken",
                url="https://example.com/rss",
                source=broken_source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="network failed",
            )

            with patch("pm_brief.build.fetch_articles", return_value=[warning]):
                output_path = generate_brief(config_path, reports, archive_path, date(2026, 7, 3))

            content = output_path.read_text(encoding="utf-8")
            status = (reports / "status.md").read_text(encoding="utf-8")
            self.assertIn("Recent AI workflow launch", content)
            self.assertIn("Fallback mode: archive", status)
            self.assertIn("Preserved existing report: False", status)

    def test_generate_brief_preserves_previous_report_when_fallback_is_too_weak(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "sources.json"
            config_path.write_text(
                '{"sources": [{"name":"AWS Machine Learning Blog","url":"https://aws.amazon.com/blogs/machine-learning/feed/","category":"AI Frontier","quality":4,"language":"en"}], "lookback_days": 4, "limit_per_source": 8}',
                encoding="utf-8",
            )
            reports = root / "reports"
            reports.mkdir()
            previous_daily = reports / "2026-07-02.md"
            previous_daily.write_text("# Daily PM Growth Brief — 2026-07-02\n\n上一份高质量简报", encoding="utf-8")
            archive_path = root / "data" / "archive.jsonl"
            archive_path.parent.mkdir(parents=True)
            archive_path.write_text(
                '{"date":"2026-07-02","title":"Recent marketplace note","url":"https://example.com/market","source":"Retail Dive","category":"E-commerce & Marketplace","score":2.65,"published_at":"2026-07-02T11:00:00+00:00"}\n',
                encoding="utf-8",
            )
            broken_source = Source("Broken", "https://example.com/rss", "AI Frontier", 5, "en")
            warning = Article(
                title="[Fetch warning] Broken",
                url="https://example.com/rss",
                source=broken_source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="network failed",
            )

            with patch("pm_brief.build.fetch_articles", return_value=[warning]):
                output_path = generate_brief(config_path, reports, archive_path, date(2026, 7, 3))

            status = (reports / "status.md").read_text(encoding="utf-8")
            self.assertEqual(output_path, previous_daily)
            self.assertIn("Fallback mode: preserved", status)
            self.assertIn("Preserved existing report: True", status)

    def test_generate_brief_falls_back_to_recent_feed_cache_when_live_fetches_fail(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "sources.json"
            config_path.write_text(
                '{"sources": [{"name":"OpenAI Blog","url":"https://openai.com/blog/rss.xml","category":"AI Frontier","quality":5,"language":"en"}], "lookback_days": 4, "limit_per_source": 8, "feed_cache_path":"data/feed_cache.json", "feed_cache_retention_days": 7}',
                encoding="utf-8",
            )
            reports = root / "reports"
            feed_cache = root / "data" / "feed_cache.json"
            feed_cache.parent.mkdir(parents=True)
            feed_cache.write_text(
                '{\n'
                '  "OpenAI Blog|https://openai.com/blog/rss.xml": {\n'
                '    "name": "OpenAI Blog",\n'
                '    "url": "https://openai.com/blog/rss.xml",\n'
                '    "category": "AI Frontier",\n'
                '    "quality": 5,\n'
                '    "language": "en",\n'
                '    "fetched_at": "2026-07-02T12:00:00+00:00",\n'
                '    "articles": [\n'
                '      {\n'
                '        "title": "OpenAI launches operator workflow for merchants",\n'
                '        "url": "https://example.com/openai-workflow",\n'
                '        "published_at": "2026-07-02T09:00:00+00:00",\n'
                '        "summary": "A new agent workflow helps merchants analyze performance and take actions."\n'
                '      }\n'
                '    ]\n'
                '  }\n'
                '}\n',
                encoding="utf-8",
            )
            broken_source = Source("Broken", "https://example.com/rss", "AI Frontier", 5, "en")
            warning = Article(
                title="[Fetch warning] Broken",
                url="https://example.com/rss",
                source=broken_source,
                published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
                summary="network failed",
            )

            with patch("pm_brief.build.fetch_articles", return_value=[warning]):
                output_path = generate_brief(config_path, reports, root / "data" / "archive.jsonl", date(2026, 7, 3))

            content = output_path.read_text(encoding="utf-8")
            status = (reports / "status.md").read_text(encoding="utf-8")
            self.assertIn("OpenAI launches operator workflow for merchants", content)
            self.assertIn("Fallback mode: feed_cache", status)


if __name__ == "__main__":
    unittest.main()
