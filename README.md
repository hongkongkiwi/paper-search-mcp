# Paper Search MCP

A Model Context Protocol (MCP) server for searching and downloading academic papers from multiple sources, including arXiv, PubMed, Semantic Scholar, OpenAlex, and more. Designed for seamless integration with large language models like Claude Desktop.

![PyPI](https://img.shields.io/pypi/v/paper-search-mcp.svg) ![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
[![smithery badge](https://smithery.ai/badge/@openags/paper-search-mcp)](https://smithery.ai/server/@openags/paper-search-mcp)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Quick Start](#quick-start)
    - [Install Package](#install-package)
    - [Configure Claude Desktop](#configure-claude-desktop)
  - [For Development](#for-development)
    - [Setup Environment](#setup-environment)
    - [Install Dependencies](#install-dependencies)
- [Contributing](#contributing)
- [Demo](#demo)
- [License](#license)
- [TODO](#todo)

---

## Overview

`paper-search-mcp` is a Python-based MCP server that enables users to search and download academic papers from various platforms. It provides tools for searching papers (e.g., `search_arxiv`) and downloading PDFs (e.g., `download_arxiv`), making it ideal for researchers and AI-driven workflows. Built with the MCP Python SDK, it integrates seamlessly with LLM clients like Claude Desktop.

---

## Features

- **Multi-Source Support**: Search and download papers from:
  - **arXiv** - Preprint papers in physics, math, computer science, and more
  - **PubMed** - Biomedical and life sciences literature
  - **bioRxiv** - Preprints in biology and life sciences
  - **medRxiv** - Preprints in medicine and health sciences
  - **Semantic Scholar** - AI-powered academic search with citations and references
  - **OpenAlex** - Open index of scholarly papers with rich metadata
  - **CrossRef** - DOI-based metadata search
  - **IACR ePrint Archive** - Cryptography and security papers
  - **PubMed Central (PMC)** - Full-text biomedical papers
  - **HAL** - French open archive for multidisciplinary research
  - **SSRN** - Social sciences research network
  - **DBLP** - Computer science bibliography
  - **Google Scholar** - Web-based academic search (PDF download via Sci-Hub)
- **Standardized Output**: Papers are returned in a consistent dictionary format via the `Paper` class.
- **PDF Download**: Download papers directly to local storage.
- **Paper Reading**: Extract and read text from downloaded PDFs.
- **Citation Tracking**: Get citations and references for papers (Semantic Scholar, OpenAlex).
- **Deduplication**: Built-in tools to remove duplicate papers.
- **MCP Integration**: Compatible with MCP clients for LLM context enhancement.
- **Extensible Design**: Easily add new academic platforms by extending the `academic_platforms` module.

---

## Installation

`paper-search-mcp` can be installed using `uv`, `uvx`, or `pip`. Below are several approaches for different use cases.

### Quick Install with uvx (Recommended)

The easiest way to run paper-search-mcp is using `uvx` with your GitHub repository:

```bash
# Run directly from GitHub
uvx --from gh:hongkongkiwi/paper-search-mcp paper-search-mcp
```

**Claude Desktop Configuration with uvx:**

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "paper_search_server": {
      "command": "uvx",
      "args": [
        "--from",
        "gh:hongkongkiwi/paper-search-mcp",
        "paper-search-mcp"
      ],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": ""
      }
    }
  }
}
```

### Installing via Smithery

To install paper-search-mcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@openags/paper-search-mcp):

```bash
npx -y @smithery/cli install @openags/paper-search-mcp --client claude
```

### Local Installation with uv

For local development or to install from source:

1. **Clone and Install**:

   ```bash
   git clone https://github.com/hongkongkiwi/paper-search-mcp.git
   cd paper-search-mcp
   uv sync
   ```

2. **Configure Claude Desktop** (for local development):
   ```json
   {
     "mcpServers": {
       "paper_search_server": {
         "command": "uv",
         "args": [
           "run",
           "--directory",
           "/path/to/paper-search-mcp",
           "paper-search-mcp"
         ],
         "env": {
           "SEMANTIC_SCHOLAR_API_KEY": ""
         }
       }
     }
   }
   ```

### Pip Installation

```bash
pip install paper-search-mcp
```

Then run with:
```bash
paper-search-mcp
```

### For Development

For developers who want to modify the code or contribute:

1. **Setup Environment**:

   ```bash
   # Install uv if not installed
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Clone repository
   git clone https://github.com/openags/paper-search-mcp.git
   cd paper-search-mcp

   # Create and activate virtual environment
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install Dependencies**:

   ```bash
   # Install project in editable mode
   uv add -e .

   # Add development dependencies (optional)
   uv add pytest flake8
   ```

---

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork the Repository**:
   Click "Fork" on GitHub at https://github.com/hongkongkiwi/paper-search-mcp

2. **Clone and Set Up**:

   ```bash
   git clone https://github.com/yourusername/paper-search-mcp.git
   cd paper-search-mcp
   uv sync
   ```

3. **Make Changes**:

   - Add new platforms in `academic_platforms/`.
   - Update tests in `tests/`.
   - Run tests: `uv run pytest tests/`

4. **Submit a Pull Request**:
   Push changes and create a PR on GitHub.

---

## Demo

<img src="docs\images\demo.png" alt="Demo" width="800">

## Supported Academic Platforms

### Completed Platforms

| Platform | Status | Search | Download | Notes |
|----------|--------|--------|----------|-------|
| arXiv | Done | Yes | Yes | Preprint server |
| PubMed | Done | Yes | No | Abstracts only |
| bioRxiv | Done | Yes | Yes | Biology preprints |
| medRxiv | Done | Yes | Yes | Medicine preprints |
| Semantic Scholar | Done | Yes | Yes | AI-powered, citations |
| OpenAlex | Done | Yes | Yes | Rich metadata |
| CrossRef | Done | Yes | No | DOI-based |
| IACR ePrint | Done | Yes | Yes | Cryptography |
| PMC | Done | Yes | Yes | Full-text biomedical |
| HAL | Done | Yes | Yes | French open archive |
| SSRN | Done | Yes | Yes | Social sciences |
| DBLP | Done | Yes | No | CS bibliography |
| Google Scholar | Done | Yes | No | Web-based |

### Future Platforms

- Science Direct
- Springer Link
- IEEE Xplore
- ACM Digital Library
- JSTOR
- ResearchGate

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

Happy researching with `paper-search-mcp`! If you encounter issues, open a GitHub issue.
