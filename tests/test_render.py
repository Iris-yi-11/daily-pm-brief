import unittest
from datetime import date, datetime, timezone

from pm_brief.models import Article, Brief, LearningCard, ScoredArticle, ScoreBreakdown, Source
from pm_brief.render import render_markdown


class RenderTests(unittest.TestCase):
    def test_renders_required_sections_and_source_metadata(self):
        source = Source(
            name="Marketplace Pulse",
            url="https://www.marketplacepulse.com/feed",
            category="E-commerce & Marketplace",
            quality=5,
            language="en",
        )
        article = Article(
            title="Amazon adds new seller analytics dashboard",
            url="https://example.com/seller-analytics",
            source=source,
            published_at=datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc),
            summary="Amazon released seller analytics tools for ads and conversion diagnostics.",
        )
        scored = ScoredArticle(
            article=article,
            score=ScoreBreakdown(
                impact=5,
                novelty=4,
                source_quality=5,
                pm_relevance=5,
                actionability=4,
                total=4.65,
            ),
            keywords=["Seller Analytics", "Retail Media", "Conversion Funnel"],
        )
        brief = Brief(
            brief_date=date(2026, 6, 30),
            one_line_signal="商家增长工具正在从报表走向可执行诊断。",
            must_reads=[scored],
            ai_product_watch=[scored],
            marketplace_signals=[scored],
            thinking_question="如果为 POP 商家设计经营诊断，应优先解释指标还是推荐动作？",
            thinking_hints=["商家不只缺数据，也缺下一步动作。", "不同成熟度商家需要不同诊断粒度。"],
            learning_card=LearningCard(
                concept="Retail Media",
                explanation="平台利用站内流量和交易数据提供广告与营销能力。",
                scenario="商家根据搜索、推荐和转化数据投放广告。",
                relation="商家成长产品需要帮助商家理解流量质量和投放回报。",
                english_expression="Retail media turns marketplace traffic into measurable advertising inventory.",
            ),
            cited_articles=[scored],
            tags=["#Retail-Media", "#Seller-Growth"],
        )

        markdown = render_markdown(brief)

        self.assertIn("Daily PM Growth Brief — 2026-06-30", markdown)
        self.assertIn("0. Today's One-Line Signal", markdown)
        self.assertIn("1. Must Read", markdown)
        self.assertIn("2. AI Product Watch", markdown)
        self.assertIn("3. Marketplace & Seller Growth", markdown)
        self.assertIn("4. PM Thinking", markdown)
        self.assertIn("5. 5-Minute Learning Card", markdown)
        self.assertIn("6. 原文阅读清单", markdown)
        self.assertIn("Marketplace Pulse / 2026-06-30", markdown)
        self.assertIn("https://example.com/seller-analytics", markdown)


if __name__ == "__main__":
    unittest.main()
