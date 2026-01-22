"""Tests for deduplication module."""
import unittest
from datetime import datetime
from paper_search_mcp.paper import Paper
from paper_search_mcp.deduplication import Deduplicator, ContentHasher, TFIDFSimilarity


class TestContentHasher(unittest.TestCase):
    """Tests for ContentHasher class."""

    def test_hash_paper(self):
        """Test hashing a paper."""
        hasher = ContentHasher()

        paper = Paper(
            paper_id="test1",
            title="Test Paper",
            authors=["Author A", "Author B"],
            abstract="This is a test abstract",
            doi="10.1234/test",
            published_date=datetime(2023, 1, 1),
            pdf_url="https://example.com/test.pdf",
            url="https://example.com/test",
            source="test",
            categories=["test"],
            keywords=["testing"],
            citations=0,
            references=[]
        )

        hash1 = hasher.hash_paper(paper)
        hash2 = hasher.hash_paper(paper)

        self.assertIsNotNone(hash1)
        self.assertEqual(hash1, hash2)

    def test_hash_different_papers_same_content(self):
        """Test that papers with same content get same hash."""
        hasher = ContentHasher()

        paper1 = Paper(
            paper_id="test1",
            title="Test Paper",
            authors=["Author A"],
            abstract="This is a test abstract",
            doi="10.1234/test",
            published_date=datetime(2023, 1, 1),
            pdf_url="https://example.com/test.pdf",
            url="https://example.com/test",
            source="test",
            categories=["test"],
            keywords=[],
            citations=0,
            references=[]
        )

        paper2 = Paper(
            paper_id="test2",
            title="Test Paper",
            authors=["Author A"],
            abstract="This is a test abstract",
            doi="10.5678/test",
            published_date=datetime(2023, 1, 1),
            pdf_url="https://example.com/test.pdf",
            url="https://example.com/test",
            source="test",
            categories=["test"],
            keywords=[],
            citations=0,
            references=[]
        )

        self.assertEqual(hasher.hash_paper(paper1), hasher.hash_paper(paper2))


class TestTFIDFSimilarity(unittest.TestCase):
    """Tests for TFIDFSimilarity class."""

    def test_compute_similarity(self):
        """Test computing similarity between two papers."""
        similarity = TFIDFSimilarity()

        paper1 = Paper(
            paper_id="test1",
            title="Machine Learning Neural Networks",
            authors=["Author A"],
            abstract="This paper discusses machine learning approaches using neural networks",
            doi="10.1234/test1",
            published_date=datetime(2023, 1, 1),
            pdf_url="",
            url="https://example.com/test1",
            source="test",
            categories=["ML"],
            keywords=["machine learning", "neural networks"],
            citations=0,
            references=[]
        )

        paper2 = Paper(
            paper_id="test2",
            title="Deep Learning and Neural Networks",
            authors=["Author B"],
            abstract="This paper explores deep learning with neural networks",
            doi="10.1234/test2",
            published_date=datetime(2023, 2, 1),
            pdf_url="",
            url="https://example.com/test2",
            source="test",
            categories=["ML"],
            keywords=["deep learning", "neural networks"],
            citations=0,
            references=[]
        )

        sim = similarity.compute_similarity(paper1, paper2)

        self.assertIsInstance(sim, float)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)


class TestDeduplicator(unittest.TestCase):
    """Tests for Deduplicator class."""

    def test_remove_duplicates_by_title(self):
        """Test removing duplicate papers by title."""
        deduplicator = Deduplicator(strategy="title")

        papers = [
            Paper(
                paper_id="test1",
                title="Test Paper",
                authors=["Author A"],
                abstract="Abstract 1",
                doi="10.1234/test1",
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="test",
                categories=["test"],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Test Paper",
                authors=["Author B"],
                abstract="Abstract 2",
                doi="10.5678/test2",
                published_date=datetime(2023, 1, 2),
                pdf_url="",
                url="https://example.com/test2",
                source="test",
                categories=["test"],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test3",
                title="Different Paper",
                authors=["Author C"],
                abstract="Abstract 3",
                doi="10.9999/test3",
                published_date=datetime(2023, 1, 3),
                pdf_url="",
                url="https://example.com/test3",
                source="test",
                categories=["test"],
                keywords=[],
                citations=0,
                references=[]
            ),
        ]

        unique = deduplicator.remove_duplicates(papers)

        self.assertEqual(len(unique), 2)
        titles = [p.title for p in unique]
        self.assertIn("Test Paper", titles)
        self.assertIn("Different Paper", titles)

    def test_remove_duplicates_empty_list(self):
        """Test removing duplicates from empty list."""
        deduplicator = Deduplicator(strategy="title")
        result = deduplicator.remove_duplicates([])
        self.assertEqual(result, [])

    def test_cluster_similar(self):
        """Test clustering similar papers."""
        deduplicator = Deduplicator(similarity_threshold=0.3)

        papers = [
            Paper(
                paper_id="test1",
                title="Machine Learning Neural Networks",
                authors=["Author A"],
                abstract="This paper discusses machine learning approaches using neural networks",
                doi="10.1234/test1",
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="test",
                categories=["ML"],
                keywords=["machine learning", "neural networks"],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Deep Learning and Neural Networks",
                authors=["Author B"],
                abstract="This paper explores deep learning with neural networks",
                doi="10.1234/test2",
                published_date=datetime(2023, 2, 1),
                pdf_url="",
                url="https://example.com/test2",
                source="test",
                categories=["ML"],
                keywords=["deep learning", "neural networks"],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test3",
                title="Quantum Computing Algorithms",
                authors=["Author C"],
                abstract="This paper presents quantum computing algorithms",
                doi="10.9999/test3",
                published_date=datetime(2023, 1, 3),
                pdf_url="",
                url="https://example.com/test3",
                source="test",
                categories=["Quantum"],
                keywords=["quantum", "computing"],
                citations=0,
                references=[]
            ),
        ]

        clusters = deduplicator.cluster_similar(papers)

        # Should have at least 2 clusters (ML papers together, quantum separate)
        self.assertGreaterEqual(len(clusters), 2)

        # Check that test1 and test2 are in the same cluster
        ml_cluster = None
        for cluster in clusters:
            paper_ids = [p.paper_id for p in cluster]
            if "test1" in paper_ids and "test2" in paper_ids:
                ml_cluster = cluster
                break

        self.assertIsNotNone(ml_cluster)


if __name__ == "__main__":
    unittest.main()
