from abc import ABC, abstractmethod

from rag_curator.processing.document import Document, DocumentChunk


class ChunkingStrategy(ABC):
    """
    Base interface for all chunking strategies.
    """

    @abstractmethod
    def chunk(
        self,
        document: Document | str,
        source: str = "",
        document_id: str = "",
    ) -> list[DocumentChunk]:
        """
        Split a document or raw text string into chunks.
        """
        raise NotImplementedError