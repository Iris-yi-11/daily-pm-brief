import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pm_brief.candidates import load_candidate_articles


class CandidateTests(unittest.TestCase):
    def test_load_candidate_articles_from_json_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "candidates.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "title": "OpenAI launches new agent analytics workflow",
                            "url": "https://example.com/openai-agent-analytics",
                            "source": "Example Source",
                            "category": "AI Frontier",
                            "quality": 5,
                            "language": "en",
                            "published_at": "2026-07-03T01:00:00+00:00",
                            "summary": "The product helps teams turn analytics into executable agent workflows.",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            articles = load_candidate_articles(path)

            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].title, "OpenAI launches new agent analytics workflow")
            self.assertEqual(articles[0].source.name, "Example Source")
            self.assertEqual(articles[0].source.category, "AI Frontier")
            self.assertEqual(articles[0].published_at.isoformat(), "2026-07-03T01:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
