"""Code Assistant search tests; no MCP server, credentials or network required."""

import importlib.util
import unittest
from pathlib import Path

import pandas as pd

SOURCE = Path(__file__).resolve().parents[1] / "src" / "utils" / "api_searcher.py"
SPEC = importlib.util.spec_from_file_location("code_assistant_searcher", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class APISearcherTests(unittest.TestCase):
    def setUp(self):
        self.searcher = MODULE.APISearcher.__new__(MODULE.APISearcher)
        self.searcher._data = pd.DataFrame(
            [
                {
                    "api_name": "Quote [v1]",
                    "function_name": "quote_v1",
                    "category": "domestic",
                    "subcategory": "stock",
                },
                {
                    "api_name": "Quote regular",
                    "function_name": "quote_regular",
                    "category": "overseas",
                    "subcategory": "stock",
                },
            ]
        )

    def test_other_metacharacters_do_not_become_patterns(self):
        for term in ("(", ".", "+", "*"):
            with self.subTest(term=term):
                self.assertEqual(
                    self.searcher.search(api_name=term)["status"], "no_results"
                )

    def test_partial_match_is_case_insensitive(self):
        result = self.searcher.search(api_name="quote")
        self.assertEqual(result["total_count"], 2)

    def test_category_filter_remains_exact(self):
        self.assertEqual(self.searcher.search(category="dom")["status"], "no_results")
        self.assertEqual(self.searcher.search(category="domestic")["total_count"], 1)

    def test_missing_values_do_not_match(self):
        self.searcher._data.loc[1, "api_name"] = None
        result = self.searcher.search(api_name="Quote")
        self.assertEqual(result["total_count"], 1)

    def test_open_bracket_is_a_literal_search_term(self):
        response = self.searcher.search(api_name="[")
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["total_count"], 1)
        self.assertEqual(response["results"][0]["function_name"], "quote_v1")


if __name__ == "__main__":
    unittest.main()
