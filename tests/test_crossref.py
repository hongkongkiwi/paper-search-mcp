"""Tests for CrossRef searcher."""
import unittest
import requests
from paper_search_mcp.academic_platforms.crossref import CrossRefSearcher


def check_crossref_accessible():
    """Check if CrossRef API is accessible."""
    try:
        response = requests.get("https://api.crossref.org/works", timeout=5)
        return response.status_code == 200
    except:
        return False


class TestCrossRefSearcher(unittest.TestCase):
    """Tests for CrossRefSearcher class."""

    @classmethod
    def setUpClass(cls):
        cls.crossref_accessible = check_crossref_accessible()
        if not cls.crossref_accessible:
            print(
                "\nWarning: CrossRef API is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = CrossRefSearcher()

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_search_basic(self):
        """Test basic search functionality."""
        results = self.searcher.search("machine learning", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertEqual(paper.source, "crossref")

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.searcher.search("", max_results=3)
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_search_max_results(self):
        """Test max_results parameter."""
        results = self.searcher.search("cryptography", max_results=2)
        self.assertLessEqual(len(results), 2)

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_get_paper_by_doi(self):
        """Test getting paper by DOI."""
        # Use a known DOI
        test_doi = "10.1038/nature12373"

        paper = self.searcher.get_paper_by_doi(test_doi)

        if paper:
            self.assertEqual(paper.doi, test_doi)
            self.assertTrue(paper.title)
            self.assertIsInstance(paper.authors, list)
        else:
            print(f"Could not fetch paper with DOI: {test_doi}")

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_get_paper_by_invalid_doi(self):
        """Test getting paper by invalid DOI."""
        paper = self.searcher.get_paper_by_doi("10.9999/invalid.doi.that.does.not.exist")
        self.assertIsNone(paper)

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_download_pdf_raises_error(self):
        """Test that download_pdf raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.searcher.download_pdf("10.1038/nature12373", "./downloads")

    @unittest.skipUnless(check_crossref_accessible(), "CrossRef not accessible")
    def test_read_paper_returns_error_message(self):
        """Test that read_paper returns an error message."""
        result = self.searcher.read_paper("10.1038/nature12373", "./downloads")
        self.assertIsInstance(result, str)
        self.assertIn("cannot", result.lower())


class TestCrossRefSearcherUnit(unittest.TestCase):
    """Unit tests for CrossRefSearcher without network."""

    def setUp(self):
        self.searcher = CrossRefSearcher()

    def test_extract_title_with_list(self):
        """Test title extraction from CrossRef item."""
        item = {"title": ["Test Title"]}
        title = self.searcher._extract_title(item)
        self.assertEqual(title, "Test Title")

    def test_extract_title_empty(self):
        """Test title extraction with empty title."""
        item = {"title": []}
        title = self.searcher._extract_title(item)
        self.assertEqual(title, "")

    def test_extract_authors(self):
        """Test author extraction from CrossRef item."""
        item = {
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"}
            ]
        }
        authors = self.searcher._extract_authors(item)
        self.assertEqual(authors, ["John Doe", "Jane Smith"])

    def test_extract_authors_partial(self):
        """Test author extraction with partial info."""
        item = {
            "author": [
                {"family": "Doe"},
                {"given": "Jane"}
            ]
        }
        authors = self.searcher._extract_authors(item)
        self.assertEqual(authors, ["Doe", "Jane"])

    def test_extract_date(self):
        """Test date extraction from CrossRef item."""
        item = {
            "published": {
                "date-parts": [[2023, 6, 15]]
            }
        }
        date = self.searcher._extract_date(item, "published")
        self.assertIsNotNone(date)
        self.assertEqual(date.year, 2023)
        self.assertEqual(date.month, 6)
        self.assertEqual(date.day, 15)

    def test_extract_container_title(self):
        """Test container title extraction."""
        item = {
            "container-title": ["Nature", "Science"]
        }
        container = self.searcher._extract_container_title(item)
        self.assertEqual(container, "Nature")


if __name__ == "__main__":
    unittest.main()
