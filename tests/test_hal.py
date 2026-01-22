"""Tests for HAL searcher."""
import unittest
import requests
from paper_search_mcp.academic_platforms.hal import HALSearcher


def check_hal_accessible():
    """Check if HAL API is accessible."""
    try:
        response = requests.get("https://hal.science/search/search?rows=1", timeout=5)
        return response.status_code == 200
    except:
        return False


class TestHALSearcher(unittest.TestCase):
    """Tests for HALSearcher class."""

    @classmethod
    def setUpClass(cls):
        cls.hal_accessible = check_hal_accessible()
        if not cls.hal_accessible:
            print(
                "\nWarning: HAL API is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = HALSearcher()

    @unittest.skipUnless(check_hal_accessible(), "HAL not accessible")
    def test_search_basic(self):
        """Test basic search functionality."""
        results = self.searcher.search("apprentissage automatique", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertEqual(paper.source, "hal")

    @unittest.skipUnless(check_hal_accessible(), "HAL not accessible")
    def test_search_with_year_filter(self):
        """Test search with year filter."""
        results = self.searcher.search("deep learning", max_results=3, year="2022")
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_hal_accessible(), "HAL not accessible")
    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.searcher.search("", max_results=3)
        self.assertIsInstance(results, list)


class TestHALSearcherUnit(unittest.TestCase):
    """Unit tests for HALSearcher without network."""

    def setUp(self):
        self.searcher = HALSearcher()

    def test_session_created(self):
        """Test that session is created on initialization."""
        self.assertTrue(hasattr(self.searcher, 'session'))
        self.assertIsNotNone(self.searcher.session)

    def test_base_url(self):
        """Test that base URL is set correctly."""
        self.assertIn("hal.science", self.searcher.BASE_URL)


if __name__ == "__main__":
    unittest.main()
