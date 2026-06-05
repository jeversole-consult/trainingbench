"""
Web scraper for HTML and PDF content.
Supports crawling websites and extracting text from HTML and PDF files.
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set, Optional
import pypdf
from pathlib import Path
import time


# Tunable defaults (env-overridable). Constructor arguments still win.
DEFAULT_SCRAPER_MAX_PAGES = int(os.getenv("SCRAPER_MAX_PAGES", "50"))
DEFAULT_SCRAPER_REQUEST_DELAY_SECONDS = float(os.getenv("SCRAPER_REQUEST_DELAY_SECONDS", "1.0"))
SCRAPER_REQUEST_TIMEOUT_SECONDS = int(os.getenv("SCRAPER_REQUEST_TIMEOUT_SECONDS", "30"))
# Threshold below which we assume a PDF is scanned (and therefore needs OCR
# rather than pypdf text extraction).
OCR_FALLBACK_MIN_CHARS = int(os.getenv("OCR_FALLBACK_MIN_CHARS", "100"))


class WebScraper:
    """Web scraper that extracts content from HTML pages and PDFs."""

    def __init__(
        self,
        max_pages: int = DEFAULT_SCRAPER_MAX_PAGES,
        delay: float = DEFAULT_SCRAPER_REQUEST_DELAY_SECONDS,
    ):
        """
        Initialize the web scraper.

        Args:
            max_pages: Maximum number of pages to scrape
            delay: Delay between requests in seconds
        """
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.scraped_data: List[Dict] = []
        self.last_error: Optional[str] = None

    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL is valid and belongs to the same domain."""
        parsed = urlparse(url)
        parsed_base = urlparse(base_domain)
        return (
            parsed.scheme in ['http', 'https'] and
            parsed.netloc == parsed_base.netloc
        )

    def extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file. Falls back to OCR for scanned PDFs."""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error extracting text from PDF {pdf_path}: {e}")

        if len(text.strip()) < OCR_FALLBACK_MIN_CHARS:
            print(f"OCR fallback for {pdf_path} (pypdf returned {len(text.strip())} chars)")
            try:
                from document_processor import DocumentProcessor
                with open(pdf_path, 'rb') as file:
                    pdf_bytes = file.read()
                result = DocumentProcessor.process_pdf(
                    pdf_bytes, os.path.basename(pdf_path), use_ocr=True
                )
                ocr_text = result.get("content", "")
                if len(ocr_text.strip()) > len(text.strip()):
                    return ocr_text
            except Exception as ocr_error:
                print(f"OCR fallback failed for {pdf_path}: {ocr_error}")

        return text

    def download_pdf(self, url: str, save_dir: str = "scraped_data") -> str:
        """Download a PDF file and return its local path."""
        os.makedirs(save_dir, exist_ok=True)

        filename = os.path.basename(urlparse(url).path)
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        filepath = os.path.join(save_dir, filename)

        try:
            response = requests.get(url, timeout=SCRAPER_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            return filepath
        except Exception as e:
            print(f"Error downloading PDF {url}: {e}")
            return None

    def scrape_page(self, url: str) -> Dict:
        """Scrape a single page and return its content."""
        try:
            response = requests.get(url, timeout=SCRAPER_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.exceptions.MissingSchema:
            self.last_error = f"URL '{url}' is missing a scheme (e.g. add 'https://' in front)."
            print(self.last_error)
            return None
        except requests.exceptions.InvalidURL as e:
            self.last_error = f"URL '{url}' is malformed: {e}"
            print(self.last_error)
            return None
        except requests.exceptions.SSLError as e:
            self.last_error = f"SSL certificate validation failed for '{url}': {e}"
            print(self.last_error)
            return None
        except requests.exceptions.ConnectTimeout:
            self.last_error = f"Connection to '{url}' timed out (host may be unreachable or blocking the scraper)."
            print(self.last_error)
            return None
        except requests.exceptions.ReadTimeout:
            self.last_error = f"Request to '{url}' timed out while waiting for response."
            print(self.last_error)
            return None
        except requests.exceptions.ConnectionError as e:
            msg = str(e)
            if "Name or service not known" in msg or "nodename nor servname" in msg or "getaddrinfo failed" in msg:
                self.last_error = f"DNS lookup failed for '{url}' (does the domain exist?)."
            elif "Connection refused" in msg:
                self.last_error = f"Connection refused by '{url}'."
            else:
                self.last_error = f"Could not connect to '{url}': {msg}"
            print(self.last_error)
            return None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            self.last_error = f"'{url}' returned HTTP {status}."
            print(self.last_error)
            return None
        except requests.exceptions.RequestException as e:
            self.last_error = f"Request to '{url}' failed: {e}"
            print(self.last_error)
            return None

        try:
            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type:
                # Handle PDF
                pdf_path = self.download_pdf(url)
                if pdf_path:
                    text = self.extract_text_from_pdf(pdf_path)
                    return {
                        'url': url,
                        'type': 'pdf',
                        'content': text,
                        'title': os.path.basename(pdf_path)
                    }
            else:
                # Handle HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.title.string if soup.title else url
                text = self.extract_text_from_html(response.text)

                return {
                    'url': url,
                    'type': 'html',
                    'content': text,
                    'title': title
                }

        except Exception as e:
            self.last_error = f"Failed to parse response from '{url}': {e}"
            print(self.last_error)
            return None

    def find_links(self, html_content: str, base_url: str) -> List[str]:
        """Find all links in HTML content, prioritizing PDFs."""
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        html_links = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            url = urljoin(base_url, href)
            # Remove fragments
            url = url.split('#')[0]

            # Prioritize PDF links
            if href.lower().endswith('.pdf') or 'pdf' in url.lower():
                pdf_links.append(url)
            else:
                html_links.append(url)

        # Return PDFs first, then HTML pages
        return pdf_links + html_links

    def crawl(self, start_url: str, max_depth: int = 3) -> List[Dict]:
        """
        Crawl a website starting from the given URL.

        Args:
            start_url: The starting URL to crawl
            max_depth: Maximum depth to crawl

        Returns:
            List of dictionaries containing scraped content
        """
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'https://' + start_url

        to_visit = [(start_url, 0)]
        base_domain = start_url

        while to_visit and len(self.visited_urls) < self.max_pages:
            url, depth = to_visit.pop(0)

            if url in self.visited_urls or depth > max_depth:
                continue

            if not self.is_valid_url(url, base_domain):
                continue

            print(f"Scraping ({len(self.visited_urls) + 1}/{self.max_pages}): {url}")

            self.visited_urls.add(url)
            page_data = self.scrape_page(url)

            if page_data:
                self.scraped_data.append(page_data)

                # If it's HTML, find more links to crawl
                if page_data['type'] == 'html':
                    try:
                        response = requests.get(url, timeout=SCRAPER_REQUEST_TIMEOUT_SECONDS)
                        links = self.find_links(response.text, url)

                        for link in links:
                            if link not in self.visited_urls:
                                to_visit.append((link, depth + 1))
                    except Exception as e:
                        print(f"Error finding links in {url}: {e}")

            # Be polite - delay between requests
            time.sleep(self.delay)

        return self.scraped_data

    def scrape_single_page(self, url: str) -> Dict:
        """Scrape a single page without crawling."""
        return self.scrape_page(url)

    def save_scraped_data(self, output_file: str = "scraped_data/scraped_content.txt"):
        """Save scraped data to a text file."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            for item in self.scraped_data:
                f.write(f"\n\n{'='*80}\n")
                f.write(f"URL: {item['url']}\n")
                f.write(f"Title: {item['title']}\n")
                f.write(f"Type: {item['type']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(item['content'])

        print(f"Saved scraped data to {output_file}")


if __name__ == "__main__":
    # Example usage
    scraper = WebScraper(max_pages=10, delay=1.0)

    # Example: Scrape Python documentation
    url = "https://docs.python.org/3/tutorial/"
    print(f"Starting to scrape: {url}")

    data = scraper.crawl(url, max_depth=2)
    scraper.save_scraped_data()

    print(f"\nScraped {len(data)} pages")
