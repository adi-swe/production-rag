from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Document:
    """
    Represents a complete document.

    A Document normally comes from the ingestion layer.
    """

    document_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass
class DocumentChunk:
    """
    Represents a searchable chunk of a document.
    """

    chunk_id: int | str
    document_id: str
    chunk_index: int
    text: str
    start_idx: int = 0
    end_idx: int = 0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the chunk into a dictionary.
        """

        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "source": self.source,
            "metadata": self.metadata,
        }