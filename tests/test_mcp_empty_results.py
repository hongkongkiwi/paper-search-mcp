import asyncio
import unittest
from datetime import datetime
from unittest.mock import patch

from paper_search_mcp import server
from paper_search_mcp.paper import Paper


class TestMCPEmptyResults(unittest.TestCase):
    def test_search_semantic_direct_call_still_returns_empty_list(self):
        with patch.object(server.semantic_searcher, "search", return_value=[]):
            result = asyncio.run(server.search_semantic("missing", max_results=1))

        self.assertEqual(result, [])

    def test_search_semantic_mcp_call_wraps_empty_list(self):
        with patch.object(server.semantic_searcher, "search", return_value=[]):
            result = asyncio.run(
                server.mcp.call_tool(
                    "search_semantic",
                    {"query": "missing", "max_results": 1},
                )
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(result[0].text, "No results found (zero matches).")

    def test_search_semantic_mcp_call_keeps_non_empty_results(self):
        paper = Paper(
            paper_id="paper-1",
            title="Test Paper",
            authors=["Ada Lovelace"],
            abstract="",
            doi="",
            published_date=datetime(2024, 1, 1),
            pdf_url="",
            url="https://example.com/paper-1",
            source="semantic",
        )

        with patch.object(server.semantic_searcher, "search", return_value=[paper]):
            result = asyncio.run(
                server.mcp.call_tool(
                    "search_semantic",
                    {"query": "test", "max_results": 1},
                )
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn('"paper_id": "paper-1"', result[0].text)
        self.assertIn('"title": "Test Paper"', result[0].text)
