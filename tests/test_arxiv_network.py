import os
import tempfile
import unittest

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher
from tests.network import check_url_accessible


def check_arxiv_accessible():
    return check_url_accessible("http://export.arxiv.org/api/query?search_query=all:test&max_results=1")


class TestArxivSearcherNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arxiv_accessible = check_arxiv_accessible()
        if not cls.arxiv_accessible:
            print("\nWarning: arXiv API is not accessible, some tests will be skipped")

    def setUp(self):
        self.searcher = ArxivSearcher()

    @unittest.skipUnless(check_arxiv_accessible(), "arXiv not accessible")
    def test_search_basic(self):
        papers = self.searcher.search("machine learning", max_results=3)

        self.assertIsInstance(papers, list)
        self.assertLessEqual(len(papers), 3)
        self.assertTrue(papers)
        self.assertTrue(papers[0].title)
        self.assertEqual(papers[0].source, "arxiv")

    @unittest.skipUnless(check_arxiv_accessible(), "arXiv not accessible")
    def test_download_pdf(self):
        papers = self.searcher.search("machine learning", max_results=1)
        self.assertTrue(papers)

        with tempfile.TemporaryDirectory() as save_path:
            result = self.searcher.download_pdf(papers[0].paper_id, save_path)

            self.assertIsInstance(result, str)
            self.assertTrue(result.endswith(".pdf"))
            self.assertTrue(os.path.exists(result))


if __name__ == "__main__":
    unittest.main()
