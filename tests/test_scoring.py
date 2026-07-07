import unittest
from datetime import datetime, timezone

from pm_brief.models import Article, Source
from pm_brief.scoring import ScoreWeights, score_article


class ScoringTests(unittest.TestCase):
    def test_scores_relevant_frontier_article_higher_than_generic_news(self):
        source = Source(
            name="OpenAI Blog",
            url="https://openai.com/blog/rss.xml",
            category="AI Frontier",
            quality=5,
            language="en",
        )
        relevant = Article(
            title="OpenAI launches agent workflow tools for enterprise analytics",
            url="https://example.com/agent-workflows",
            source=source,
            published_at=datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc),
            summary="New AI agent workflow automation helps teams analyze data, run tasks, and integrate business tools.",
        )
        generic = Article(
            title="Technology stocks move higher after market open",
            url="https://example.com/stocks",
            source=source,
            published_at=datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc),
            summary="Shares changed during trading with no new product capability announced.",
        )

        relevant_score = score_article(relevant, ScoreWeights.default())
        generic_score = score_article(generic, ScoreWeights.default())

        self.assertGreater(relevant_score.total, generic_score.total)
        self.assertGreaterEqual(relevant_score.pm_relevance, 4)
        self.assertGreaterEqual(relevant_score.actionability, 3)

    def test_score_weights_can_be_loaded_from_config_mapping(self):
        weights = ScoreWeights.from_mapping(
            {
                "impact": 0.25,
                "novelty": 0.2,
                "source_quality": 0.15,
                "pm_relevance": 0.25,
                "actionability": 0.15,
            }
        )

        self.assertEqual(weights.impact, 0.25)
        self.assertEqual(weights.pm_relevance, 0.25)


if __name__ == "__main__":
    unittest.main()
