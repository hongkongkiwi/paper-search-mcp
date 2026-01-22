"""Tests for deduplication module."""
import unittest
from datetime import datetime
from paper_search_mcp.paper import Paper
from paper_search_mcp.deduplication import (
    normalize_doi,
    normalize_title,
    title_similarity,
    are_titles_similar,
    are_same_paper,
    deduplicate_papers,
    deduplicate_paper_dicts,
    find_duplicates,
    dict_to_paper
)


class TestNormalizeDOI(unittest.TestCase):
    """Tests for DOI normalization."""

    def test_normalize_doi(self):
        """Test DOI normalization."""
        doi1 = "10.1234/test"
        doi2 = "https://doi.org/10.1234/test"
        doi3 = "doi:10.1234/test"

        self.assertEqual(normalize_doi(doi1), "10.1234/test")
        self.assertEqual(normalize_doi(doi2), "10.1234/test")
        self.assertEqual(normalize_doi(doi3), "10.1234/test")

    def test_normalize_doi_empty(self):
        """Test normalizing empty DOI."""
        self.assertEqual(normalize_doi(""), "")
        self.assertEqual(normalize_doi(None), "")


class TestNormalizeTitle(unittest.TestCase):
    """Tests for title normalization."""

    def test_normalize_title(self):
        """Test title normalization."""
        title1 = "  Test Paper Title  "
        title2 = "Test Paper Title"
        title3 = "TEST PAPER TITLE"

        self.assertEqual(normalize_title(title1), "test paper title")
        self.assertEqual(normalize_title(title2), "test paper title")
        self.assertEqual(normalize_title(title3), "test paper title")

    def test_normalize_title_special_chars(self):
        """Test normalizing title with special characters."""
        title = "Test Paper: A New Approach!"
        normalized = normalize_title(title)
        self.assertIn("test paper", normalized)
        self.assertIn("new approach", normalized)


class TestTitleSimilarity(unittest.TestCase):
    """Tests for title similarity."""

    def test_identical_titles(self):
        """Test similarity of identical titles."""
        title = "Machine Learning and Neural Networks"
        self.assertEqual(title_similarity(title, title), 1.0)

    def test_similar_titles(self):
        """Test similarity of similar titles."""
        title1 = "Machine Learning and Neural Networks"
        title2 = "Machine Learning with Neural Networks"
        sim = title_similarity(title1, title2)
        self.assertGreater(sim, 0.8)

    def test_different_titles(self):
        """Test similarity of different titles."""
        title1 = "Machine Learning and Neural Networks"
        title2 = "Quantum Computing Algorithms"
        sim = title_similarity(title1, title2)
        self.assertLess(sim, 0.5)

    def test_are_titles_similar(self):
        """Test are_titles_similar function."""
        title1 = "Test Paper Title"
        title2 = "Test Paper Title"
        self.assertTrue(are_titles_similar(title1, title2))

        title3 = "Test Paper Title"
        title4 = "Different Paper Title"
        self.assertFalse(are_titles_similar(title3, title4))


class TestAreSamePaper(unittest.TestCase):
    """Tests for are_same_paper function."""

    def test_same_doi(self):
        """Test papers with same DOI are detected as same."""
        paper1 = Paper(
            paper_id="test1",
            title="Test Paper",
            authors=["Author A"],
            abstract="Abstract",
            doi="10.1234/test",
            published_date=datetime(2023, 1, 1),
            pdf_url="",
            url="https://example.com/test1",
            source="test",
            categories=[],
            keywords=[],
            citations=0,
            references=[]
        )

        paper2 = Paper(
            paper_id="test2",
            title="Different Title",
            authors=["Author B"],
            abstract="Different abstract",
            doi="10.1234/test",
            published_date=datetime(2023, 1, 2),
            pdf_url="",
            url="https://example.com/test2",
            source="test",
            categories=[],
            keywords=[],
            citations=0,
            references=[]
        )

        self.assertTrue(are_same_paper(paper1, paper2))

    def test_similar_title_authors_year(self):
        """Test papers with similar title, authors, and year."""
        paper1 = Paper(
            paper_id="test1",
            title="Machine Learning and Neural Networks",
            authors=["Author A", "Author B"],
            abstract="Abstract 1",
            doi="",
            published_date=datetime(2023, 1, 1),
            pdf_url="",
            url="https://example.com/test1",
            source="test",
            categories=[],
            keywords=[],
            citations=0,
            references=[]
        )

        paper2 = Paper(
            paper_id="test2",
            title="Machine Learning with Neural Networks",
            authors=["Author A", "Author B"],
            abstract="Abstract 2",
            doi="",
            published_date=datetime(2023, 5, 1),
            pdf_url="",
            url="https://example.com/test2",
            source="test",
            categories=[],
            keywords=[],
            citations=0,
            references=[]
        )

        self.assertTrue(are_same_paper(paper1, paper2))

    def test_different_papers(self):
        """Test that different papers are not detected as same."""
        paper1 = Paper(
            paper_id="test1",
            title="Machine Learning",
            authors=["Author A"],
            abstract="Abstract 1",
            doi="10.1234/test1",
            published_date=datetime(2023, 1, 1),
            pdf_url="",
            url="https://example.com/test1",
            source="test",
            categories=[],
            keywords=[],
            citations=0,
            references=[]
        )

        paper2 = Paper(
            paper_id="test2",
            title="Quantum Computing",
            authors=["Author B"],
            abstract="Abstract 2",
            doi="10.5678/test2",
            published_date=datetime(2023, 1, 2),
            pdf_url="",
            url="https://example.com/test2",
            source="test",
            categories=[],
            keywords=[],
            citations=0,
            references=[]
        )

        self.assertFalse(are_same_paper(paper1, paper2))


class TestDeduplicatePapers(unittest.TestCase):
    """Tests for deduplicate_papers function."""

    def test_remove_duplicates_by_doi(self):
        """Test removing duplicate papers by DOI."""
        papers = [
            Paper(
                paper_id="test1",
                title="Test Paper",
                authors=["Author A"],
                abstract="Abstract 1",
                doi="10.1234/test",
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="test",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Different Title",
                authors=["Author B"],
                abstract="Abstract 2",
                doi="10.1234/test",
                published_date=datetime(2023, 1, 2),
                pdf_url="",
                url="https://example.com/test2",
                source="test",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test3",
                title="Unique Paper",
                authors=["Author C"],
                abstract="Abstract 3",
                doi="10.5678/test",
                published_date=datetime(2023, 1, 3),
                pdf_url="",
                url="https://example.com/test3",
                source="test",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
        ]

        unique = deduplicate_papers(papers, keep="first")

        self.assertEqual(len(unique), 2)
        dois = [p.doi for p in unique]
        self.assertIn("10.1234/test", dois)
        self.assertIn("10.5678/test", dois)

    def test_remove_duplicates_by_title(self):
        """Test removing duplicate papers by title."""
        papers = [
            Paper(
                paper_id="test1",
                title="Test Paper Title",
                authors=["Author A"],
                abstract="Abstract 1",
                doi="",  # No DOI - will rely on title + author + year
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="test",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Test Paper Title",
                authors=["Author A"],  # Same author to trigger title+author+year match
                abstract="Abstract 2",
                doi="",  # No DOI
                published_date=datetime(2023, 5, 1),  # Same year
                pdf_url="",
                url="https://example.com/test2",
                source="test",
                categories=[],
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
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
        ]

        unique = deduplicate_papers(papers, keep="first")

        self.assertEqual(len(unique), 2)
        titles = [p.title for p in unique]
        self.assertIn("Test Paper Title", titles)
        self.assertIn("Different Paper", titles)

    def test_remove_duplicates_empty_list(self):
        """Test removing duplicates from empty list."""
        result = deduplicate_papers([])
        self.assertEqual(result, [])

    def test_keep_first(self):
        """Test keep='first' option."""
        papers = [
            Paper(
                paper_id="test1",
                title="Same Title",
                authors=["Author A"],
                abstract="First",
                doi="",
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="source1",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Same Title",
                authors=["Author A"],
                abstract="Second",
                doi="",
                published_date=datetime(2023, 1, 2),
                pdf_url="",
                url="https://example.com/test2",
                source="source2",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
        ]

        unique = deduplicate_papers(papers, keep="first")
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].paper_id, "test1")

    def test_keep_last(self):
        """Test keep='last' option."""
        papers = [
            Paper(
                paper_id="test1",
                title="Same Title",
                authors=["Author A"],
                abstract="First",
                doi="",
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="source1",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Same Title",
                authors=["Author A"],
                abstract="Second",
                doi="",
                published_date=datetime(2023, 1, 2),
                pdf_url="",
                url="https://example.com/test2",
                source="source2",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
        ]

        unique = deduplicate_papers(papers, keep="last")
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].paper_id, "test2")


class TestDeduplicatePaperDicts(unittest.TestCase):
    """Tests for deduplicate_paper_dicts function."""

    def test_deduplicate_dicts(self):
        """Test deduplicating paper dictionaries."""
        dicts = [
            {
                "paper_id": "test1",
                "title": "Test Paper",
                "authors": ["Author A"],
                "abstract": "Abstract 1",
                "doi": "10.1234/test",
                "published_date": "2023-01-01T00:00:00",
                "pdf_url": "",
                "url": "https://example.com/test1",
                "source": "test",
                "categories": [],
                "keywords": [],
                "citations": 0,
                "references": [],
                "extra": {}
            },
            {
                "paper_id": "test2",
                "title": "Test Paper",
                "authors": ["Author B"],
                "abstract": "Abstract 2",
                "doi": "10.1234/test",
                "published_date": "2023-01-02T00:00:00",
                "pdf_url": "",
                "url": "https://example.com/test2",
                "source": "test",
                "categories": [],
                "keywords": [],
                "citations": 0,
                "references": [],
                "extra": {}
            },
        ]

        unique = deduplicate_paper_dicts(dicts)
        self.assertEqual(len(unique), 1)


class TestFindDuplicates(unittest.TestCase):
    """Tests for find_duplicates function."""

    def test_find_duplicate_groups(self):
        """Test finding duplicate groups."""
        papers = [
            Paper(
                paper_id="test1",
                title="Same Title",
                authors=["Author A"],
                abstract="Abstract 1",
                doi="10.1234/test",
                published_date=datetime(2023, 1, 1),
                pdf_url="",
                url="https://example.com/test1",
                source="source1",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test2",
                title="Same Title",
                authors=["Author A"],
                abstract="Abstract 2",
                doi="10.1234/test",
                published_date=datetime(2023, 1, 2),
                pdf_url="",
                url="https://example.com/test2",
                source="source2",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
            Paper(
                paper_id="test3",
                title="Unique Paper",
                authors=["Author B"],
                abstract="Abstract 3",
                doi="10.5678/test",
                published_date=datetime(2023, 1, 3),
                pdf_url="",
                url="https://example.com/test3",
                source="source3",
                categories=[],
                keywords=[],
                citations=0,
                references=[]
            ),
        ]

        groups = find_duplicates(papers)

        # Should have 1 duplicate group
        self.assertEqual(len(groups), 1)

        # First group should have canonical paper + 1 duplicate
        canonical, duplicates = groups[0]
        self.assertEqual(canonical.paper_id, "test1")
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0].paper_id, "test2")


if __name__ == "__main__":
    unittest.main()
