"""Tests for OpenAlex searcher."""
import unittest
import requests
from paper_search_mcp.academic_platforms.openalex import OpenAlexSearcher


def check_openalex_accessible():
    """Check if OpenAlex API is accessible."""
    try:
        response = requests.get("https://api.openalex.org/works?per_page=1", timeout=5)
        return response.status_code == 200
    except:
        return False


class TestOpenAlexSearcher(unittest.TestCase):
    """Tests for OpenAlexSearcher class."""

    @classmethod
    def setUpClass(cls):
        cls.openalex_accessible = check_openalex_accessible()
        if not cls.openalex_accessible:
            print(
                "\nWarning: OpenAlex API is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = OpenAlexSearcher()

    @unittest.skipUnless(check_openalex_accessible(), "OpenAlex not accessible")
    def test_search_basic(self):
        """Test basic search functionality."""
        results = self.searcher.search("machine learning", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertTrue(paper.source.startswith("openalex"))

    @unittest.skipUnless(check_openalex_accessible(), "OpenAlex not accessible")
    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.searcher.search("", max_results=3)
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_openalex_accessible(), "OpenAlex not accessible")
    def test_search_with_year_filter(self):
        """Test search with year filter."""
        results = self.searcher.search("deep learning", max_results=3, year="2023")
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_openalex_accessible(), "OpenAlex not accessible")
    def test_get_paper_by_id(self):
        """Test getting paper by OpenAlex ID."""
        test_id = "W2741809807"  # A known OpenAlex paper ID

        paper = self.searcher.get_paper_by_id(test_id)

        if paper:
            self.assertEqual(paper.paper_id, test_id)
            self.assertTrue(paper.title)
        else:
            print(f"Could not fetch paper with ID: {test_id}")

    @unittest.skipUnless(check_openalex_accessible(), "OpenAlex not accessible")
    def test_get_paper_by_doi(self):
        """Test getting paper by DOI."""
        test_doi = "10.1038/nature12373"

        paper = self.searcher.get_paper_by_doi(test_doi)

        if paper:
            self.assertTrue(paper.title)
            self.assertIsInstance(paper.authors, list)
        else:
            print(f"Could not fetch paper with DOI: {test_doi}")

    @unittest.skipUnless(check_openalex_accessible(), "OpenAlex not accessible")
    def test_search_by_author(self):
        """Test searching by author name."""
        results = self.searcher.search_by_author("Geoffrey Hinton", max_results=3)
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)


class TestOpenAlexSearcherUnit(unittest.TestCase):
    """Unit tests for OpenAlexSearcher without network."""

    def setUp(self):
        self.searcher = OpenAlexSearcher()

    def test_session_created(self):
        """Test that session is created on initialization."""
        self.assertTrue(hasattr(self.searcher, 'session'))
        self.assertIsNotNone(self.searcher.session)


if __name__ == "__main__":
    unittest.main()
