import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from paper_search_mcp import cross_source
from paper_search_mcp.academic_platforms.semantic import SemanticRateLimitError
from paper_search_mcp.http_status import SEMANTIC_SCHOLAR_429_NOTE


def _write_pdf(tmpdir: str, name: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\n%fake\n")
    return path


class StubSearcher:
    """Configurable searcher: returns a preset path, error string, or raises."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def download_pdf(self, identifier, save_path):
        self.calls.append((identifier, save_path))
        if callable(self.outcome):
            return self.outcome()
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class DoiDownloadTests(unittest.TestCase):
    def test_scihub_tried_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "scihub.pdf")
            biorxiv = StubSearcher("should not be called")
            medrxiv = StubSearcher("should not be called")
            semantic = StubSearcher("should not be called")
            openalex = MagicMock()
            scihub = StubSearcher(pdf)

            result = cross_source.doi_download(
                "10.1101/2021.03.01.433208", tmp,
                biorxiv, medrxiv, semantic, openalex, scihub,
            )

            self.assertEqual(result["source"], "scihub")
            self.assertEqual(result["path"], pdf)
            self.assertEqual(len(scihub.calls), 1)
            self.assertEqual(len(biorxiv.calls), 0)
            self.assertEqual(len(medrxiv.calls), 0)

    def test_biorxiv_wins_when_scihub_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "biorxiv.pdf")
            biorxiv = StubSearcher(pdf)
            medrxiv = StubSearcher("should not be called")
            semantic = StubSearcher("should not be called")
            openalex = MagicMock()
            scihub = StubSearcher("Error: no mirror")

            result = cross_source.doi_download(
                "10.1101/2021.03.01.433208", tmp,
                biorxiv, medrxiv, semantic, openalex, scihub,
            )

            self.assertEqual(result["source"], "biorxiv")
            sources_tried = [a["source"] for a in result["attempts"]]
            self.assertEqual(sources_tried, ["scihub", "biorxiv"])

    def test_non_biorxiv_doi_skips_biorxiv_and_medrxiv(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "openalex.pdf")
            biorxiv = StubSearcher("should not be called")
            medrxiv = StubSearcher("should not be called")
            semantic = StubSearcher("should not be called")
            paper_stub = MagicMock()
            paper_stub.paper_id = "W1"
            openalex = MagicMock()
            openalex.get_paper_by_doi.return_value = paper_stub
            openalex.download_pdf.return_value = pdf
            scihub = StubSearcher("Error: no mirror")

            result = cross_source.doi_download(
                "10.1038/nature12373", tmp,
                biorxiv, medrxiv, semantic, openalex, scihub,
            )

            self.assertEqual(result["source"], "openalex")
            sources_tried = [a["source"] for a in result["attempts"]]
            self.assertEqual(sources_tried, ["scihub", "openalex"])
            self.assertEqual(len(biorxiv.calls), 0)
            self.assertEqual(len(medrxiv.calls), 0)
            self.assertEqual(len(semantic.calls), 0)

    def test_falls_through_to_semantic(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "semantic.pdf")
            biorxiv = StubSearcher("Error: 404")
            medrxiv = StubSearcher(RuntimeError("medrxiv broke"))
            semantic = StubSearcher(pdf)
            openalex = MagicMock()
            openalex.get_paper_by_doi.return_value = None
            scihub = StubSearcher("Error: no mirror")

            result = cross_source.doi_download(
                "10.1101/2021.01.01.000000", tmp,
                biorxiv, medrxiv, semantic, openalex, scihub,
            )

            self.assertEqual(result["source"], "semantic")
            sources_tried = [a["source"] for a in result["attempts"]]
            self.assertEqual(sources_tried, ["scihub", "biorxiv", "medrxiv", "openalex", "semantic"])
            self.assertIn("medrxiv broke", result["attempts"][2]["error"])

    def test_semantic_429_note_is_reported_in_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            biorxiv = StubSearcher("Error: 404")
            medrxiv = StubSearcher("Error: 404")
            semantic = StubSearcher(SemanticRateLimitError(SEMANTIC_SCHOLAR_429_NOTE))
            openalex = MagicMock()
            openalex.get_paper_by_doi.return_value = None
            scihub = StubSearcher("Error: no mirror")

            result = cross_source.doi_download(
                "10.1101/2021.01.01.000000", tmp,
                biorxiv, medrxiv, semantic, openalex, scihub,
            )

            self.assertIn(SEMANTIC_SCHOLAR_429_NOTE, result["attempts"][-1]["error"])

    def test_openalex_uses_doi_lookup_then_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "openalex.pdf")
            biorxiv = StubSearcher("skipped")
            medrxiv = StubSearcher("skipped")
            semantic = StubSearcher("should not be called")
            paper_stub = MagicMock()
            paper_stub.paper_id = "W12345"
            openalex = MagicMock()
            openalex.get_paper_by_doi.return_value = paper_stub
            openalex.download_pdf.return_value = pdf
            scihub = StubSearcher("Error: no mirror")

            result = cross_source.doi_download(
                "10.1038/nature12373", tmp,
                biorxiv, medrxiv, semantic, openalex, scihub,
            )

            self.assertEqual(result["source"], "openalex")
            openalex.get_paper_by_doi.assert_called_once_with("10.1038/nature12373")
            openalex.download_pdf.assert_called_once_with("W12345", tmp)

    def test_normalizes_doi_url_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "biorxiv.pdf")
            biorxiv = StubSearcher(pdf)
            scihub = StubSearcher("Error: no mirror")
            result = cross_source.doi_download(
                "https://doi.org/10.1101/abc", tmp,
                biorxiv, StubSearcher("x"), StubSearcher("x"),
                MagicMock(), scihub,
            )
            self.assertEqual(biorxiv.calls[0][0], "10.1101/abc")
            self.assertEqual(scihub.calls[0][0], "10.1101/abc")
            self.assertEqual(result["source"], "biorxiv")


class PmidDownloadTests(unittest.TestCase):
    def test_scihub_tried_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "scihub.pdf")
            semantic = StubSearcher("should not be called")
            pmc = StubSearcher("should not be called")
            scihub = StubSearcher(pdf)

            with patch.object(cross_source, "_resolve_pmcid", return_value="PMC2323736"):
                result = cross_source.pmid_download(
                    "19872477", tmp, semantic, pmc, scihub,
                )

            self.assertEqual(result["source"], "scihub")
            self.assertEqual(scihub.calls[0][0], "19872477")
            self.assertEqual(len(pmc.calls), 0)

    def test_pmc_wins_when_scihub_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "pmc.pdf")
            semantic = StubSearcher("should not be called")
            pmc = StubSearcher(pdf)
            scihub = StubSearcher("Error: no mirror")

            with patch.object(cross_source, "_resolve_pmcid", return_value="PMC2323736"):
                result = cross_source.pmid_download(
                    "19872477", tmp, semantic, pmc, scihub,
                )

            self.assertEqual(result["source"], "pmc")
            self.assertEqual(pmc.calls[0][0], "PMC2323736")

    def test_semantic_is_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "semantic.pdf")
            semantic = StubSearcher(pdf)
            pmc = StubSearcher("Error: 404")
            scihub = StubSearcher("Error: no mirror")

            with patch.object(cross_source, "_resolve_pmcid", return_value="PMC1"):
                result = cross_source.pmid_download(
                    "19872477", tmp, semantic, pmc, scihub,
                )

            self.assertEqual(result["source"], "semantic")
            sources_tried = [a["source"] for a in result["attempts"]]
            self.assertEqual(sources_tried, ["scihub", "pmc", "semantic"])
            self.assertEqual(semantic.calls[0][0], "PMID:19872477")

    def test_pmc_skipped_when_no_pmcid(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "scihub.pdf")
            semantic = StubSearcher("should not be called")
            pmc = StubSearcher("should not be called")
            scihub = StubSearcher(pdf)

            with patch.object(cross_source, "_resolve_pmcid", return_value=""):
                result = cross_source.pmid_download(
                    "19872477", tmp, semantic, pmc, scihub,
                )

            sources_tried = [a["source"] for a in result["attempts"]]
            self.assertEqual(sources_tried, ["scihub"])
            self.assertEqual(len(pmc.calls), 0)
            self.assertEqual(len(semantic.calls), 0)

    def test_rejects_non_numeric_pmid(self):
        with self.assertRaises(AssertionError):
            cross_source.pmid_download(
                "not-a-pmid", "/tmp",
                StubSearcher("x"), StubSearcher("x"), StubSearcher("x"),
            )

    def test_all_fail_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            semantic = StubSearcher("Error: paywall")
            pmc = StubSearcher("Error: 404")
            scihub = StubSearcher("Error: no mirror")

            with patch.object(cross_source, "_resolve_pmcid", return_value="PMC1"):
                result = cross_source.pmid_download(
                    "19872477", tmp, semantic, pmc, scihub,
                )

            self.assertIn("error", result)
            self.assertIn("19872477", result["error"])
            self.assertEqual(len(result["attempts"]), 3)
            self.assertTrue(all(a["error"] is not None for a in result["attempts"]))


class ReadTests(unittest.TestCase):
    def test_read_propagates_download_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            biorxiv = StubSearcher("Error: 404")
            medrxiv = StubSearcher("Error: 404")
            semantic = StubSearcher("Error: paywall")
            openalex = MagicMock()
            openalex.get_paper_by_doi.return_value = None

            result = cross_source.doi_read(
                "10.1038/nope", tmp,
                biorxiv, medrxiv, semantic, openalex, StubSearcher("x"),
            )

            self.assertIn("error", result)
            self.assertNotIn("text", result)

    def test_read_extracts_text_from_winning_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _write_pdf(tmp, "biorxiv.pdf")
            biorxiv = StubSearcher(pdf)
            scihub = StubSearcher("Error: no mirror")

            with patch.object(cross_source, "_extract_text", return_value="hello world"):
                result = cross_source.doi_read(
                    "10.1101/abc", tmp,
                    biorxiv, StubSearcher("x"), StubSearcher("x"),
                    MagicMock(), scihub,
                )

            self.assertEqual(result["text"], "hello world")
            self.assertEqual(result["source"], "biorxiv")
            self.assertEqual(result["path"], pdf)


if __name__ == "__main__":
    unittest.main()
