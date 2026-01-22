"""Tests for SSRN searcher."""
import unittest
import requests
from paper_search_mcp.academic_platforms.ssrn import SSRNSearcher


def check_ssrn_accessible():
    """Check if SSRN API is accessible."""
    try:
        response = requests.get("https://papers.ssrn.com/sol13/search.cgi?", timeout=5, params={"q": "test", "ma": "1"})
        return response.status_code == 200
    except:
        return False


class TestSSRNSearcher(unittest.TestCase):
    """Tests for SSRNSearcher class."""

    @classmethod
    def setUpClass(cls):
        cls.ssrn_accessible = check_ssrn_accessible()
        if not cls.ssrn_accessible:
            print(
                "\nWarning: SSRN is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = SSRNSearcher()

    @unittest.skipUnless(check_ssrn_accessible(), "SSRN not accessible")
    def test_search_basic(self):
        """Test basic search functionality."""
        results = self.searcher.search("economics", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertEqual(paper.source, "ssrn")

    @unittest.skipUnless(check_ssrn_accessible(), "SSRN not accessible")
    def test_search_with_year_filter(self):
        """Test search with year filter."""
        results = self.searcher.search("finance", max_results=3, year="2022")
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_ssrn_accessible(), "SSRN not accessible")
    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.searcher.search("", max_results=3)
        self.assertIsInstance(results, list)


class TestSSRNSearcherUnit(unittest.TestCase):
    """Unit tests for SSRNSearcher without network."""

    def setUp(self):
        self.searcher = SSRNSearcher()

    def test_session_created(self):
        """Test that session is created on initialization."""
        self.assertTrue(hasattr(self.searcher, 'session'))
        self.assertIsNotNone(self.searcher.session)


if __name__ == "__main__":
    unittest.main()
