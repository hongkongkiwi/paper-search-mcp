# paper_search_mcp/sources/pubmed.py
from typing import List
import requests
from xml.etree import ElementTree as ET
from datetime import datetime
from ..paper import Paper
import os
import logging

logger = logging.getLogger(__name__)


class PaperSource:
    """Abstract base class for paper sources"""
    def search(self, query: str, **kwargs) -> List[Paper]:
        raise NotImplementedError

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError

    def read_paper(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError


class PubMedSearcher(PaperSource):
    """Searcher for PubMed papers"""
    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def search(self, query: str, max_results: int = 10) -> List[Paper]:
        """Search PubMed for papers.

        Args:
            query: Search query string
            max_results: Maximum number of papers to return

        Returns:
            List of Paper objects
        """
        papers = []
        try:
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'xml'
            }
            search_response = requests.get(self.SEARCH_URL, params=search_params, timeout=30)
            search_response.raise_for_status()
            search_root = ET.fromstring(search_response.content)
            ids = [id.text for id in search_root.findall('.//Id')]

            if not ids:
                logger.info(f"No results found for query: {query}")
                return papers

            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(ids),
                'retmode': 'xml'
            }
            fetch_response = requests.get(self.FETCH_URL, params=fetch_params, timeout=30)
            fetch_response.raise_for_status()
            fetch_root = ET.fromstring(fetch_response.content)

            for article in fetch_root.findall('.//PubmedArticle'):
                try:
                    paper = self._parse_article(article)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing PubMed article: {e}")
                    continue

        except requests.RequestException as e:
            logger.error(f"Error fetching from PubMed: {e}")
        except ET.ParseError as e:
            logger.error(f"Error parsing PubMed response: {e}")

        return papers

    def _parse_article(self, article) -> Paper:
        """Parse a PubMed article element into a Paper object.

        Args:
            article: XML element from PubMed response

        Returns:
            Paper object or None if parsing fails
        """
        try:
            # Extract PMID
            pmid_elem = article.find('.//PMID')
            if pmid_elem is None or not pmid_elem.text:
                return None
            pmid = pmid_elem.text

            # Extract title
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None and title_elem.text else "No title"

            # Extract authors with safe access
            authors = []
            for author in article.findall('.//Author'):
                lastname = author.find('LastName')
                initials = author.find('Initials')
                if lastname is not None and lastname.text:
                    name = lastname.text
                    if initials is not None and initials.text:
                        name += f" {initials.text}"
                    authors.append(name)

            # Extract abstract
            abstract_elem = article.find('.//AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None and abstract_elem.text else ""

            # Extract publication date
            pub_date = None
            year_elem = article.find('.//PubDate/Year')
            if year_elem is not None and year_elem.text:
                try:
                    pub_date = datetime.strptime(year_elem.text, '%Y')
                except ValueError:
                    pub_date = datetime.now()
            else:
                pub_date = datetime.now()

            # Extract DOI
            doi = ""
            doi_elem = article.find('.//ELocationID[@EIdType="doi"]')
            if doi_elem is not None and doi_elem.text:
                doi = doi_elem.text

            return Paper(
                paper_id=pmid,
                title=title,
                authors=authors,
                abstract=abstract,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                pdf_url='',
                published_date=pub_date,
                updated_date=pub_date,
                source='pubmed',
                categories=[],
                keywords=[],
                doi=doi
            )
        except Exception as e:
            logger.error(f"Error parsing PubMed article: {e}")
            return None

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        """Attempt to download a paper's PDF from PubMed.

        Args:
            paper_id: PubMed ID (PMID)
            save_path: Directory to save the PDF

        Returns:
            str: Error message indicating PDF download is not supported
        
        Raises:
            NotImplementedError: Always raises this error as PubMed doesn't provide direct PDF access
        """
        message = ("PubMed does not provide direct PDF downloads. "
                  "Please use the paper's DOI or URL to access the publisher's website.")
        raise NotImplementedError(message)

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Attempt to read and extract text from a PubMed paper.

        Args:
            paper_id: PubMed ID (PMID)
            save_path: Directory for potential PDF storage (unused)

        Returns:
            str: Error message indicating PDF reading is not supported
        """
        message = ("PubMed papers cannot be read directly through this tool. "
                  "Only metadata and abstracts are available through PubMed's API. "
                  "Please use the paper's DOI or URL to access the full text on the publisher's website.")
        return message

if __name__ == "__main__":
    # 测试 PubMedSearcher 的功能
    searcher = PubMedSearcher()
    
    # 测试搜索功能
    print("Testing search functionality...")
    query = "machine learning"
    max_results = 5
    try:
        papers = searcher.search(query, max_results=max_results)
        print(f"Found {len(papers)} papers for query '{query}':")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title}")
            print(f"   Authors: {', '.join(paper.authors)}")
            print(f"   DOI: {paper.doi}")
            print(f"   URL: {paper.url}\n")
    except Exception as e:
        print(f"Error during search: {e}")
    
    # 测试 PDF 下载功能（会返回不支持的提示）
    if papers:
        print("\nTesting PDF download functionality...")
        paper_id = papers[0].paper_id
        try:
            pdf_path = searcher.download_pdf(paper_id, "./downloads")
        except NotImplementedError as e:
            print(f"Expected error: {e}")
    
    # 测试论文阅读功能（会返回不支持的提示）
    if papers:
        print("\nTesting paper reading functionality...")
        paper_id = papers[0].paper_id
        try:
            message = searcher.read_paper(paper_id)
            print(f"Response: {message}")
        except Exception as e:
            print(f"Error during paper reading: {e}")