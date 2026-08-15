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

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import urllib.request
import urllib.parse
from xml.etree import ElementTree as ET
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArXivDownloader:
    """Downloads papers from ArXiv API with rate limiting and metadata extraction."""
    
    # ArXiv API base URL
    BASE_URL = "http://export.arxiv.org/api/query?"
    
    # Rate limit: ArXiv requests users to wait 3 seconds between API calls
    MIN_REQUEST_INTERVAL = 3.0
    
    # Maximum results per API call
    MAX_RESULTS_PER_QUERY = 2000
    
    def __init__(
        self,
        data_dir: str = "data",
        metadata_file: str = "papers_metadata.json",
        rate_limit: float = MIN_REQUEST_INTERVAL,
    ):
        """
        Initialize the ArXiv downloader.
        
        Args:
            data_dir: Base directory for storing data
            metadata_file: JSON file to store paper metadata
            rate_limit: Seconds to wait between API requests
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.metadata_file = self.processed_dir / metadata_file
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load existing metadata from JSON file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
        return {"papers": []}
    
    def _save_metadata(self):
        """Save metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.info(f"Metadata saved to {self.metadata_file}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _respect_rate_limit(self):
        """Wait if necessary to respect ArXiv's rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def search(
        self,
        query: str,
        max_results: int = 100,
        sort_order: str = "submittedDate",
        sort_direction: str = "descending",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search ArXiv for papers.
        
        Args:
            query: Search query (e.g., "cat:cs.AI", "all:machine learning")
            max_results: Maximum number of results to return
            sort_order: "submittedDate", "lastUpdatedDate", or "relevance"
            sort_direction: "ascending" or "descending"
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        
        Returns:
            List of paper dictionaries with metadata
        """
        papers = []
        
        # Build search query with date filter if provided
        search_query = query
        if start_date or end_date:
            date_filters = []
            if start_date:
                date_filters.append(f"submittedDate:[{start_date}000000 TO *]")
            if end_date:
                date_filters.append(f"submittedDate:[* TO {end_date}235959]")
            if date_filters:
                search_query = f"({query}) AND ({' AND '.join(date_filters)})"
        
        # Paginate through results
        for start in range(0, max_results, self.MAX_RESULTS_PER_QUERY):
            batch_size = min(self.MAX_RESULTS_PER_QUERY, max_results - start)
            
            params = {
                "search_query": search_query,
                "start": start,
                "max_results": batch_size,
                "sortBy": sort_order,
                "sortOrder": sort_direction,
            }
            
            url = self.BASE_URL + urllib.parse.urlencode(params)
            
            try:
                self._respect_rate_limit()
                logger.info(f"Fetching {batch_size} results starting from {start}")
                
                response = urllib.request.urlopen(url, timeout=30)
                content = response.read().decode('utf-8')
                
                # Parse XML response
                root = ET.fromstring(content)
                
                # Extract namespace
                namespace = {'atom': 'http://www.w3.org/2005/Atom'}
                
                # Parse entries
                entries = root.findall('atom:entry', namespace)
                
                if not entries:
                    logger.info("No more results found")
                    break
                
                for entry in entries:
                    paper = self._parse_entry(entry, namespace)
                    papers.append(paper)
                    logger.info(f"Found: {paper['title']}")
                
            except urllib.error.HTTPError as e:
                logger.error(f"HTTP error {e.code}: {e.reason}")
                break
            except Exception as e:
                logger.error(f"Error fetching results: {e}")
                break
        
        logger.info(f"Search complete. Found {len(papers)} papers")
        return papers
    
    def _parse_entry(self, entry, namespace: Dict) -> Dict:
        """Parse a single ArXiv entry into a paper dictionary."""
        try:
            # Extract basic metadata
            paper = {
                "arxiv_id": entry.find('atom:id', namespace).text.split('/abs/')[-1],
                "title": entry.find('atom:title', namespace).text.strip(),
                "authors": [
                    author.find('atom:name', namespace).text
                    for author in entry.findall('atom:author', namespace)
                ],
                "published": entry.find('atom:published', namespace).text,
                "updated": entry.find('atom:updated', namespace).text,
                "summary": entry.find('atom:summary', namespace).text.strip(),
                "categories": [
                    category.get('term')
                    for category in entry.findall('atom:category', namespace)
                ],
                "pdf_url": None,
                "downloaded": False,
            }
            
            # Extract PDF URL
            for link in entry.findall('atom:link', namespace):
                if link.get('title') == 'pdf':
                    paper["pdf_url"] = link.get('href')
                    break
            
            return paper
        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None
    
    def download_papers(self, papers: List[Dict], download_pdfs: bool = False) -> List[Dict]:
        """
        Download papers and store metadata.
        
        Args:
            papers: List of paper dictionaries from search()
            download_pdfs: Whether to download PDF files
        
        Returns:
            List of papers with local file paths
        """
        downloaded_papers = []
        
        for i, paper in enumerate(papers, 1):
            if paper is None:
                continue
            
            logger.info(f"Processing paper {i}/{len(papers)}: {paper['arxiv_id']}")
            
            # Check if already downloaded
            existing = next(
                (p for p in self.metadata["papers"] if p["arxiv_id"] == paper["arxiv_id"]),
                None
            )
            
            if existing and existing.get("downloaded"):
                logger.info(f"Paper {paper['arxiv_id']} already downloaded, skipping")
                downloaded_papers.append(existing)
                continue
            
            # Download PDF if requested
            if download_pdfs and paper.get("pdf_url"):
                pdf_path = self._download_pdf(paper)
                if pdf_path:
                    paper["pdf_path"] = str(pdf_path)
            
            # Add download timestamp
            paper["download_timestamp"] = datetime.now().isoformat()
            paper["downloaded"] = True
            
            # Update metadata
            if existing:
                self.metadata["papers"].remove(existing)
            self.metadata["papers"].append(paper)
            
            downloaded_papers.append(paper)
        
        # Save metadata
        self._save_metadata()
        
        logger.info(f"Downloaded metadata for {len(downloaded_papers)} papers")
        return downloaded_papers
    
    def _download_pdf(self, paper: Dict) -> Optional[Path]:
        """Download PDF file for a paper."""
        if not paper.get("pdf_url"):
            return None
        
        try:
            # Create filename from arxiv_id
            filename = f"{paper['arxiv_id'].replace('/', '_')}.pdf"
            filepath = self.raw_dir / filename
            
            if filepath.exists():
                logger.info(f"PDF already exists: {filepath}")
                return filepath
            
            logger.info(f"Downloading PDF: {paper['pdf_url']}")
            
            self._respect_rate_limit()
            urllib.request.urlretrieve(paper["pdf_url"], filepath)
            
            logger.info(f"PDF saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to download PDF for {paper['arxiv_id']}: {e}")
            return None
    
    def get_papers_by_category(
        self,
        category: str,
        days_back: int = 7,
        max_results: int = 100,
    ) -> List[Dict]:
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
        return self.search(
            query=query,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date,
        )
    
    def export_metadata_csv(self, output_file: str = "papers_metadata.csv"):
        """Export metadata to CSV format."""
        try:
            import csv
            
            output_path = self.processed_dir / output_file
            
            if not self.metadata["papers"]:
                logger.warning("No papers to export")
                return
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "arxiv_id",
                        "title",
                        "authors",
                        "published",
                        "categories",
                        "summary",
                        "pdf_url",
                    ]
                )
                writer.writeheader()
                
                for paper in self.metadata["papers"]:
                    writer.writerow({
                        "arxiv_id": paper["arxiv_id"],
                        "title": paper["title"],
                        "authors": "; ".join(paper["authors"]),
                        "published": paper["published"],
                        "categories": "; ".join(paper["categories"]),
                        "summary": paper["summary"][:200] + "...",
                        "pdf_url": paper.get("pdf_url", ""),
                    })
            
            logger.info(f"Metadata exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")


def main():
    """Example usage of the ArXivDownloader."""
    
    # Initialize downloader
    downloader = ArXivDownloader(data_dir="data")
    
    # Example 1: Search for machine learning papers from the last 30 days
    print("\n=== Searching for Machine Learning papers ===")
    ml_papers = downloader.search(
        query="cat:cs.LG",
        max_results=5,  # Reduce for testing
    )
    
    # Download metadata (without PDFs for now)
    downloader.download_papers(ml_papers, download_pdfs=False)
    
    # Example 2: Search for NLP papers
    print("\n=== Searching for NLP papers ===")
    nlp_papers = downloader.search(
        query="cat:cs.CL",
        max_results=5,
    )
    downloader.download_papers(nlp_papers, download_pdfs=False)
    
    # Export to CSV
    print("\n=== Exporting metadata ===")
    downloader.export_metadata_csv()
    
    print(f"\nTotal papers in database: {len(downloader.metadata['papers'])}")


if __name__ == "__main__":
    main()

