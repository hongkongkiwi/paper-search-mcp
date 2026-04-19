# tests/test_server.py
import unittest
import asyncio
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from paper_search_mcp import server

class TestPaperSearchServer(unittest.TestCase):
    def test_download_pubmed_returns_not_supported_message(self):
        message = "PubMed does not provide direct PDF downloads."

        with patch.object(server.pubmed_searcher, "download_pdf", side_effect=NotImplementedError(message)):
            result = asyncio.run(server.download_pubmed("12345"))

        self.assertEqual(result, message)

    def test_download_crossref_returns_not_supported_message(self):
        message = "CrossRef does not provide direct PDF downloads."

        with patch.object(server.crossref_searcher, "download_pdf", side_effect=NotImplementedError(message)):
            result = asyncio.run(server.download_crossref("10.1000/example"))

        self.assertEqual(result, message)

    def test_download_semantic_uses_client_root_for_relative_save_path(self):
        with tempfile.TemporaryDirectory() as workspace_dir:
            expected_path = os.path.join(workspace_dir, "downloads")

            class FakeSession:
                def check_client_capability(self, capability):
                    return True

                async def list_roots(self):
                    root = SimpleNamespace(uri=Path(workspace_dir).as_uri())
                    return SimpleNamespace(roots=[root])

            ctx = SimpleNamespace(session=FakeSession())

            def fake_download_pdf(paper_id, save_path):
                self.assertEqual(save_path, expected_path)
                return os.path.join(save_path, "paper.pdf")

            with patch.object(server.semantic_searcher, "download_pdf", side_effect=fake_download_pdf):
                result = asyncio.run(
                    server.download_semantic(
                        "DOI:10.1186/s13071-023-06098-0",
                        ctx=ctx,
                    )
                )

        self.assertEqual(result, os.path.join(expected_path, "paper.pdf"))

    def test_search_arxiv(self):
        """Test the search_arxiv tool returns 10 results."""
        result = asyncio.run(server.search_arxiv("machine learning", max_results=10))
        self.assertIsInstance(result, list, "Result should be a list")
        self.assertEqual(len(result), 10, "Should return exactly 10 results")
        for paper in result:
            self.assertIn('title', paper, "Each result should contain a title")
            self.assertIn('paper_id', paper, "Each result should contain a paper_id")

    def test_download_arxiv_from_search(self):
        """Test downloading 10 arXiv papers based on search results."""
        # 先搜索 10 个结果
        search_results = asyncio.run(server.search_arxiv("machine learning", max_results=10))
        self.assertEqual(len(search_results), 10, "Search should return 10 results")

        # 下载目录
        save_path = "./downloads"
        os.makedirs(save_path, exist_ok=True)  # 确保目录存在

        # 下载每个搜索结果的 PDF
        for paper in search_results:
            paper_id = paper['paper_id']
            result = asyncio.run(server.download_arxiv(paper_id, save_path))
            self.assertIsInstance(result, str, f"Result for {paper_id} should be a file path")
            self.assertTrue(result.endswith(".pdf"), f"Result for {paper_id} should be a PDF file path")
            self.assertTrue(os.path.exists(result), f"PDF file for {paper_id} should exist on disk")

if __name__ == "__main__":
    unittest.main()
