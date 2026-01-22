"""Tests for DBLP searcher."""
import unittest
import requests
from paper_search_mcp.academic_platforms.dblp import DBLPSearcher


def check_dblp_accessible():
    """Check if DBLP API is accessible."""
    try:
        response = requests.get("https://dblp.org/search/publ/api?q=machine+learning&h=1&format=xml", timeout=5)
        return response.status_code == 200
    except:
        return False


class TestDBLPSearcher(unittest.TestCase):
    """Tests for DBLPSearcher class."""

    @classmethod
    def setUpClass(cls):
        cls.dblp_accessible = check_dblp_accessible()
        if not cls.dblp_accessible:
            print(
                "\nWarning: DBLP API is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = DBLPSearcher()

    @unittest.skipUnless(check_dblp_accessible(), "DBLP not accessible")
    def test_search_basic(self):
        """Test basic search functionality."""
        results = self.searcher.search("machine learning", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertEqual(paper.source, "dblp")

    @unittest.skipUnless(check_dblp_accessible(), "DBLP not accessible")
    def test_search_with_year_filter(self):
        """Test search with year filter."""
        results = self.searcher.search("neural networks", max_results=3, year="2022")
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_dblp_accessible(), "DBLP not accessible")
    def test_search_with_author_filter(self):
        """Test search with author filter."""
        results = self.searcher.search("", max_results=3, author="Geoffrey Hinton")
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_dblp_accessible(), "DBLP not accessible")
    def test_get_top_conferences(self):
        """Test getting top conferences list."""
        conferences = self.searcher.get_top_conferences()
        self.assertIsInstance(conferences, list)
        self.assertGreater(len(conferences), 0)
        self.assertIn("key", conferences[0])
        self.assertIn("name", conferences[0])

    @unittest.skipUnless(check_dblp_accessible(), "DBLP not accessible")
    def test_get_top_journals(self):
        """Test getting top journals list."""
        journals = self.searcher.get_top_journals()
        self.assertIsInstance(journals, list)
        self.assertGreater(len(journals), 0)


class TestDBLPSearcherUnit(unittest.TestCase):
    """Unit tests for DBLPSearcher without network."""

    def setUp(self):
        self.searcher = DBLPSearcher()

    def test_session_created(self):
        """Test that session is created on initialization."""
        self.assertTrue(hasattr(self.searcher, 'session'))
        self.assertIsNotNone(self.searcher.session)

    def test_base_urls(self):
        """Test that base URLs are set correctly."""
        self.assertIn("dblp.org", self.searcher.BASE_URL)
        self.assertIn("dblp.org", self.searcher.SEARCH_URL)


if __name__ == "__main__":
    unittest.main()
