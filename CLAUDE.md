# Paper Search MCP - Project Context for Claude Code

## Project Summary

This is a **Model Context Protocol (MCP) server** that provides LLMs with the ability to search and download academic papers from 16+ academic sources. It's designed to work with Claude Desktop and other MCP-compatible clients.

## Architecture

### Core Components

1. **server.py** - MCP server using FastMCP framework
   - Exposes ~70+ async tools for paper search, download, and reading
   - Each platform has: `search_<platform>`, `download_<platform>`, `read_<platform>_paper`
   - Some platforms have additional tools (citations, author search, venue search)

2. **paper.py** - `Paper` dataclass
   - Standardized format for paper metadata
   - `to_dict()` method for JSON serialization

3. **academic_platforms/** - Platform integrations
   - Each file: `arxiv.py`, `pubmed.py`, `semantic.py`, etc.
   - Class pattern: `PlatformSearcher` with `search()`, `download_pdf()`, `read_paper()`
   - Returns `List[Paper]` from search methods

4. **deduplication.py** - Duplicate handling
   - `deduplicate_paper_dicts()` - Remove duplicates by DOI/title/author+year
   - `merge_duplicate_papers()` - Merge metadata from duplicates
   - `find_duplicates()` - Find and report duplicate groups

## Supported Platforms (16 implemented)

| Platform | Search | Download | Notes |
|----------|--------|----------|-------|
| arXiv | Yes | Yes | Preprints, PDFs always available |
| PubMed | Yes | No | Abstracts only |
| bioRxiv | Yes | Yes | Biology preprints |
| medRxiv | Yes | Yes | Medicine preprints |
| Semantic Scholar | Yes | Yes | Citations, references, related papers |
| OpenAlex | Yes | Yes | Largest open index, rich metadata |
| CrossRef | Yes | No | DOI-based metadata |
| IACR ePrint | Yes | Yes | Cryptography papers |
| PMC | Yes | Yes | Full-text biomedical |
| HAL | Yes | Yes | French open archive, theses |
| SSRN | Yes | Yes | Social sciences preprints |
| DBLP | Yes | No | CS bibliography, no abstracts |
| Google Scholar | Yes | No | Web scraping, rate-limited |

## Key Design Patterns

### Paper Data Structure

```python
@dataclass
class Paper:
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    doi: str
    published_date: datetime
    pdf_url: str
    url: str
    source: str          # Platform name (e.g., "arxiv", "semantic")
    categories: List[str]
    keywords: List[str]
    citations: int
    references: List[str]
    extra: Dict          # Platform-specific metadata
```

### MCP Tool Pattern

```python
@mcp.tool()
async def search_<platform>(query: str, max_results: int = 10, **kwargs) -> List[Dict]:
    """Search papers from <platform>.

    Args:
        query: Search query string
        max_results: Maximum number of papers (default: 10)
        **kwargs: Platform-specific filters

    Returns:
        List of paper dictionaries.
    """
    papers = searcher.search(query, max_results, **kwargs)
    return [paper.to_dict() for paper in papers] if papers else []
```

### Error Handling

- Search methods return empty list `[]` on error
- Download/read methods return error message string
- All tools are async but wrap sync searchers via `sync_search()` helper

## Development Workflow

### Adding a New Platform

1. Create `academic_platforms/new_platform.py` with `NewPlatformSearcher` class
2. Implement `search()`, `download_pdf()`, `read_paper()` methods
3. Import and instantiate in `server.py`
4. Add `@mcp.tool()` decorated async functions
5. Create `tests/test_new_platform.py`
6. Run tests: `uv run pytest tests/test_new_platform.py -v`

### Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test
uv run pytest tests/test_arxiv.py -v

# Run with coverage
uv run pytest --cov=paper_search_mcp tests/
```

### Local Development Server

```bash
# Run MCP server (for Claude Desktop testing)
uv run paper-search-mcp

# Or with specific working directory
uv run --directory . paper-search-mcp
```

## Configuration

### Claude Desktop (Mac)

```json
{
  "mcpServers": {
    "paper_search_server": {
      "command": "uvx",
      "args": ["--from", "gh:hongkongkiwi/paper-search-mcp", "paper-search-mcp"],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "optional-key"
      }
    }
  }
}
```

### Environment Variables

- `SEMANTIC_SCHOLAR_API_KEY` - Optional, higher rate limits
- `CORE_API_KEY` - Optional, for CORE repository

## Common Issues

### Import Errors
- Ensure all platform imports are added to `server.py`
- Check class name matches filename (e.g., `SSRNSearcher` from `ssrn.py`)

### Tests Failing
- Some platforms have unreliable APIs or rate limits
- Mock responses for testing when needed
- Test both success and error paths

### Missing Tools
- After adding a platform, remember to expose MCP tools in `server.py`
- Follow the naming pattern: `search_<platform>`, `download_<platform>`, `read_<platform>_paper`

## File Locations

- Main code: `/paper_search_mcp/`
- Tests: `/tests/`
- Docs: `/docs/`
- Config: `/pyproject.toml`
- Lock file: `/uv.lock`

## Package Publishing

- Published to PyPI as `paper-search-mcp`
- GitHub Actions auto-publish on release
- Smithery registry: `@openags/paper-search-mcp`
