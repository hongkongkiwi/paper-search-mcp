"""Sci-Hub downloader integration.

Simple wrapper adapted from scihub.py for downloading PDFs via Sci-Hub.
"""
from pathlib import Path
import re
import hashlib
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader


SCIHUB_MIRRORS = [
    "https://sci-hub.ru",
    "https://sci-hub.st",
    "https://sci-hub.su",
    "https://sci-hub.box",
    "https://sci-hub.red",
]


class SciHubFetcher:
    """Simple Sci-Hub PDF downloader."""

    def __init__(self, mirrors: list = None):
        """Initialize with list of Sci-Hub mirror URLs."""
        self.mirrors = [m.rstrip("/") for m in (mirrors or SCIHUB_MIRRORS)]
        self._failed_mirrors: set = set()
        self._mirror_statuses: dict[str, int] = {}
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def download_pdf(self, identifier: str, save_path: str = "./downloads") -> Optional[str]:
        """Download a PDF from Sci-Hub using a DOI, PMID, or URL.

        Args:
            identifier: DOI, PMID, or URL to the paper
            save_path: Directory to save the PDF

        Returns:
            Path to saved PDF or None on failure
        """
        if not identifier.strip():
            return "Error: empty identifier provided to Sci-Hub downloader"

        try:
            self._mirror_statuses = {}
            # Try each mirror in order, skipping known failed ones
            pdf_url = None
            for mirror in self.mirrors:
                if mirror in self._failed_mirrors:
                    continue
                pdf_url = self._get_direct_url(identifier, mirror)
                if pdf_url:
                    break
            if not pdf_url:
                tried = [m for m in self.mirrors if m not in self._failed_mirrors]
                failed = list(self._failed_mirrors)
                statuses = {
                    mirror: status
                    for mirror, status in self._mirror_statuses.items()
                }
                return (
                    f"Error: could not find PDF URL on any Sci-Hub mirror for: {identifier}. "
                    f"Tried mirrors: {tried}. Previously failed mirrors: {failed}. "
                    f"HTTP statuses: {statuses}"
                )

            # Download the PDF
            response = self.session.get(pdf_url, verify=False, timeout=30)

            if response.status_code != 200:
                return f"Error: Sci-Hub returned HTTP {response.status_code} when downloading PDF for: {identifier}"

            content_type = response.headers.get('Content-Type', 'unknown')
            if 'application/pdf' not in content_type:
                return f"Error: Sci-Hub returned non-PDF content (Content-Type: {content_type}) for: {identifier}"

            # Generate filename and save
            output_dir = Path(save_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = self._generate_filename(response, identifier)
            file_path = output_dir / filename

            with open(file_path, 'wb') as f:
                f.write(response.content)

            return str(file_path)

        except Exception as e:
            logging.error(f"Error downloading PDF for {identifier}: {e}")
            return f"Error downloading from Sci-Hub for {identifier}: {type(e).__name__}: {e}"

    def _get_direct_url(self, identifier: str, base_url: str) -> Optional[str]:
        """Get the direct PDF URL from a Sci-Hub mirror."""
        try:
            # If it's already a direct PDF URL, return it
            if identifier.endswith('.pdf'):
                return identifier

            # Search on Sci-Hub
            search_url = f"{base_url}/{identifier}"
            response = self.session.get(search_url, verify=False, timeout=20)

            if response.status_code != 200:
                self._failed_mirrors.add(base_url)
                self._mirror_statuses[base_url] = response.status_code
                logging.warning(f"Mirror {base_url} returned status {response.status_code}, marking as failed")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for article not found (mirror is working, paper just isn't available)
            if "article not found" in response.text.lower():
                logging.warning(f"Article not found on {base_url}")
                return None

            # Look for embed tag with PDF (most common in modern Sci-Hub)
            embed = soup.find('embed', {'type': 'application/pdf'})
            logging.debug(f"Found embed tag: {embed}")
            if embed:
                src = embed.get('src') if hasattr(embed, 'get') else None
                logging.debug(f"Embed src: {src}")
                if src and isinstance(src, str):
                    if src.startswith('//'):
                        pdf_url = 'https:' + src
                        logging.debug(f"Returning PDF URL: {pdf_url}")
                        return pdf_url
                    elif src.startswith('/'):
                        pdf_url = base_url + src
                        logging.debug(f"Returning PDF URL: {pdf_url}")
                        return pdf_url
                    else:
                        logging.debug(f"Returning PDF URL: {src}")
                        return src

            # Look for iframe with PDF (fallback)
            iframe = soup.find('iframe')
            if iframe:
                src = iframe.get('src') if hasattr(iframe, 'get') else None
                if src and isinstance(src, str):
                    if src.startswith('//'):
                        return 'https:' + src
                    elif src.startswith('/'):
                        return base_url + src
                    else:
                        return src

            # Look for download button with onclick
            for button in soup.find_all('button'):
                onclick = button.get('onclick', '') if hasattr(button, 'get') else ''
                if isinstance(onclick, str) and 'pdf' in onclick.lower():
                    # Extract URL from onclick JavaScript
                    url_match = re.search(r"location\.href='([^']+)'", onclick)
                    if url_match:
                        url = url_match.group(1)
                        if url.startswith('//'):
                            return 'https:' + url
                        elif url.startswith('/'):
                            return base_url + url
                        else:
                            return url

            # Look for direct download links
            for link in soup.find_all('a'):
                href = link.get('href', '') if hasattr(link, 'get') else ''
                if isinstance(href, str) and href and ('pdf' in href.lower() or href.endswith('.pdf')):
                    if href.startswith('//'):
                        return 'https:' + href
                    elif href.startswith('/'):
                        return base_url + href
                    elif href.startswith('http'):
                        return href

            return None

        except requests.exceptions.ConnectionError:
            self._failed_mirrors.add(base_url)
            logging.warning(f"Mirror {base_url} is unreachable, marking as failed")
            return None
        except requests.exceptions.Timeout:
            self._failed_mirrors.add(base_url)
            logging.warning(f"Mirror {base_url} timed out, marking as failed")
            return None
        except Exception as e:
            logging.error(f"Error getting direct URL from {base_url} for {identifier}: {e}")
            return None

    def read_paper(self, identifier: str, save_path: str = "./downloads") -> str:
        """Download and extract text from a paper via Sci-Hub.

        Args:
            identifier: DOI, PMID, article URL, or direct PDF URL.
            save_path: Directory where the PDF is/will be saved (default: './downloads').

        Returns:
            str: Extracted text from the PDF or error message.
        """
        try:
            pdf_path = self.download_pdf(identifier, save_path)
            if not pdf_path or pdf_path.startswith("Error"):
                return pdf_path or f"Failed to download PDF from Sci-Hub for: {identifier}"

            reader = PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
            text = "\n".join(text_parts).strip()
            return text or "No extractable text found in PDF."
        except Exception as e:
            logging.error(f"Error reading paper {identifier}: {e}")
            return f"Failed to read paper from Sci-Hub: {e}"

    def _generate_filename(self, response: requests.Response, identifier: str) -> str:
        """Generate a unique filename for the PDF."""
        # Try to get filename from URL
        url_parts = response.url.split('/')
        if url_parts:
            name = url_parts[-1]
            # Remove view parameters
            name = re.sub(r'#view=(.+)', '', name)
            if name.endswith('.pdf'):
                # Generate hash for uniqueness
                pdf_hash = hashlib.md5(response.content).hexdigest()[:8]
                base_name = name[:-4]  # Remove .pdf
                return f"{pdf_hash}_{base_name}.pdf"

        # Fallback: use identifier
        clean_identifier = re.sub(r'[^\w\-_.]', '_', identifier)
        pdf_hash = hashlib.md5(response.content).hexdigest()[:8]
        return f"{pdf_hash}_{clean_identifier}.pdf"
