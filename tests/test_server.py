# tests/test_server.py
import unittest
import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from paper_search_mcp import server
from paper_search_mcp.academic_platforms.semantic import SemanticRateLimitError
from paper_search_mcp.paper import Paper

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
            expected_path = os.path.realpath(os.path.join(workspace_dir, "downloads"))

            class FakeSession:
                def check_client_capability(self, capability):
                    return True

                async def list_roots(self):
                    root = SimpleNamespace(uri=Path(workspace_dir).resolve().as_uri())
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

    def test_download_scihub_uses_client_root_for_relative_save_path(self):
        with tempfile.TemporaryDirectory() as workspace_dir:
            expected_path = os.path.realpath(os.path.join(workspace_dir, "downloads"))

            class FakeSession:
                def check_client_capability(self, capability):
                    return True

                async def list_roots(self):
                    root = SimpleNamespace(uri=Path(workspace_dir).resolve().as_uri())
                    return SimpleNamespace(roots=[root])

            ctx = SimpleNamespace(session=FakeSession())

            def fake_download_pdf(identifier, save_path):
                self.assertEqual(save_path, expected_path)
                return os.path.join(save_path, "paper.pdf")

            with patch.object(server.scihub_fetcher, "download_pdf", side_effect=fake_download_pdf):
                result = asyncio.run(
                    server.download_scihub(
                        "10.1021/acs.analchem.8b02271",
                        ctx=ctx,
                    )
                )

        self.assertEqual(result, os.path.join(expected_path, "paper.pdf"))

    def test_download_scihub_rejects_relative_path_without_client_roots(self):
        result = asyncio.run(server.download_scihub("10.1021/acs.analchem.8b02271"))
        self.assertIn("relative save_path requires MCP client context", result)

    def test_resolve_save_path_rejects_missing_client_context(self):
        with self.assertRaisesRegex(ValueError, r"relative save_path requires MCP client context"):
            asyncio.run(server._resolve_save_path("./downloads"))

    def test_resolve_save_path_rejects_missing_client_roots_support(self):
        class FakeSession:
            def check_client_capability(self, capability):
                return False

        ctx = SimpleNamespace(session=FakeSession())

        with self.assertRaisesRegex(ValueError, r"relative save_path requires MCP client roots support"):
            asyncio.run(server._resolve_save_path("./downloads", ctx))

    def test_resolve_save_path_rejects_empty_roots_list(self):
        class FakeSession:
            def check_client_capability(self, capability):
                return True

            async def list_roots(self):
                return SimpleNamespace(roots=[])

        ctx = SimpleNamespace(session=FakeSession())

        with self.assertRaisesRegex(ValueError, r"Client advertised roots support but returned no roots"):
            asyncio.run(server._resolve_save_path("./downloads", ctx))

    def test_resolve_save_path_rejects_escape_outside_client_root(self):
        with tempfile.TemporaryDirectory() as workspace_dir:
            class FakeSession:
                def check_client_capability(self, capability):
                    return True

                async def list_roots(self):
                    root = SimpleNamespace(uri=Path(workspace_dir).resolve().as_uri())
                    return SimpleNamespace(roots=[root])

            ctx = SimpleNamespace(session=FakeSession())

            with self.assertRaisesRegex(ValueError, r"save_path escapes client root"):
                asyncio.run(server._resolve_save_path("../outside", ctx))

    def test_search_semantic_returns_rate_limit_error(self):
        message = (
            "Semantic Scholar API rate limited the request (HTTP 429) after 3 "
            "attempts. Wait a moment and retry, or set "
            "SEMANTIC_SCHOLAR_API_KEY for higher limits."
        )

        with patch.object(
            server.semantic_searcher,
            "search",
            side_effect=SemanticRateLimitError(message),
        ):
            result = asyncio.run(server.search_semantic("secret sharing", max_results=1))

        self.assertEqual(result, [{"error": message, "status_code": 429}])

    def test_search_arxiv(self):
        """Test the search_arxiv tool serializes search results."""
        papers = [
            Paper(
                paper_id="1234.5678",
                title="Paper One",
                authors=["Ada Lovelace"],
                abstract="A",
                doi="",
                url="https://arxiv.org/abs/1234.5678",
                pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
                published_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 2),
                source="arxiv",
            ),
            Paper(
                paper_id="2345.6789",
                title="Paper Two",
                authors=["Grace Hopper"],
                abstract="B",
                doi="",
                url="https://arxiv.org/abs/2345.6789",
                pdf_url="https://arxiv.org/pdf/2345.6789.pdf",
                published_date=datetime(2024, 2, 1),
                updated_date=datetime(2024, 2, 2),
                source="arxiv",
            ),
        ]

        with patch.object(server.arxiv_searcher, "search", return_value=papers):
            result = asyncio.run(server.search_arxiv("machine learning", max_results=10))

        self.assertIsInstance(result, list, "Result should be a list")
        self.assertEqual(len(result), 2, "Should return serialized search results")
        for paper in result:
            self.assertIn('title', paper, "Each result should contain a title")
            self.assertIn('paper_id', paper, "Each result should contain a paper_id")

    def test_download_arxiv_from_search(self):
        """Test downloading arXiv PDFs from search results without live network access."""
        papers = [
            Paper(
                paper_id="1234.5678",
                title="Paper One",
                authors=["Ada Lovelace"],
                abstract="A",
                doi="",
                url="https://arxiv.org/abs/1234.5678",
                pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
                published_date=datetime(2024, 1, 1),
                updated_date=datetime(2024, 1, 2),
                source="arxiv",
            ),
            Paper(
                paper_id="2345.6789",
                title="Paper Two",
                authors=["Grace Hopper"],
                abstract="B",
                doi="",
                url="https://arxiv.org/abs/2345.6789",
                pdf_url="https://arxiv.org/pdf/2345.6789.pdf",
                published_date=datetime(2024, 2, 1),
                updated_date=datetime(2024, 2, 2),
                source="arxiv",
            ),
        ]

        with tempfile.TemporaryDirectory() as save_path:
            def fake_download_pdf(paper_id, resolved_save_path):
                file_path = os.path.join(resolved_save_path, f"{paper_id}.pdf")
                with open(file_path, "wb") as handle:
                    handle.write(b"%PDF-1.4 test")
                return file_path

            with patch.object(server.arxiv_searcher, "search", return_value=papers):
                search_results = asyncio.run(server.search_arxiv("machine learning", max_results=10))

            self.assertEqual(len(search_results), 2, "Search should return mocked results")

            with patch.object(server.arxiv_searcher, "download_pdf", side_effect=fake_download_pdf):
                for paper in search_results:
                    paper_id = paper['paper_id']
                    result = asyncio.run(server.download_arxiv(paper_id, save_path))
                    self.assertIsInstance(result, str, f"Result for {paper_id} should be a file path")
                    self.assertTrue(result.endswith(".pdf"), f"Result for {paper_id} should be a PDF file path")
                    self.assertTrue(os.path.exists(result), f"PDF file for {paper_id} should exist on disk")

if __name__ == "__main__":
    unittest.main()
