from __future__ import annotations

import logging
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PdfDownloader:
    """Handle PDF downloads and local file storage."""

    def __init__(self, raw_dir: Path, rate_limit: float = 3.0):
        self.raw_dir = raw_dir
        self.rate_limit = rate_limit 
        self.last_request_time = 0.0
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.info("Rate limiting: sleeping for %.2f seconds", sleep_time)
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def download_pdf(self, paper: Any) -> Optional[Path]:
        pdf_url = getattr(paper, "pdf_url", None) or paper.get("pdf_url")
        arxiv_id = getattr(paper, "arxiv_id", None) or paper.get("arxiv_id")

        if not pdf_url or not arxiv_id:
            logger.warning("No PDF URL for paper %s. Skipping download.", arxiv_id)
            return None

        file_path = self.raw_dir / f"{arxiv_id.replace('/', '_')}.pdf"
        if file_path.exists():
            logger.info("PDF already exists for %s at %s", arxiv_id, file_path)
            return file_path

        try:
            self._rate_limit()
            logger.info("Downloading PDF from %s to %s", pdf_url, file_path)
            urllib.request.urlretrieve(pdf_url, file_path)
            logger.info("Successfully downloaded PDF for %s to %s", arxiv_id, file_path)
            return file_path
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to download PDF for %s: %s", arxiv_id, exc)
            return None
