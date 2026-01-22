"""Tests for PubMed Central searcher."""
import unittest
import requests
from paper_search_mcp.academic_platforms.pmc import PMCSearcher


def check_pmc_accessible():
    """Check if PMC API is accessible."""
    try:
        response = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term=cancer&retmax=1", timeout=5)
        return response.status_code == 200
    except:
        return False


class TestPMCSearcher(unittest.TestCase):
    """Tests for PMCSearcher class."""

    @classmethod
    def setUpClass(cls):
        cls.pmc_accessible = check_pmc_accessible()
        if not cls.pmc_accessible:
            print(
                "\nWarning: PMC API is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = PMCSearcher()

    @unittest.skipUnless(check_pmc_accessible(), "PMC not accessible")
    def test_search_basic(self):
        """Test basic search functionality."""
        results = self.searcher.search("cancer", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertEqual(paper.source, "pmc")

    @unittest.skipUnless(check_pmc_accessible(), "PMC not accessible")
    def test_search_with_year_filter(self):
        """Test search with year filter."""
        results = self.searcher.search("immunotherapy", max_results=3, year="2022")
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_pmc_accessible(), "PMC not accessible")
    def test_get_paper_by_pmcid(self):
        """Test getting paper by PMCID."""
        test_pmcid = "PMC1234567"

        paper = self.searcher.get_paper_by_pmcid(test_pmcid)

        # Paper may or may not exist, but should not raise an error
        if paper:
            self.assertTrue(paper.title)
        else:
            print(f"Could not fetch paper with PMCID: {test_pmcid}")


class TestPMCSearcherUnit(unittest.TestCase):
    """Unit tests for PMCSearcher without network."""

    def setUp(self):
        self.searcher = PMCSearcher()

    def test_session_created(self):
        """Test that session is created on initialization."""
        self.assertTrue(hasattr(self.searcher, 'session'))
        self.assertIsNotNone(self.searcher.session)


if __name__ == "__main__":
    unittest.main()
