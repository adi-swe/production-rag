from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ArXivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    pdf_url: str
    published: str
    updated: str | None
    categories: list[str]
    downloaded: bool = False
    download_path: Optional[str] = None
    download_timestamp: Optional[str] = None


class MetadataStore:
    """Load, persist, and export paper metadata."""

    def __init__(self, metadata_path: Path):
        self.metadata_path = metadata_path
        self.papers_metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, List[dict]]:
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        return data
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Error decoding metadata file: %s", exc)
        return {"papers": []}

    def _save_metadata(self):
        try:
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_path, "w", encoding="utf-8") as handle:
                json.dump(self.papers_metadata, handle, indent=2)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error saving metadata to JSON file: %s", exc)

    def find_by_arxiv_id(self, arxiv_id: str):
        return next(
            (paper for paper in self.papers_metadata.get("papers", []) if paper.get("arxiv_id") == arxiv_id),
            None,
        )

    def add_or_update(self, paper: Any):
        existing = self.find_by_arxiv_id(
            paper.arxiv_id if hasattr(paper, "arxiv_id") else paper.get("arxiv_id")
        )
        if existing:
            self.papers_metadata["papers"] = [
                p for p in self.papers_metadata["papers"] if p.get("arxiv_id") != (paper.arxiv_id if hasattr(paper, "arxiv_id") else paper.get("arxiv_id"))
            ]
        self.papers_metadata["papers"].append(
            asdict(paper) if hasattr(paper, "__dict__") else paper
        )
        self._save_metadata()

    def export_metadata_to_csv(self, output_path: Path):
        if not self.papers_metadata.get("papers"):
            logger.warning("No papers metadata to export.")
            return

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=[
                    "arxiv_id",
                    "title",
                    "authors",
                    "abstract",
                    "pdf_url",
                    "published",
                    "updated",
                    "categories",
                    "downloaded",
                    "download_path",
                    "download_timestamp",
                ],
            )
            writer.writeheader()

            for paper in self.papers_metadata["papers"]:
                row = paper if isinstance(paper, dict) else asdict(paper)
                writer.writerow({
                    "arxiv_id": row.get("arxiv_id"),
                    "title": row.get("title"),
                    "authors": ", ".join(row.get("authors", [])),
                    "abstract": row.get("abstract"),
                    "pdf_url": row.get("pdf_url"),
                    "published": row.get("published"),
                    "updated": row.get("updated"),
                    "categories": ", ".join(row.get("categories", [])),
                    "downloaded": row.get("downloaded"),
                    "download_path": row.get("download_path"),
                    "download_timestamp": row.get("download_timestamp"),
                })

        logger.info("Metadata exported to %s", output_path)
