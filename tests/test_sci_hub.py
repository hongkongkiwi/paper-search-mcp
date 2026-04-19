import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from paper_search_mcp.academic_platforms.sci_hub import SciHubFetcher


class TestSciHubFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = SciHubFetcher(mirrors=["https://mirror-1", "https://mirror-2"])

    def test_init(self):
        self.assertEqual(self.fetcher.mirrors, ["https://mirror-1", "https://mirror-2"])
        self.assertEqual(self.fetcher._failed_mirrors, set())
        self.assertIsNotNone(self.fetcher.session)

    def test_download_pdf_empty_query(self):
        self.assertEqual(
            self.fetcher.download_pdf(""),
            "Error: empty identifier provided to Sci-Hub downloader",
        )
        self.assertEqual(
            self.fetcher.download_pdf("   "),
            "Error: empty identifier provided to Sci-Hub downloader",
        )

    def test_generate_filename(self):
        response = Mock()
        response.url = "https://example.com/paper.pdf"
        response.content = b"fake pdf content"
        filename = self.fetcher._generate_filename(response, "10.1234/test")
        self.assertTrue(filename.endswith(".pdf"))
        self.assertIn("_paper.pdf", filename)

        response.url = "https://example.com/page"
        filename = self.fetcher._generate_filename(response, "test-paper")
        self.assertTrue(filename.endswith(".pdf"))
        self.assertIn("test-paper", filename)

    def test_get_direct_url_pdf_url(self):
        pdf_url = "https://example.com/paper.pdf"
        result = self.fetcher._get_direct_url(pdf_url, "https://mirror-1")
        self.assertEqual(result, pdf_url)

    def test_session_headers(self):
        self.assertIn("User-Agent", self.fetcher.session.headers)
        self.assertIn("Mozilla", self.fetcher.session.headers["User-Agent"])

    def test_download_pdf_creates_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "nested", "downloads")
            response = Mock()
            response.status_code = 200
            response.headers = {"Content-Type": "application/pdf"}
            response.content = b"%PDF-1.4 fake"
            response.url = "https://example.com/paper.pdf"

            with patch.object(self.fetcher, "_get_direct_url", return_value="https://example.com/paper.pdf"):
                with patch.object(self.fetcher.session, "get", return_value=response):
                    result = self.fetcher.download_pdf("10.1234/test", save_path)

            assert result is not None
            self.assertTrue(os.path.exists(save_path))
            self.assertTrue(os.path.exists(result))
            self.assertTrue(result.endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
