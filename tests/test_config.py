import unittest
from pathlib import Path

from pm_brief.config import load_manual_sources, load_sources, resolve_config_path


class ConfigTests(unittest.TestCase):
    def test_load_sources_ignores_disabled_and_manual_sources(self):
        config = {
            "sources": [
                {
                    "name": "OpenAI Blog",
                    "url": "https://openai.com/blog/rss.xml",
                    "category": "AI Frontier",
                    "quality": 5,
                    "language": "en",
                    "enabled": True,
                },
                {
                    "name": "Manual Only",
                    "url": "https://example.com/profile",
                    "category": "AI Creator Watchlist",
                    "quality": 3,
                    "language": "zh",
                    "enabled": False,
                },
            ],
            "manual_sources": [
                {
                    "name": "张咋啦",
                    "url": "https://www.xiaohongshu.com/user/profile/example",
                    "category": "Chinese AI Creator Watchlist",
                    "language": "zh",
                    "reason": "字节 AI 业务与 AI 趋势追踪。",
                }
            ],
        }

        self.assertEqual([source.name for source in load_sources(config)], ["OpenAI Blog"])
        self.assertEqual(load_manual_sources(config)[0]["name"], "张咋啦")

    def test_resolve_config_path_uses_project_root_for_config_dir(self):
        resolved = resolve_config_path(Path("/tmp/project/config/sources.json"), "data/source_health.json")

        self.assertEqual(resolved, Path("/tmp/project/data/source_health.json"))


if __name__ == "__main__":
    unittest.main()
