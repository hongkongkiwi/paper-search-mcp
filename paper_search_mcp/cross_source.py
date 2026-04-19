"""Cross-source DOI and PMID fan-out.

Given a single identifier, try every source that can serve it, in priority
order, until one returns a PDF (or extracted text). Report which source won
and what the others returned.
"""
import os
import logging
import xml.etree.ElementTree as ET
from typing import Callable, Dict, List, Tuple

import requests
from PyPDF2 import PdfReader

from .deduplication import normalize_doi

logger = logging.getLogger(__name__)

NCBI_ELINK = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

Source = Tuple[str, Callable[[], str]]


def _attempt(name: str, fn: Callable[[], str]) -> Dict:
    try:
        result = fn()
    except Exception as e:
        return {"ok": False, "source": name, "error": f"{type(e).__name__}: {e}"}
    if isinstance(result, str) and os.path.isfile(result):
        return {"ok": True, "source": name, "path": result}
    return {"ok": False, "source": name, "error": str(result)}


def _try_download(sources: List[Source]) -> Dict:
    attempts = []
    for name, fn in sources:
        r = _attempt(name, fn)
        if r["ok"]:
            attempts.append({"source": name, "error": None})
            return {"path": r["path"], "source": name, "attempts": attempts}
        attempts.append({"source": name, "error": r["error"]})
    return {"attempts": attempts}


def _resolve_pmcid(pmid: str) -> str:
    """Map a PMID to a PMCID via NCBI elink, or empty string if none linked."""
    try:
        response = requests.get(
            NCBI_ELINK,
            params={"dbfrom": "pubmed", "db": "pmc", "id": pmid},
            timeout=15,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as e:
        logger.warning(f"PMID→PMCID lookup failed for {pmid}: {e}")
        return ""
    link = root.find(".//LinkSetDb/Link/Id")
    if link is None or not link.text:
        return ""
    return f"PMC{link.text}"


def _openalex_download_by_doi(openalex, doi: str, save_path: str) -> str:
    paper = openalex.get_paper_by_doi(doi)
    if not paper:
        return f"OpenAlex: no work found for DOI {doi}"
    return openalex.download_pdf(paper.paper_id, save_path)


def doi_download(
    doi: str,
    save_path: str,
    biorxiv,
    medrxiv,
    semantic,
    openalex,
    scihub,
    allow_scihub: bool,
) -> Dict:
    """Download a PDF for a DOI from the first source that serves it."""
    doi = normalize_doi(doi)
    assert doi, "doi must not be empty"

    sources: List[Source] = []
    if allow_scihub:
        sources.append(("scihub", lambda: scihub.download_pdf(doi, save_path)))
    if doi.startswith("10.1101/"):
        sources.append(("biorxiv", lambda: biorxiv.download_pdf(doi, save_path)))
        sources.append(("medrxiv", lambda: medrxiv.download_pdf(doi, save_path)))
    sources.append(("openalex", lambda: _openalex_download_by_doi(openalex, doi, save_path)))
    sources.append(("semantic", lambda: semantic.download_pdf(f"DOI:{doi}", save_path)))

    result = _try_download(sources)
    if "path" in result:
        return result
    return {"error": f"No source returned a PDF for DOI {doi}", **result}


def pmid_download(
    pmid: str,
    save_path: str,
    semantic,
    pmc,
    scihub,
    allow_scihub: bool,
) -> Dict:
    """Download a PDF for a PMID from the first source that serves it."""
    pmid = pmid.strip()
    assert pmid.isdigit(), f"pmid must be numeric: {pmid!r}"

    sources: List[Source] = []
    if allow_scihub:
        sources.append(("scihub", lambda: scihub.download_pdf(pmid, save_path)))
    pmcid = _resolve_pmcid(pmid)
    if pmcid:
        sources.append(("pmc", lambda: pmc.download_pdf(pmcid, save_path)))
    sources.append(("semantic", lambda: semantic.download_pdf(f"PMID:{pmid}", save_path)))

    result = _try_download(sources)
    if "path" in result:
        return result
    return {"error": f"No source returned a PDF for PMID {pmid}", **result}


def _extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def _read_from_download(download_result: Dict) -> Dict:
    if "error" in download_result:
        return download_result
    text = _extract_text(download_result["path"])
    return {
        "text": text,
        "path": download_result["path"],
        "source": download_result["source"],
        "attempts": download_result["attempts"],
    }


def doi_read(
    doi: str,
    save_path: str,
    biorxiv,
    medrxiv,
    semantic,
    openalex,
    scihub,
    allow_scihub: bool,
) -> Dict:
    """Download a DOI PDF from the first source that serves it, then extract text."""
    return _read_from_download(
        doi_download(doi, save_path, biorxiv, medrxiv, semantic, openalex, scihub, allow_scihub)
    )


def pmid_read(
    pmid: str,
    save_path: str,
    semantic,
    pmc,
    scihub,
    allow_scihub: bool,
) -> Dict:
    """Download a PMID PDF from the first source that serves it, then extract text."""
    return _read_from_download(
        pmid_download(pmid, save_path, semantic, pmc, scihub, allow_scihub)
    )
