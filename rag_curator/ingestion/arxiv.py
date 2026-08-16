"""
ArXiv Paper Downloader for RAG Curator

This script downloads papers from ArXiv with metadata extraction and PDF handling.
Features:
- Search by keywords, categories, and date ranges
- Rate-limited API requests (respects ArXiv's 3-second guideline)
- Metadata extraction and JSON storage
- Batch processing with error handling
- Configurable output paths
"""


import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# try:
#     from rag_curator.ingestion.metadata import ArXivPaper, MetadataStore
#     from rag_curator.ingestion.pdf import PdfDownloader
# except ImportError:  # pragma: no cover - supports direct script execution
from metadata import ArXivPaper, MetadataStore
from pdf import PdfDownloader


#Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class ArXivDownloader:
    """Downloads papers from ArXiv API with rate limiting and metadata extraction."""

    # ArXiv API base URL
    BASE_URL = "https://export.arxiv.org/api/query?"
    MIN_REQUEST_INTERVAL = 3.0  # Minimum interval between requests in seconds

    MAX_RESULTS_PER_QUERY = 2000  # Maximum results per query (ArXiv API limit)


    def __init__(
            self,
            data_dir: str = "data/arxiv",
            metadata_file: str = "papers_metadata.json",
            rate_limit: float = MIN_REQUEST_INTERVAL,
            max_results: int = MAX_RESULTS_PER_QUERY,
    ):
        """
        Initialize the ArXivDownloader.
        Args:
            data_dir (str): Directory to save downloaded PDFs and metadata.
            metadata_file (str): JSON file to store paper metadata.
            rate_limit (float): Minimum interval between API requests in seconds.
            max_results (int): Maximum number of results to fetch per query.
        """

        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.metadata_file = self.data_dir / metadata_file
        self.rate_limit = rate_limit
        self.max_results = max_results
        self.last_request_time = 0.0

        # Create directories if they don't exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_store = MetadataStore(self.metadata_file)
        self.papers_metadata = self.metadata_store.papers_metadata
        self.pdf_downloader = PdfDownloader(self.raw_dir, rate_limit=self.rate_limit)

    def _rate_limit(self):
        """Ensure that requests are rate-limited according to ArXiv's guidelines."""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.rate_limit:
            sleep_time = self.rate_limit - elapsed_time
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def search_papers(
            self, 
            query: str, 
            max_results: int = 100,
            sort_order: str = "submittedDate",
            sort_direction: str = "descending",
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> List[ArXivPaper]:
        """
        Search for papers on ArXiv based on a query and optional date range.
        Args:
            query (str): Search query (keywords, categories, etc.).
            max_results (int): Maximum number of results to fetch.
            sort_order (str): Field to sort by (e.g., "submittedDate").
            sort_direction (str): Sort direction ("ascending" or "descending").
            start_date (str): Optional start date in YYYY-MM-DD format.
            end_date (str): Optional end date in YYYY-MM-DD format.
        Returns:
            List[ArXivPaper]: List of ArXivPaper objects containing metadata.
        """

        papers = []

        search_query = query.strip()
        if search_query.startswith("cat:") and " cat:" not in search_query:
            search_query = search_query
        elif search_query.startswith("cat:"):
            search_query = search_query.replace("cat:cat:", "cat:")

        if start_date or end_date:
            date_filters = []
            if start_date:
                date_filters.append(f"submittedDate:[{start_date} TO *]")
            if end_date:
                date_filters.append(f"submittedDate:[* TO {end_date}]")
            if date_filters:
                search_query = f"({search_query}) AND ({' AND '.join(date_filters)})"
        
        for start in range(0, max_results, self.MAX_RESULTS_PER_QUERY):
            batch_size = min(self.MAX_RESULTS_PER_QUERY, max_results - start)
            logger.info(f"Fetching results {start + 1} to {start + batch_size}")

            params = {
                "search_query": search_query,
                "start": start,
                "max_results": batch_size,
                "sortBy": sort_order,
                "sortOrder": sort_direction
            }
            
            url = self.BASE_URL + urllib.parse.urlencode(params)
            print(f"Fetching URL: {url}")
            try:
                self._rate_limit()
                logger.info(f"Fetching {batch_size} papers from ArXiv API with query: {search_query}")

                response = urllib.request.urlopen(url)
                content = response.read().decode("utf-8")

                # Parse XML response using arxiv library
                root = ET.fromstring(content)
                namespace = {'atom': 'http://www.w3.org/2005/Atom'}

                # Parse each entry in the response
                entries = root.findall('atom:entry', namespace)

                if not entries:
                    logger.info("No more entries found.")
                    break

                for entry in entries:
                    paper = self._parse_arxiv_id(entry, namespace)
                    papers.append(paper)
                    logger.info(f"Found paper: {paper.arxiv_id} - {paper.title}")

            except urllib.error.HTTPError as e:
                logger.error(f"HTTP error occurred: {e.code} - {e.reason}")
                break
            except Exception as e:
                logger.error(f"Error occurred while rate limiting: {e}")
                break
        logger.info(f"Total papers fetched: {len(papers) + 1}")
        return papers


    def _parse_arxiv_id(self, entry, namespace: Dict[str, str]) -> ArXivPaper:
        """Parse a single entry from the ArXiv API response"""
        try:
            # Extract basic metadata from the entry
            paper ={
                "arxiv_id": entry.find('atom:id', namespace).text.split('/abs/')[-1],
                "title": entry.find('atom:title', namespace).text.strip(),
                "authors": [
                    author.find('atom:name', namespace).text 
                    for author in entry.findall('atom:author', namespace)
                ],
                "abstract": entry.find('atom:summary', namespace).text.strip(),
                "pdf_url": entry.find('atom:link[@type="application/pdf"]', namespace).attrib['href'],
                "published": entry.find('atom:published', namespace).text,
                "updated": entry.find('atom:updated', namespace).text if entry.find('atom:updated', namespace) is not None else None,

                "categories": [
                    category.attrib["term"]
                    for category in entry.findall("atom:category", namespace)
                ],
                "download_path": None,
                "download_timestamp": None
            }

            # Extract pdf_url from the entry's links
            for link in entry.findall('atom:link', namespace):
                if link.attrib.get('type') == 'application/pdf':
                    paper["pdf_url"] = link.attrib['href']
                    break

            return ArXivPaper(**paper)

        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            raise

    def download_papers(self, papers: List[ArXivPaper], download_pdfs: bool) -> List[Dict]:
        """
        Download papers and store metadata.
        Args:
            papers (List[ArXivPaper]): The papers to download.
            download_pdfs (bool): Whether to download the PDFs.
        Returns:
            List of papers with updated metadata.
        """
        downloaded_papers = []
        for i, paper in enumerate(papers, start=1):
            if paper is None:
                continue
            logger.info(f"Processing paper {i}/{len(papers)}: {paper.arxiv_id} - {paper.title}")

            existing = next(
                (p for p in self.papers_metadata["papers"] 
                 if p["arxiv_id"] == paper.arxiv_id), None
            )

            if existing and existing.get("downloaded"):
                logger.info(f"Paper {paper.arxiv_id} already downloaded. Skipping.")
                continue

            if download_pdfs and paper.pdf_url:
                try:
                    pdf_path = self.pdf_downloader.download_pdf(paper)
                    if pdf_path:
                        paper.downloaded = True
                        paper.download_path = str(pdf_path)
                        paper.download_timestamp = datetime.now().isoformat()
                    else:
                        paper.downloaded = False
                except Exception as e:
                    logger.error(f"Failed to download PDF for {paper.arxiv_id}: {e}")
                    paper.downloaded = False
            else:
                logger.info(f"Skipping PDF download for {paper.arxiv_id} as download_pdfs is False or pdf_url is missing.")
                paper.downloaded = False

            downloaded_papers.append(paper.__dict__)

        # Update metadata with newly downloaded papers
        self.papers_metadata["papers"].extend(downloaded_papers)
        self.metadata_store.papers_metadata = self.papers_metadata
        self.metadata_store._save_metadata()

        logger.info(f"Downloaded {len(downloaded_papers)} papers and updated metadata.")
        return downloaded_papers

    def _download_pdf(self, paper: ArXivPaper) -> Optional[Path]:
        """Download the PDF of a single paper and return the file path."""
        if not paper.pdf_url:
            logger.warning(f"No PDF URL for paper {paper.arxiv_id}. Skipping download.")
            return None

        try:
            filename = f"{paper.arxiv_id.replace('/', '_')}.pdf"
            file_path = self.raw_dir / filename

            if file_path.exists():
                logger.info(f"PDF for {paper.arxiv_id} already exists at {file_path}. Skipping download.")
                return file_path

            logger.info(f"Downloading PDF from {paper.pdf_url} to {file_path}")
            self._rate_limit()
            urllib.request.urlretrieve(paper.pdf_url, file_path)
            logger.info(f"Successfully downloaded PDF for {paper.arxiv_id} to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to download PDF for {paper.arxiv_id}: {e}")
            return None

    def get_papers_by_category(
        self,
        category: str,
        days_back: int = 7,
        max_results: int = 100,
    ) -> List[ArXivPaper]:
        """
        Get recent papers from a specific category.
        
        Args:
            category: ArXiv category (e.g., "cs.AI", "cs.CL", "stat.ML")
            days_back: Number of days to look back
            max_results: Maximum results to return
        
        Returns:
            List of papers
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        query = f"cat:{category}"
        return self.search_papers(
            query=query,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date
        )

    def export_metadata_to_csv(self, output_file: str = "papers_metadata.csv"):
        """Export the metadata to a specified CSV file."""
        try:
            output_path = self.processed_dir / output_file

            if not self.metadata_file.exists():
                logger.warning("No papers metadata to export.")
                return

            self.metadata_store.export_metadata_to_csv(output_path)
            logger.info(f"Metadata exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export metadata: {e}")

        
def main():
    """Example usage of the ArXivDownloader."""
    
    # Initialize downloader
    downloader = ArXivDownloader(data_dir="data")
    
    # Example 1: Search for machine learning papers from the last 30 days
    print("\n=== Searching for Machine Learning papers ===")
    ml_papers = downloader.search_papers(
        query="cat:cs.LG",
        max_results=5,  # Reduce for testing
    )
    
    # Download metadata (without PDFs for now)
    downloader.download_papers(ml_papers, download_pdfs=True)
    
    # Example 2: Search for NLP papers
    print("\n=== Searching for NLP papers ===")
    nlp_papers = downloader.search_papers(
        query="cat:cs.CL",
        max_results=5,
    )
    downloader.download_papers(nlp_papers, download_pdfs=True)
    
    # Export to CSV
    print("\n=== Exporting metadata ===")
    downloader.export_metadata_to_csv()
    
    print(f"\nTotal papers in database: {len(downloader.papers_metadata['papers']) + 1}")


if __name__ == "__main__":
    main()

