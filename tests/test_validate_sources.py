import unittest

from scripts.validate_sources import _looks_like_global_network_failure


class ValidateSourcesTests(unittest.TestCase):
    def test_global_network_failure_detects_all_dns_failures(self):
        failed = [
            {"name": "A", "error": "URLError: nodename nor servname provided, or not known"},
            {"name": "B", "error": "RuntimeError: curl fallback failed: could not resolve host"},
        ]

        self.assertTrue(_looks_like_global_network_failure(failed))

    def test_global_network_failure_ignores_mixed_source_errors(self):
        failed = [
            {"name": "A", "error": "URLError: nodename nor servname provided, or not known"},
            {"name": "B", "error": "HTTPError: HTTP Error 404: Not Found"},
        ]

        self.assertFalse(_looks_like_global_network_failure(failed))


if __name__ == "__main__":
    unittest.main()
