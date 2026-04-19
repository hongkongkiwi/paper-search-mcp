import asyncio
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import requests

from paper_search_mcp import server
from paper_search_mcp.academic_platforms.sci_hub import SciHubFetcher
from paper_search_mcp.academic_platforms.semantic import SemanticSearcher
from paper_search_mcp.http_status import is_pdf_response
from paper_search_mcp.paper import Paper


def status_response(status_code: int, reason: str) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.reason = reason
    response.headers = {}
    response.content = b""
    response.text = ""
    return response


def http_error_response(status_code: int, reason: str) -> Mock:
    response = status_response(status_code, reason)
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


class TestHttpStatusReporting(unittest.TestCase):
    def test_search_crossref_reports_http_status(self):
        response = status_response(503, "Service Unavailable")

        with patch.object(server.crossref_searcher.session, "get", return_value=response):
            result = asyncio.run(server.search_crossref("transformers"))

        self.assertIn("remote service error (HTTP 503 Service Unavailable)", result[0]["error"])

    def test_get_crossref_paper_by_doi_reports_http_status(self):
        response = status_response(404, "Not Found")

        with patch.object(server.crossref_searcher.session, "get", return_value=response):
            result = asyncio.run(server.get_crossref_paper_by_doi("10.9999/missing"))

        self.assertIn("resource not found (HTTP 404 Not Found)", result["error"])

    def test_search_openalex_reports_http_status(self):
        response = status_response(500, "Internal Server Error")

        with patch.object(server.openalex_searcher.session, "get", return_value=response):
            result = asyncio.run(server.search_openalex("graph neural networks"))

        self.assertIn("remote service error (HTTP 500 Internal Server Error)", result[0]["error"])

    def test_get_openalex_paper_reports_http_status(self):
        response = status_response(404, "Not Found")

        with patch.object(server.openalex_searcher.session, "get", return_value=response):
            result = asyncio.run(server.get_openalex_paper("W404"))

        self.assertIn("resource not found (HTTP 404 Not Found)", result["error"])

    def test_search_semantic_reports_http_status(self):
        response = status_response(503, "Service Unavailable")

        with patch.object(SemanticSearcher, "get_api_key", return_value=None):
            with patch.object(server.semantic_searcher.session, "get", return_value=response):
                result = asyncio.run(server.search_semantic("secret sharing", max_results=1))

        self.assertIn("remote service error (HTTP 503 Service Unavailable)", result[0]["error"])

    def test_search_biorxiv_reports_final_http_status_after_retries(self):
        response = http_error_response(502, "Bad Gateway")

        with patch.object(server.biorxiv_searcher.session, "get", return_value=response) as mock_get:
            result = asyncio.run(server.search_biorxiv("cell biology", max_results=1))

        self.assertEqual(mock_get.call_count, server.biorxiv_searcher.max_retries)
        self.assertIn("remote service error (HTTP 502 Bad Gateway)", result[0]["error"])

    def test_search_dblp_returns_empty_list_for_204(self):
        response = status_response(204, "No Content")

        with patch.object(server.dblp_searcher.session, "get", return_value=response):
            result = asyncio.run(server.search_dblp("attention", max_results=1))

        self.assertEqual(result, [])

    def test_read_openalex_paper_returns_http_status_in_error(self):
        paper = Paper(
            paper_id="W123",
            title="Test",
            authors=["Ada"],
            abstract="",
            doi="",
            published_date=datetime(2024, 1, 1),
            pdf_url="https://example.com/paper.pdf",
            url="https://example.com/paper",
            source="openalex",
            extra={"open_access": {"is_oa": True}, "has_fulltext": True},
        )
        response = status_response(403, "Forbidden")

        with patch.object(server.openalex_searcher, "get_paper_by_id", return_value=paper):
            with patch.object(server.openalex_searcher.session, "get", return_value=response):
                result = asyncio.run(server.read_openalex_paper("W123"))

        self.assertIn("access denied (HTTP 403 Forbidden)", result)

    def test_download_semantic_reports_paper_not_found_for_missing_doi(self):
        response = status_response(404, "Not Found")

        with tempfile.TemporaryDirectory() as save_path:
            with patch.object(SemanticSearcher, "get_api_key", return_value=None):
                with patch.object(server.semantic_searcher.session, "get", return_value=response):
                    result = asyncio.run(
                        server.download_semantic(
                            "DOI:10.1039/b403378c",
                            save_path=os.path.realpath(save_path),
                        )
                    )

        self.assertIn("Semantic Scholar paper lookup failed for DOI:10.1039/b403378c", result)
        self.assertIn("resource not found (HTTP 404 Not Found)", result)

    def test_is_pdf_response_accepts_pdf_content_type(self):
        response = Mock()
        response.headers = {"Content-Type": "application/pdf"}
        response.content = b"<!DOCTYPE html>"  # header wins
        self.assertTrue(is_pdf_response(response))

    def test_is_pdf_response_accepts_pdf_magic_bytes(self):
        response = Mock()
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.content = b"%PDF-1.4\n..."
        self.assertTrue(is_pdf_response(response))

    def test_is_pdf_response_rejects_html_challenge_page(self):
        response = Mock()
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.content = b"<!DOCTYPE html><html><head>Just a moment...</head>"
        self.assertFalse(is_pdf_response(response))

    def test_download_openalex_rejects_non_pdf_content(self):
        paper = Paper(
            paper_id="W123", title="Test", authors=["Ada"], abstract="",
            doi="", published_date=datetime(2024, 1, 1),
            pdf_url="https://example.com/paper.pdf",
            url="https://example.com/paper", source="openalex",
            extra={"open_access": {"is_oa": True}, "has_fulltext": True},
        )
        response = Mock()
        response.status_code = 200
        response.reason = "OK"
        response.headers = {"Content-Type": "text/html"}
        response.content = b"<!DOCTYPE html>"

        with patch.object(server.openalex_searcher, "get_paper_by_id", return_value=paper):
            with patch.object(server.openalex_searcher.session, "get", return_value=response):
                result = server.openalex_searcher.download_pdf("W123", "/tmp/claude")

        self.assertIn("non-PDF content", result)

    def test_download_openalex_skips_paywalled_paper(self):
        paper = Paper(
            paper_id="W999", title="Paywalled", authors=["Ada"], abstract="",
            doi="", published_date=datetime(2024, 1, 1),
            pdf_url="https://example.com/paper.pdf",
            url="https://example.com/paper", source="openalex",
            extra={"open_access": {"is_oa": False}, "has_fulltext": False},
        )

        with patch.object(server.openalex_searcher, "get_paper_by_id", return_value=paper):
            with patch.object(server.openalex_searcher.session, "get") as mock_get:
                result = server.openalex_searcher.download_pdf("W999", "/tmp/claude")

        mock_get.assert_not_called()
        self.assertIn("is_oa=false", result)
        self.assertIn("has_fulltext=false", result)

    def test_download_scihub_reports_mirror_statuses(self):
        fetcher = SciHubFetcher(mirrors=["https://mirror-1", "https://mirror-2"])
        responses = [
            status_response(403, "Forbidden"),
            status_response(503, "Service Unavailable"),
        ]

        with tempfile.TemporaryDirectory() as save_path:
            with patch("paper_search_mcp.server.scihub_fetcher", fetcher):
                with patch.object(fetcher.session, "get", side_effect=responses):
                    result = asyncio.run(
                        server.download_scihub(
                            "10.1000/test",
                            save_path=os.path.realpath(save_path),
                        )
                    )

        self.assertIn("'https://mirror-1': 403", result)
        self.assertIn("'https://mirror-2': 503", result)
