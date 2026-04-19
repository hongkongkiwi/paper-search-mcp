# paper_search_mcp/server.py
from typing import List, Dict, Optional
import os
import logging
import httpx
from urllib.parse import urlparse, unquote
from urllib.request import url2pathname

logger = logging.getLogger(__name__)
import mcp.types as types
from fastmcp.server import _convert_to_content
from mcp.server.fastmcp import FastMCP, Context
from .academic_platforms.arxiv import ArxivSearcher
from .academic_platforms.pubmed import PubMedSearcher
from .academic_platforms.biorxiv import BioRxivSearcher
from .academic_platforms.medrxiv import MedRxivSearcher
from .academic_platforms.google_scholar import GoogleScholarSearcher
from .academic_platforms.iacr import IACRSearcher
from .academic_platforms.semantic import SemanticSearcher, SemanticRateLimitError
from .academic_platforms.crossref import CrossRefSearcher
from .academic_platforms.openalex import OpenAlexSearcher
from .academic_platforms.pmc import PMCSearcher
from .academic_platforms.sci_hub import SciHubFetcher
from .academic_platforms.hal import HALSearcher
from .academic_platforms.ssrn import SSRNSearcher
from .academic_platforms.dblp import DBLPSearcher
from .deduplication import deduplicate_paper_dicts, merge_duplicate_papers, dict_to_paper, find_duplicates

from .paper import Paper


class PaperSearchMCP(FastMCP):
    async def call_tool(self, name: str, arguments: dict):
        context = self.get_context()
        result = await self._tool_manager.call_tool(name, arguments, context=context)
        if isinstance(result, list) and not result:
            return [types.TextContent(type="text", text="[]")]
        return _convert_to_content(result)


# Initialize MCP server
mcp = PaperSearchMCP("paper_search_server")

# Instances of searchers
arxiv_searcher = ArxivSearcher()
pubmed_searcher = PubMedSearcher()
biorxiv_searcher = BioRxivSearcher()
medrxiv_searcher = MedRxivSearcher()
google_scholar_searcher = GoogleScholarSearcher()
iacr_searcher = IACRSearcher()
semantic_searcher = SemanticSearcher()
crossref_searcher = CrossRefSearcher()
openalex_searcher = OpenAlexSearcher()
pmc_searcher = PMCSearcher()
scihub_fetcher = SciHubFetcher()
hal_searcher = HALSearcher()
ssrn_searcher = SSRNSearcher()
dblp_searcher = DBLPSearcher()


def _apply_filename(result: str, filename: Optional[str]) -> str:
    """Rename a downloaded file if a custom filename was provided.

    Args:
        result: The return value from a download method (file path or error string).
        filename: Optional custom filename. '.pdf' extension is added if missing.

    Returns:
        The new file path, or the original result if no rename was needed.
    """
    if not filename or not os.path.isfile(result):
        return result
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    new_path = os.path.join(os.path.dirname(result), filename)
    os.rename(result, new_path)
    return new_path


def _file_uri_to_path(uri: str) -> str:
    parsed = urlparse(uri)
    assert parsed.scheme == "file"

    path = url2pathname(unquote(parsed.path))
    if parsed.netloc and parsed.netloc != "localhost":
        return f"//{parsed.netloc}{path}"

    return path


async def _resolve_save_path(save_path: str, ctx: Context = None) -> str:
    if os.path.isabs(save_path) or ctx is None:
        return save_path

    supports_roots = ctx.session.check_client_capability(
        types.ClientCapabilities(roots=types.RootsCapability())
    )
    if not supports_roots:
        return save_path

    roots_result = await ctx.session.list_roots()
    assert roots_result.roots, "Client advertised roots support but returned no roots"

    root_path = _file_uri_to_path(str(roots_result.roots[0].uri))
    return os.path.normpath(os.path.join(root_path, save_path))


# Synchronous helper to adapt synchronous searchers
def sync_search(searcher, query: str, max_results: int, **kwargs) -> List[Dict]:
    """Synchronous search wrapper for searchers."""
    if 'year' in kwargs:
        papers = searcher.search(query, year=kwargs['year'], max_results=max_results)
    else:
        papers = searcher.search(query, max_results=max_results)
    return [paper.to_dict() for paper in papers]


# Tool definitions
@mcp.tool()
async def search_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from arXiv.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        papers = sync_search(arxiv_searcher, query, max_results)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_arxiv failed: {e}")
        return [{"error": f"arXiv search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_pubmed(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from PubMed.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        papers = sync_search(pubmed_searcher, query, max_results)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_pubmed failed: {e}")
        return [{"error": f"PubMed search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_biorxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from bioRxiv.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        papers = sync_search(biorxiv_searcher, query, max_results)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_biorxiv failed: {e}")
        return [{"error": f"bioRxiv search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_medrxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from medRxiv.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        papers = sync_search(medrxiv_searcher, query, max_results)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_medrxiv failed: {e}")
        return [{"error": f"medRxiv search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_google_scholar(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from Google Scholar.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        papers = sync_search(google_scholar_searcher, query, max_results)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_google_scholar failed: {e}")
        return [{"error": f"Google Scholar search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_iacr(
    query: str, max_results: int = 10, fetch_details: bool = True
) -> List[Dict]:
    """Search academic papers from IACR ePrint Archive.

    Args:
        query: Search query string (e.g., 'cryptography', 'secret sharing').
        max_results: Maximum number of papers to return (default: 10).
        fetch_details: Whether to fetch detailed information for each paper (default: True).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        papers = iacr_searcher.search(query, max_results, fetch_details)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"search_iacr failed: {e}")
        return [{"error": f"IACR search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def download_arxiv(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of an arXiv paper.

    Args:
        paper_id: arXiv paper ID (e.g., '2106.12345').
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        Path to the downloaded PDF file.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = arxiv_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_arxiv failed: {e}")
        return f"Download failed for arXiv paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def download_pubmed(paper_id: str, save_path: str = "./downloads", filename: Optional[str] = None) -> str:
    """Attempt to download PDF of a PubMed paper.

    Args:
        paper_id: PubMed ID (PMID).
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        str: Message indicating that direct PDF download is not supported.
    """
    try:
        result = pubmed_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except NotImplementedError as e:
        return str(e)
    except Exception as e:
        logger.error(f"download_pubmed failed: {e}")
        return f"Download failed for PubMed paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def download_biorxiv(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of a bioRxiv paper.

    Args:
        paper_id: bioRxiv DOI.
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        Path to the downloaded PDF file.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = biorxiv_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_biorxiv failed: {e}")
        return f"Download failed for bioRxiv paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def download_medrxiv(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of a medRxiv paper.

    Args:
        paper_id: medRxiv DOI.
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        Path to the downloaded PDF file.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = medrxiv_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_medrxiv failed: {e}")
        return f"Download failed for medRxiv paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def download_iacr(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of an IACR ePrint paper.

    Args:
        paper_id: IACR paper ID (e.g., '2009/101').
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        Path to the downloaded PDF file.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = iacr_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_iacr failed: {e}")
        return f"Download failed for IACR paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_arxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an arXiv paper PDF.

    Args:
        paper_id: arXiv paper ID (e.g., '2106.12345').
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return arxiv_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_arxiv_paper failed: {e}")
        return f"Failed to read arXiv paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_pubmed_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a PubMed paper.

    Args:
        paper_id: PubMed ID (PMID).
        save_path: Directory where the PDF would be saved (unused).
    Returns:
        str: Message indicating that direct paper reading is not supported.
    """
    try:
        return pubmed_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_pubmed_paper failed: {e}")
        return f"Failed to read PubMed paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_biorxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a bioRxiv paper PDF.

    Args:
        paper_id: bioRxiv DOI.
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return biorxiv_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_biorxiv_paper failed: {e}")
        return f"Failed to read bioRxiv paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_medrxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a medRxiv paper PDF.

    Args:
        paper_id: medRxiv DOI.
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return medrxiv_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_medrxiv_paper failed: {e}")
        return f"Failed to read medRxiv paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_iacr_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an IACR ePrint paper PDF.

    Args:
        paper_id: IACR paper ID (e.g., '2009/101').
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return iacr_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_iacr_paper failed: {e}")
        return f"Failed to read IACR paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def search_semantic(query: str, year: Optional[str] = None, max_results: int = 10) -> List[Dict]:
    """Search academic papers from Semantic Scholar.

    Args:
        query: Search query string (e.g., 'machine learning').
        year: Optional year filter (e.g., '2019', '2016-2020', '2010-', '-2015').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    try:
        kwargs = {}
        if year is not None:
            kwargs['year'] = year
        papers = sync_search(semantic_searcher, query, max_results, **kwargs)
        return papers if papers else []
    except SemanticRateLimitError as e:
        logger.error(f"search_semantic rate limited: {e}")
        return [{"error": str(e), "status_code": 429}]
    except Exception as e:
        logger.error(f"search_semantic failed: {e}")
        return [{"error": f"Semantic Scholar search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def download_semantic(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of a Semantic Scholar paper.

    Args:
        paper_id: Semantic Scholar paper ID, Paper identifier in one of the following formats:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI:<doi> (e.g., "DOI:10.18653/v1/N18-3011")
            - ARXIV:<id> (e.g., "ARXIV:2106.15928")
            - MAG:<id> (e.g., "MAG:112218234")
            - ACL:<id> (e.g., "ACL:W12-3903")
            - PMID:<id> (e.g., "PMID:19872477")
            - PMCID:<id> (e.g., "PMCID:2323736")
            - URL:<url> (e.g., "URL:https://arxiv.org/abs/2106.15928v1")
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        Path to the downloaded PDF file.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = semantic_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_semantic failed: {e}")
        return f"Download failed for Semantic Scholar paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_semantic_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a Semantic Scholar paper.

    Args:
        paper_id: Semantic Scholar paper ID, Paper identifier in one of the following formats:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI:<doi> (e.g., "DOI:10.18653/v1/N18-3011")
            - ARXIV:<id> (e.g., "ARXIV:2106.15928")
            - MAG:<id> (e.g., "MAG:112218234")
            - ACL:<id> (e.g., "ACL:W12-3903")
            - PMID:<id> (e.g., "PMID:19872477")
            - PMCID:<id> (e.g., "PMCID:2323736")
            - URL:<url> (e.g., "URL:https://arxiv.org/abs/2106.15928v1")
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return semantic_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_semantic_paper failed: {e}")
        return f"Failed to read Semantic Scholar paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def get_semantic_citations(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers that cite this Semantic Scholar paper (forward citations).

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
        max_results: Maximum number of citing papers to return (default: 20)

    Returns:
        List of papers that cite the given paper.

    Example:
        await get_semantic_citations("5bbfdf2e62f0508c65ba6de9c72fe2066fd98138", 10)
    """
    try:
        papers = semantic_searcher.get_citations(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"get_semantic_citations failed: {e}")
        return [{"error": f"Semantic Scholar citations lookup failed for {paper_id}: {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_semantic_references(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers referenced by this Semantic Scholar paper (backward citations).

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
        max_results: Maximum number of referenced papers to return (default: 20)

    Returns:
        List of papers referenced by the given paper.

    Example:
        await get_semantic_references("5bbfdf2e62f0508c65ba6de9c72fe2066fd98138", 10)
    """
    try:
        papers = semantic_searcher.get_references(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"get_semantic_references failed: {e}")
        return [{"error": f"Semantic Scholar references lookup failed for {paper_id}: {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_semantic_related(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers related to this Semantic Scholar paper based on citations and concepts.

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
        max_results: Maximum number of related papers to return (default: 20)

    Returns:
        List of related papers.

    Example:
        await get_semantic_related("5bbfdf2e62f0508c65ba6de9c72fe2066fd98138", 10)
    """
    try:
        papers = semantic_searcher.get_related_papers(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"get_semantic_related failed: {e}")
        return [{"error": f"Semantic Scholar related papers lookup failed for {paper_id}: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_semantic_by_author(
    author_name: str,
    max_results: int = 20
) -> List[Dict]:
    """Search for papers by a specific author in Semantic Scholar.

    Args:
        author_name: Name of the author (e.g., 'Geoffrey Hinton')
        max_results: Maximum number of papers to return (default: 20)

    Returns:
        List of papers by the author.

    Example:
        await search_semantic_by_author("Yann LeCun", 15)
    """
    try:
        papers = semantic_searcher.search_by_author(author_name, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"search_semantic_by_author failed: {e}")
        return [{"error": f"Semantic Scholar author search failed for '{author_name}': {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_crossref(query: str, max_results: int = 10, **kwargs) -> List[Dict]:
    """Search academic papers from CrossRef database.
    
    CrossRef is a scholarly infrastructure organization that provides 
    persistent identifiers (DOIs) for scholarly content and metadata.
    It's one of the largest citation databases covering millions of 
    academic papers, journals, books, and other scholarly content.

    Args:
        query: Search query string (e.g., 'machine learning', 'climate change').
        max_results: Maximum number of papers to return (default: 10, max: 1000).
        **kwargs: Additional search parameters:
            - filter: CrossRef filter string (e.g., 'has-full-text:true,from-pub-date:2020')
            - sort: Sort field ('relevance', 'published', 'updated', 'deposited', etc.)
            - order: Sort order ('asc' or 'desc')
    Returns:
        List of paper metadata in dictionary format.
        
    Examples:
        # Basic search
        search_crossref("deep learning", 20)
        
        # Search with filters
        search_crossref("climate change", 10, filter="from-pub-date:2020,has-full-text:true")
        
        # Search sorted by publication date
        search_crossref("neural networks", 15, sort="published", order="desc")
    """
    try:
        papers = sync_search(crossref_searcher, query, max_results, **kwargs)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_crossref failed: {e}")
        return [{"error": f"CrossRef search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_crossref_paper_by_doi(doi: str) -> Dict:
    """Get a specific paper from CrossRef by its DOI.

    Args:
        doi: Digital Object Identifier (e.g., '10.1038/nature12373').
    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        get_crossref_paper_by_doi("10.1038/nature12373")
    """
    try:
        paper = crossref_searcher.get_paper_by_doi(doi)
        return paper.to_dict() if paper else {"error": f"Paper with DOI {doi} not found in CrossRef"}
    except Exception as e:
        logger.error(f"get_crossref_paper_by_doi failed: {e}")
        return {"error": f"CrossRef DOI lookup failed for {doi}: {type(e).__name__}: {e}"}


@mcp.tool()
async def download_crossref(paper_id: str, save_path: str = "./downloads", filename: Optional[str] = None) -> str:
    """Attempt to download PDF of a CrossRef paper.

    Args:
        paper_id: CrossRef DOI (e.g., '10.1038/nature12373').
        save_path: Directory to save the PDF (default: './downloads').
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').
    Returns:
        str: Message indicating that direct PDF download is not supported.

    Note:
        CrossRef is a citation database and doesn't provide direct PDF downloads.
        Use the DOI to access the paper through the publisher's website.
    """
    try:
        result = crossref_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except NotImplementedError as e:
        return str(e)
    except Exception as e:
        logger.error(f"download_crossref failed: {e}")
        return f"Download failed for CrossRef paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_crossref_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Attempt to read and extract text content from a CrossRef paper.

    Args:
        paper_id: CrossRef DOI (e.g., '10.1038/nature12373').
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: Message indicating that direct paper reading is not supported.

    Note:
        CrossRef is a citation database and doesn't provide direct paper content.
        Use the DOI to access the paper through the publisher's website.
    """
    try:
        return crossref_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_crossref_paper failed: {e}")
        return f"Failed to read CrossRef paper {paper_id}: {type(e).__name__}: {e}"


# ============================================================================
# OpenAlex Tools
# ============================================================================

@mcp.tool()
async def search_openalex(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    **kwargs
) -> List[Dict]:
    """Search academic papers from OpenAlex.

    OpenAlex is a free and open catalog of the global research system with
    over 200M works, comprehensive citation data, and author information.

    Args:
        query: Search query string (e.g., 'machine learning transformers').
        max_results: Maximum number of papers to return (default: 10, max: 200).
        year: Optional year filter (e.g., '2020', '2018-2022').
        **kwargs: Additional search parameters:
            - filter: OpenAlex filter (e.g., 'has_fulltext:true,type:journal-article')
            - sort: Sort field (e.g., 'cited_by_count:desc', 'publication_date:desc')
            - fields: Comma-separated list of fields to return

    Returns:
        List of paper metadata in dictionary format.

    Examples:
        # Basic search
        await search_openalex("deep learning", 20)

        # Search with year filter
        await search_openalex("quantum computing", 15, year="2020-2023")

        # Search with filters
        await search_openalex("climate change", 10, filter="has_fulltext:true")
    """
    try:
        search_kwargs = {}
        if year:
            search_kwargs['year'] = year
        if 'filter' in kwargs:
            search_kwargs['filter'] = kwargs['filter']
        if 'sort' in kwargs:
            search_kwargs['sort'] = kwargs['sort']

        papers = sync_search(openalex_searcher, query, max_results, **search_kwargs)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_openalex failed: {e}")
        return [{"error": f"OpenAlex search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_openalex_paper(paper_id: str) -> Dict:
    """Get a specific paper from OpenAlex by its ID.

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890' or 'https://openalex.org/W3124567890')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_openalex_paper("W3108360596")
    """
    try:
        paper = openalex_searcher.get_paper_by_id(paper_id)
        return paper.to_dict() if paper else {"error": f"OpenAlex paper {paper_id} not found"}
    except Exception as e:
        logger.error(f"get_openalex_paper failed: {e}")
        return {"error": f"OpenAlex paper lookup failed for {paper_id}: {type(e).__name__}: {e}"}


@mcp.tool()
async def get_openalex_paper_by_doi(doi: str) -> Dict:
    """Get a specific paper from OpenAlex by its DOI.

    Args:
        doi: Digital Object Identifier (e.g., '10.1038/nature12373')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_openalex_paper_by_doi("10.1038/nature12373")
    """
    try:
        paper = openalex_searcher.get_paper_by_doi(doi)
        return paper.to_dict() if paper else {"error": f"Paper with DOI {doi} not found in OpenAlex"}
    except Exception as e:
        logger.error(f"get_openalex_paper_by_doi failed: {e}")
        return {"error": f"OpenAlex DOI lookup failed for {doi}: {type(e).__name__}: {e}"}


@mcp.tool()
async def get_openalex_citations(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers that cite this OpenAlex work (forward citations).

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890')
        max_results: Maximum number of citing papers to return (default: 20)

    Returns:
        List of papers that cite the given paper.

    Example:
        await get_openalex_citations("W3108360596", 10)
    """
    try:
        papers = openalex_searcher.get_citations(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"get_openalex_citations failed: {e}")
        return [{"error": f"OpenAlex citations lookup failed for {paper_id}: {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_openalex_references(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers referenced by this OpenAlex work (backward citations).

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890')
        max_results: Maximum number of referenced papers to return (default: 20)

    Returns:
        List of papers referenced by the given paper.

    Example:
        await get_openalex_references("W3108360596", 10)
    """
    try:
        papers = openalex_searcher.get_references(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"get_openalex_references failed: {e}")
        return [{"error": f"OpenAlex references lookup failed for {paper_id}: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_openalex_by_author(
    author_name: str,
    max_results: int = 20,
    **kwargs
) -> List[Dict]:
    """Search for papers by a specific author in OpenAlex.

    Args:
        author_name: Name of the author (e.g., 'Geoffrey Hinton')
        max_results: Maximum number of papers to return (default: 20)
        **kwargs: Additional search parameters (year, filter, sort)

    Returns:
        List of papers by the author.

    Example:
        await search_openalex_by_author("Yann LeCun", 15)
    """
    try:
        papers = openalex_searcher.search_by_author(author_name, max_results, **kwargs)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"search_openalex_by_author failed: {e}")
        return [{"error": f"OpenAlex author search failed for '{author_name}': {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_openalex_related(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers related to this OpenAlex work based on concepts and references.

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890')
        max_results: Maximum number of related papers to return (default: 20)

    Returns:
        List of related papers.

    Example:
        await get_openalex_related("W3108360596", 10)
    """
    try:
        papers = openalex_searcher.get_related_papers(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"get_openalex_related failed: {e}")
        return [{"error": f"OpenAlex related papers lookup failed for {paper_id}: {type(e).__name__}: {e}"}]


@mcp.tool()
async def download_openalex(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of an OpenAlex paper.

    Args:
        paper_id: OpenAlex paper ID (e.g., 'W3124567890')
        save_path: Directory to save the PDF (default: './downloads')
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').

    Returns:
        Path to downloaded PDF or error message.

    Note:
        OpenAlex doesn't directly host PDFs. This attempts to find and download
        from available open access sources.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = openalex_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_openalex failed: {e}")
        return f"Download failed for OpenAlex paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_openalex_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an OpenAlex paper PDF.

    Args:
        paper_id: OpenAlex paper ID (e.g., 'W3124567890')
        save_path: Directory where the PDF is/will be saved (default: './downloads')

    Returns:
        The extracted text content of the paper.
    """
    try:
        return openalex_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_openalex_paper failed: {e}")
        return f"Failed to read OpenAlex paper {paper_id}: {type(e).__name__}: {e}"


# ============================================================================
# Sci-Hub Tools
# ============================================================================

@mcp.tool()
async def download_scihub(
    identifier: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF from Sci-Hub using DOI, PMID, or URL.

    Sci-Hub provides access to millions of research papers behind paywalls.
    Use this tool when you cannot find a free PDF from other sources.

    Args:
        identifier: DOI (e.g., '10.1038/nature12373'), PMID, or paper URL
        save_path: Directory to save the PDF (default: './downloads')
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').

    Returns:
        Path to downloaded PDF or error message.

    Examples:
        # Download by DOI
        await download_scihub("10.1038/nature12373")

        # Download by PMID
        await download_scihub("19872477")

        # Download by URL
        await download_scihub("https://arxiv.org/abs/2106.15928")

    Note:
        Sci-Hub operates in a legal gray area. Only use for legitimate research
        purposes and ensure compliance with your local laws and institution policies.
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = scihub_fetcher.download_pdf(identifier, save_path)
        if not result or result.startswith("Error"):
            return result or f"Failed to download PDF from Sci-Hub for identifier: {identifier}"
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_scihub failed: {e}")
        return f"Sci-Hub download failed for {identifier}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_scihub_paper(identifier: str, save_path: str = "./downloads") -> str:
    """Download and extract text from a paper via Sci-Hub.

    Args:
        identifier: DOI, PMID, article URL, or direct PDF URL.
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        Extracted paper text, or an error message if unavailable.
    """
    try:
        return scihub_fetcher.read_paper(identifier, save_path)
    except Exception as e:
        logger.error(f"read_scihub_paper failed: {e}")
        return f"Failed to read paper from Sci-Hub for {identifier}: {type(e).__name__}: {e}"


# ============================================================================
# Deduplication Tools
# ============================================================================

@mcp.tool()
async def deduplicate_papers(
    papers: List[Dict],
    keep: str = "first"
) -> List[Dict]:
    """Remove duplicate papers from a list of paper dictionaries.

    Same papers often appear in multiple sources (arXiv, Semantic Scholar, etc.).
    This tool identifies duplicates based on:
    - DOI matching (most reliable)
    - Title similarity (>= 90% match)
    - Author + year matching

    Args:
        papers: List of paper dictionaries (e.g., from search results)
        keep: Which duplicate to keep ('first', 'last', or 'best')
            - 'first': Keep the first occurrence (default)
            - 'last': Keep the last occurrence
            - 'best': Keep the one with most complete metadata

    Returns:
        Deduplicated list of paper dictionaries.

    Example:
        # Combine and deduplicate results from multiple sources
        arxiv_results = await search_arxiv("machine learning", 10)
        semantic_results = await search_semantic("machine learning", 10)
        all_papers = arxiv_results + semantic_results
        unique_papers = await deduplicate_papers(all_papers, keep="best")
    """
    try:
        return deduplicate_paper_dicts(papers, keep)
    except Exception as e:
        logger.error(f"deduplicate_papers failed: {e}")
        return [{"error": f"Deduplication failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def merge_papers(papers: List[Dict]) -> List[Dict]:
    """Merge duplicate papers by combining their metadata.

    When duplicates are found, this creates a merged paper with the best
    metadata from all duplicates. Useful when different sources have
    complementary information.

    Args:
        papers: List of paper dictionaries to deduplicate and merge

    Returns:
        List with duplicates merged, each having combined metadata.

    Example:
        # Merge results from multiple sources
        arxiv_results = await search_arxiv("quantum computing", 10)
        openalex_results = await search_openalex("quantum computing", 10)
        all_papers = arxiv_results + openalex_results
        merged_papers = await merge_papers(all_papers)
    """
    try:
        # Convert dicts to Paper objects
        paper_objs = []
        for d in papers:
            try:
                paper_objs.append(dict_to_paper(d))
            except Exception as e:
                logger.warning(f"Skipping malformed paper dict during merge: {e}")
                continue

        # Merge and convert back
        merged = merge_duplicate_papers(paper_objs)
        return [p.to_dict() for p in merged]
    except Exception as e:
        logger.error(f"merge_papers failed: {e}")
        return [{"error": f"Paper merge failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def find_duplicate_groups(papers: List[Dict]) -> Dict[str, List[Dict]]:
    """Find and report groups of duplicate papers without removing them.

    Useful for analyzing what duplicates exist before deciding how to handle them.

    Args:
        papers: List of paper dictionaries to analyze

    Returns:
        Dictionary with duplicate information:
        {
            "count": number of duplicate groups found,
            "groups": list of duplicate groups,
            "total_duplicates": total number of duplicate papers
        }

    Example:
        # Check for duplicates in search results
        results = await search_semantic("neural networks", 20)
        dup_info = await find_duplicate_groups(results)
        print(f"Found {dup_info['count']} duplicate groups")
    """
    # Convert dicts to Paper objects
    paper_objs = []
    for d in papers:
        try:
            paper_objs.append(dict_to_paper(d))
        except Exception as e:
            logger.warning(f"Skipping malformed paper dict during duplicate detection: {e}")
            continue

    # Find duplicates
    groups = find_duplicates(paper_objs)

    # Convert to report format
    group_dicts = []
    for canonical, dups in groups:
        group_dict = {
            "canonical": canonical.to_dict(),
            "duplicates": [d.to_dict() for d in dups],
            "sources": [d.source for d in [canonical] + dups]
        }
        group_dicts.append(group_dict)

    total_dupes = sum(len(g[1]) for g in groups)

    return {
        "count": len(groups),
        "groups": group_dicts,
        "total_duplicates": total_dupes
    }


# ============================================================================
# PubMed Central (PMC) Tools
# ============================================================================

@mcp.tool()
async def search_pmc(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None
) -> List[Dict]:
    """Search academic papers from PubMed Central (PMC).

    PMC is a free full-text archive of biomedical and life sciences journal
    literature. Unlike PubMed (which only has abstracts), PMC has complete articles.

    Args:
        query: Search query string (e.g., 'cancer immunotherapy', 'CRISPR')
        max_results: Maximum number of papers to return (default: 10)
        year: Optional year filter (e.g., '2020' or '2018-2022')

    Returns:
        List of paper metadata in dictionary format.

    Examples:
        # Basic search
        await search_pmc("machine learning", 20)

        # Search with year filter
        await search_pmc("immunotherapy", 15, year="2020-2023")
    """
    try:
        papers = sync_search(pmc_searcher, query, max_results, year=year)
        return papers if papers else []
    except Exception as e:
        logger.error(f"search_pmc failed: {e}")
        return [{"error": f"PMC search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_pmc_paper(paper_id: str) -> Dict:
    """Get a specific paper from PubMed Central by its PMCID.

    Args:
        paper_id: PMC ID (e.g., 'PMC1234567' or just '1234567')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_pmc_paper("PMC1234567")
    """
    try:
        paper = pmc_searcher.get_paper_by_pmcid(paper_id)
        return paper.to_dict() if paper else {"error": f"PMC paper {paper_id} not found"}
    except Exception as e:
        logger.error(f"get_pmc_paper failed: {e}")
        return {"error": f"PMC paper lookup failed for {paper_id}: {type(e).__name__}: {e}"}


@mcp.tool()
async def download_pmc(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of a PubMed Central paper.

    Args:
        paper_id: PMC ID (e.g., 'PMC1234567' or '1234567')
        save_path: Directory to save the PDF (default: './downloads')
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').

    Returns:
        Path to downloaded PDF or error message.

    Example:
        await download_pmc("PMC1234567")
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = pmc_searcher.download_pdf(paper_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_pmc failed: {e}")
        return f"Download failed for PMC paper {paper_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_pmc_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a PubMed Central paper PDF.

    Args:
        paper_id: PMC ID (e.g., 'PMC1234567' or '1234567')
        save_path: Directory where the PDF is/will be saved (default: './downloads')

    Returns:
        The extracted text content of the paper.

    Example:
        content = await read_pmc_paper("PMC1234567")
    """
    try:
        return pmc_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        logger.error(f"read_pmc_paper failed: {e}")
        return f"Failed to read PMC paper {paper_id}: {type(e).__name__}: {e}"


# ============================================================================
# HAL Tools
# ============================================================================

@mcp.tool()
async def search_hal(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    doc_type: Optional[str] = None,
    collection: Optional[str] = None,
    language: Optional[str] = None
) -> List[Dict]:
    """Search academic documents from HAL (French open archive).

    HAL provides access to scientific documents from French institutions including
    theses, preprints, conference papers, journal articles, and reports.

    Args:
        query: Search query string (e.g., 'machine learning', 'intelligence artificielle')
        max_results: Maximum number of papers to return (default: 10)
        year: Optional year filter (e.g., '2020', '2018-2022')
        doc_type: Document type filter ('thesis', 'preprint', 'article', 'communication', 'report', 'book')
        collection: Collection filter (e.g., 'CNRS', 'INRIA', 'UNIV-PARIS')
        language: Language filter (e.g., 'en', 'fr', 'de')

    Returns:
        List of paper metadata in dictionary format.

    Examples:
        # Basic search
        await search_hal("deep learning", 20)

        # Search for theses
        await search_hal("neural networks", 10, doc_type="thesis")

        # Search in French
        await search_hal("apprentissage automatique", 10, language="fr")
    """
    try:
        search_kwargs = {"year": year} if year else {}
        if doc_type:
            search_kwargs["doc_type"] = doc_type
        if collection:
            search_kwargs["collection"] = collection
        if language:
            search_kwargs["language"] = language

        papers = hal_searcher.search(query, max_results, **search_kwargs)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"search_hal failed: {e}")
        return [{"error": f"HAL search failed: {type(e).__name__}: {e}"}]


@mcp.tool()
async def search_hal_by_author(
    author_name: str,
    max_results: int = 10,
    year: Optional[str] = None
) -> List[Dict]:
    """Search for documents by author name in HAL.

    Args:
        author_name: Name of the author (e.g., 'Yann LeCun')
        max_results: Maximum number of papers to return (default: 10)
        year: Optional year filter (e.g., '2020', '2018-2022')

    Returns:
        List of papers by the author.

    Example:
        await search_hal_by_author("Jean-Pierre Nadal", 15)
    """
    try:
        papers = hal_searcher.search_by_author_name(author_name, max_results, year)
        return [paper.to_dict() for paper in papers] if papers else []
    except Exception as e:
        logger.error(f"search_hal_by_author failed: {e}")
        return [{"error": f"HAL author search failed for '{author_name}': {type(e).__name__}: {e}"}]


@mcp.tool()
async def get_hal_document(doc_id: str) -> Dict:
    """Get a specific document from HAL by its ID.

    Args:
        doc_id: HAL document ID (e.g., 'hal-01234567')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_hal_document("hal-01234567")
    """
    try:
        paper = hal_searcher.get_document_by_id(doc_id)
        return paper.to_dict() if paper else {"error": f"HAL document {doc_id} not found"}
    except Exception as e:
        logger.error(f"get_hal_document failed: {e}")
        return {"error": f"HAL document lookup failed for {doc_id}: {type(e).__name__}: {e}"}


@mcp.tool()
async def download_hal(
    doc_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of a HAL document.

    Args:
        doc_id: HAL document ID (e.g., 'hal-01234567')
        save_path: Directory to save the PDF (default: './downloads')
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').

    Returns:
        Path to downloaded PDF or error message.

    Example:
        await download_hal("hal-01234567")
    """
    try:
        save_path = await _resolve_save_path(save_path, ctx)
        result = hal_searcher.download_file(doc_id, save_path)
        return _apply_filename(result, filename)
    except Exception as e:
        logger.error(f"download_hal failed: {e}")
        return f"Download failed for HAL document {doc_id}: {type(e).__name__}: {e}"


@mcp.tool()
async def read_hal_paper(doc_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a HAL document.

    Args:
        doc_id: HAL document ID (e.g., 'hal-01234567')
        save_path: Directory where the PDF is/will be saved (default: './downloads')

    Returns:
        The extracted text content (abstract) of the document.

    Example:
        content = await read_hal_paper("hal-01234567")
    """
    try:
        return hal_searcher.read_paper(doc_id, save_path)
    except Exception as e:
        logger.error(f"read_hal_paper failed: {e}")
        return f"Failed to read HAL document {doc_id}: {type(e).__name__}: {e}"


# ============================================================================
# SSRN Tools
# ============================================================================

@mcp.tool()
async def search_ssrn(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    topic: Optional[str] = None
) -> List[Dict]:
    """Search academic papers from SSRN (Social Sciences Research Network).

    SSRN specializes in preprints and early-stage research in economics, finance,
    law, business, and social sciences.

    Args:
        query: Search query string (e.g., 'financial regulation', 'corporate governance')
        max_results: Maximum number of papers to return (default: 10)
        year: Optional year filter (e.g., '2020', '2018-2022')
        topic: Topic filter (e.g., 'Economics', 'Finance', 'Law', 'Business')

    Returns:
        List of paper metadata in dictionary format.

    Examples:
        # Basic search
        await search_ssrn("blockchain", 20)

        # Search by topic
        await search_ssrn("market efficiency", 15, topic="Finance")

        # Search with year filter
        await search_ssrn("climate finance", 10, year="2020-2023")
    """
    search_kwargs = {"year": year} if year else {}
    if topic:
        search_kwargs["topic"] = topic

    papers = ssrn_searcher.search(query, max_results, **search_kwargs)
    return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def search_ssrn_by_author(
    author_name: str,
    max_results: int = 10,
    year: Optional[str] = None
) -> List[Dict]:
    """Search for papers by author name in SSRN.

    Args:
        author_name: Name of the author (e.g., 'Luigi Zingales')
        max_results: Maximum number of papers to return (default: 10)
        year: Optional year filter (e.g., '2020', '2018-2022')

    Returns:
        List of papers by the author.

    Example:
        await search_ssrn_by_author("Andrei Shleifer", 15)
    """
    papers = ssrn_searcher.search_by_author(author_name, max_results, year)
    return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def get_ssrn_paper(paper_id: str) -> Dict:
    """Get a specific paper from SSRN by its ID.

    Args:
        paper_id: SSRN paper ID (e.g., '1234567')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_ssrn_paper("1234567")
    """
    paper = ssrn_searcher.get_paper_by_id(paper_id)
    return paper.to_dict() if paper else {}


@mcp.tool()
async def download_ssrn(
    paper_id: str,
    save_path: str = "./downloads",
    filename: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Download PDF of an SSRN paper.

    Args:
        paper_id: SSRN paper ID (e.g., '1234567')
        save_path: Directory to save the PDF (default: './downloads')
        filename: Optional custom filename for the saved PDF (e.g., 'my_paper.pdf').

    Returns:
        Path to downloaded PDF or error message.

    Note:
        SSRN may require login for some downloads. This attempts to download
        from publicly available sources.

    Example:
        await download_ssrn("1234567")
    """
    save_path = await _resolve_save_path(save_path, ctx)
    result = ssrn_searcher.download_pdf(paper_id, save_path)
    return _apply_filename(result, filename)


@mcp.tool()
async def read_ssrn_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an SSRN paper.

    Args:
        paper_id: SSRN paper ID (e.g., '1234567')
        save_path: Directory where the PDF is/will be saved (default: './downloads')

    Returns:
        The extracted text content (abstract) of the paper.

    Example:
        content = await read_ssrn_paper("1234567")
    """
    return ssrn_searcher.read_paper(paper_id, save_path)


# ============================================================================
# DBLP Tools
# ============================================================================

@mcp.tool()
async def search_dblp(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    venue_type: Optional[str] = None,
    venue: Optional[str] = None
) -> List[Dict]:
    """Search computer science publications from DBLP.

    DBLP indexes major CS conferences, journals, books, and theses.
    It's the primary bibliography for computer science research.

    Args:
        query: Search query string (e.g., 'transformer attention', 'federated learning')
        max_results: Maximum number of papers to return (default: 10, max: 1000)
        year: Optional year filter (e.g., '2020', '2018-2022')
        venue_type: Filter by type ('conference', 'journal', 'book', 'thesis')
        venue: Filter by venue name (e.g., 'CVPR', 'ICML', 'NeurIPS')

    Returns:
        List of paper metadata in dictionary format.

    Examples:
        # Basic search
        await search_dblp("neural architecture search", 20)

        # Search conference papers only
        await search_dblp("reinforcement learning", 15, venue_type="conference")

        # Search specific venue
        await search_dblp("attention", 10, venue="NeurIPS")
    """
    search_kwargs = {"year": year} if year else {}
    if venue_type:
        search_kwargs["venue_type"] = venue_type
    if venue:
        search_kwargs["venue"] = venue

    papers = dblp_searcher.search(query, max_results, **search_kwargs)
    return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def search_dblp_by_author(
    author_name: str,
    max_results: int = 10,
    year: Optional[str] = None
) -> List[Dict]:
    """Search for publications by author name in DBLP.

    Args:
        author_name: Name of the author (e.g., 'Geoffrey Hinton')
        max_results: Maximum number of papers to return (default: 10)
        year: Optional year filter (e.g., '2020', '2018-2022')

    Returns:
        List of papers by the author.

    Example:
        await search_dblp_by_author("Yann LeCun", 15)
    """
    papers = dblp_searcher.search_by_author(author_name, max_results, year)
    return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def search_dblp_venue(venue_name: str, max_results: int = 50) -> List[Dict]:
    """Search publications from a specific DBLP venue.

    Args:
        venue_name: Venue name (e.g., 'CVPR', 'ICML', 'NeurIPS', 'AAAI')
        max_results: Maximum number of papers to return (default: 50)

    Returns:
        List of papers from the venue.

    Example:
        await search_dblp_venue("NeurIPS", 100)
    """
    papers = dblp_searcher.search_venue(venue_name, max_results)
    return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def get_dblp_paper(key: str) -> Dict:
    """Get a specific paper from DBLP by its key.

    Args:
        key: DBLP key (e.g., 'conf/icml/GuptaM20', 'conf/nips/VaswaniSPU17')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_dblp_paper("conf/nips/VaswaniSPU17")
    """
    paper = dblp_searcher.get_paper_by_key(key)
    return paper.to_dict() if paper else {}


@mcp.tool()
async def get_dblp_top_conferences() -> List[Dict]:
    """Get list of major computer science conferences in DBLP.

    Returns:
        List of conference info with keys and names.

    Example:
        conferences = await get_dblp_top_conferences()
    """
    return dblp_searcher.get_top_conferences()


@mcp.tool()
async def get_dblp_top_journals() -> List[Dict]:
    """Get list of major computer science journals in DBLP.

    Returns:
        List of journal info with keys and names.

    Example:
        journals = await get_dblp_top_journals()
    """
    return dblp_searcher.get_top_journals()


def main():
    """Entry point for uvx and CLI execution."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
