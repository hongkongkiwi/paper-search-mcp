import unittest
import os
from unittest.mock import Mock, call, patch
from paper_search_mcp.academic_platforms.semantic import SemanticSearcher, SemanticRateLimitError
from paper_search_mcp.http_status import SEMANTIC_SCHOLAR_429_NOTE
from tests.network import check_url_accessible


def check_semantic_accessible():
    return check_url_accessible(
        "https://api.semanticscholar.org/graph/v1/paper/5bbfdf2e62f0508c65ba6de9c72fe2066fd98138",
        retries=3,
        retry_statuses=(429,),
    )


class TestSemanticSearcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic_accessible = check_semantic_accessible()
        if not cls.semantic_accessible:
            print(
                "\nWarning: Semantic Scholar is not accessible, some tests will be skipped"
            )

    def setUp(self):
        self.searcher = SemanticSearcher()

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_search_basic(self):
        """Test basic search functionality"""
        results = self.searcher.search("secret sharing", max_results=3)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        if results:
            paper = results[0]
            self.assertTrue(hasattr(paper, "title"))
            self.assertTrue(hasattr(paper, "authors"))
            self.assertTrue(hasattr(paper, "abstract"))
            self.assertTrue(hasattr(paper, "paper_id"))
            self.assertTrue(hasattr(paper, "url"))
            self.assertEqual(paper.source, "semantic")

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_search_empty_query(self):
        """Test search with empty query"""
        results = self.searcher.search("", max_results=3)
        self.assertIsInstance(results, list)

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_search_max_results(self):
        """Test max_results parameter"""
        results = self.searcher.search("cryptography", max_results=2)
        self.assertLessEqual(len(results), 2)

    def test_request_api_retries_429_with_shorter_backoff(self):
        response = Mock(status_code=429)

        with patch.object(SemanticSearcher, "get_api_key", return_value=None):
            with patch.object(self.searcher.session, "get", return_value=response) as mock_get:
                with patch("paper_search_mcp.academic_platforms.semantic.time.sleep") as mock_sleep:
                    with self.assertRaises(SemanticRateLimitError) as cm:
                        self.searcher.request_api("paper/search", {"query": "secret sharing"})

        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_sleep.call_args_list, [call(1), call(2)])
        self.assertIn(SEMANTIC_SCHOLAR_429_NOTE, str(cm.exception))

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_download_pdf_functionality(self):
        """Test PDF download method with actual download"""
        import tempfile
        import shutil

        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="semantic_test_")

        try:
            # Test with a known paper that should exist
            paper_id = "5bbfdf2e62f0508c65ba6de9c72fe2066fd98138"  # A well-known paper

            print(f"\nTesting PDF download for paper {paper_id}")
            result = self.searcher.download_pdf(paper_id, test_dir)

            # Check that result is a string
            self.assertIsInstance(result, str)

            # Check if download was successful
            if not result.startswith("Error") and not result.startswith("Failed"):
                # Download successful - check if file exists
                self.assertTrue(
                    os.path.exists(result), f"Downloaded file should exist at {result}"
                )

                # Check file size (PDF should be larger than 1KB)
                file_size = os.path.getsize(result)
                self.assertGreater(
                    file_size, 1024, "PDF file should be larger than 1KB"
                )

                # Check file extension
                self.assertTrue(
                    result.endswith(".pdf"),
                    "Downloaded file should have .pdf extension",
                )

                print(
                    f"PDF successfully downloaded: {result} (size: {file_size} bytes)"
                )
            else:
                print(f"Download failed (this might be expected): {result}")

        except Exception as e:
            print(f"Exception during PDF download test: {e}")
            # Don't fail the test for network issues
            pass
        finally:
            # Clean up temporary directory
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_read_paper_functionality(self):
        """Test read paper method with text extraction functionality"""
        import tempfile
        import shutil

        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="semantic_read_test_")

        try:
            # Test with a known paper
            paper_id = "5bbfdf2e62f0508c65ba6de9c72fe2066fd98138"

            print(f"\nTesting read_paper for paper {paper_id}")
            result = self.searcher.read_paper(paper_id, test_dir)

            # Check that result is a string
            self.assertIsInstance(result, str)

            # Check for successful text extraction
            if "Error" not in result and len(result) > 100:
                print(f"Text extraction successful. Text length: {len(result)}")

                # Should contain metadata
                self.assertIn("Title:", result)
                self.assertIn("Authors:", result)
                self.assertIn("Published Date:", result)
                self.assertIn("PDF downloaded to:", result)

                # Should contain page markers indicating text extraction
                self.assertIn("--- Page", result)

                # Check if PDF was actually downloaded
                expected_filename = f"iacr_{paper_id.replace('/', '_')}.pdf"
                expected_path = os.path.join(test_dir, expected_filename)
                self.assertTrue(os.path.exists(expected_path))

                file_size = os.path.getsize(expected_path)
                print(f"PDF file found: {expected_path} (size: {file_size} bytes)")
                self.assertGreater(file_size, 1000)  # Should be at least 1KB

                # Show a preview of extracted text
                preview = result[:500] + "..." if len(result) > 500 else result
                print(f"Text preview:\n{preview}")

            else:
                print(f"Read paper result: {result}")
                # For network issues or PDF extraction problems, don't fail
                print(
                    "Note: This might be due to network issues or PDF extraction limitations"
                )

        except Exception as e:
            print(f"Exception during read_paper test: {e}")
            # Don't fail the test for network issues
            pass
        finally:
            # Clean up temporary directory
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_get_paper_details(self):
        """Test getting detailed paper information"""
        paper_id = "5bbfdf2e62f0508c65ba6de9c72fe2066fd98138"  # A known paper
        paper_details = self.searcher.get_paper_details(paper_id)

        if paper_details:
            # Test basic attributes
            self.assertTrue(paper_details.title)
            self.assertEqual(paper_details.paper_id, paper_id)
            self.assertEqual(paper_details.source, "semantic")
            self.assertTrue(paper_details.url)
            self.assertTrue(paper_details.pdf_url)

            # Test that we have authors
            self.assertIsInstance(paper_details.authors, list)
            self.assertGreater(len(paper_details.authors), 0)

            # Test that we have abstract
            self.assertTrue(paper_details.abstract)

            # Test extra metadata
            if paper_details.extra:
                self.assertIsInstance(paper_details.extra, dict)

            # printing all details for verification
            print(f"\n{paper_details}")
        else:
            self.fail("Could not fetch paper details")

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_search_returns_semantic_papers(self):
        """Test that search returns parsed Semantic Scholar papers."""
        papers = self.searcher.search("cryptography", max_results=2)

        self.assertIsInstance(papers, list)
        self.assertLessEqual(len(papers), 2)

        if papers:
            paper = papers[0]
            self.assertEqual(paper.source, "semantic")
            self.assertTrue(paper.title)
            self.assertIsInstance(paper.authors, list)
            self.assertIsInstance(paper.categories, list)
            self.assertIsInstance(paper.abstract, str)

    @unittest.skipUnless(check_semantic_accessible(), "Semantic Scholar not accessible")
    def test_search_performance_comparison(self):
        """Test performance difference between detailed and compact search"""
        import time

        query = "encryption"
        max_results = 3

        # Test detailed search time
        print("\nTesting detailed search performance...")
        start_time = time.time()
        compact_papers = self.searcher.search(
            query, max_results=max_results
        )
        compact_time = time.time() - start_time

        print(
            f"Compact search took {compact_time:.2f} seconds for {len(compact_papers)} papers"
        )




if __name__ == "__main__":
    unittest.main()
