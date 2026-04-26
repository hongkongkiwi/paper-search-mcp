import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher


class TestArxivSearcher(unittest.TestCase):
    def test_search(self):
        response = Mock()
        response.status_code = 200
        response.reason = "OK"
        response.content = b"""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1234.5678v1</id>
            <updated>2024-01-02T03:04:05Z</updated>
            <published>2024-01-01T03:04:05Z</published>
            <title>Test Paper</title>
            <summary>Test abstract</summary>
            <author><name>Ada Lovelace</name></author>
            <link href="http://arxiv.org/abs/1234.5678v1" rel="alternate" type="text/html"/>
            <link href="http://arxiv.org/pdf/1234.5678v1" rel="related" type="application/pdf"/>
            <category term="cs.LG"/>
          </entry>
        </feed>
        """

        with patch("paper_search_mcp.academic_platforms.arxiv.requests.get", return_value=response):
            papers = ArxivSearcher().search("machine learning", max_results=10)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].paper_id, "1234.5678v1")
        self.assertEqual(papers[0].title, "Test Paper")
        self.assertEqual(papers[0].authors, ["Ada Lovelace"])
        self.assertEqual(papers[0].published_date, datetime(2024, 1, 1, 3, 4, 5))


if __name__ == "__main__":
    unittest.main()
