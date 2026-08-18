import logging

from rag_curator.processing.document import Document, DocumentChunk
from .base import ChunkingStrategy


class FixedSizeChunker(ChunkingStrategy):
    """
    Fixed-size chunking with optional overlap.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if overlap < 0:
            raise ValueError("overlap cannot be negative")

        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.step = chunk_size - overlap

    def chunk(
        self,
        document: Document | str,
        source: str = "",
        document_id: str = "",
    ) -> list[DocumentChunk]:
        """Split text or a document into fixed-size chunks with optional overlap."""
        text = document.text if isinstance(document, Document) else str(document)
        document_id = document_id or (
            document.document_id if isinstance(document, Document) else source or "document"
        )
        metadata = document.metadata.copy() if isinstance(document, Document) else {}
        source = source or (document.metadata.get("source", "") if isinstance(document, Document) else "")

        chunks: list[DocumentChunk] = []
        chunk_id = 0

        for start_idx in range(0, len(text), self.step):
            end_idx = min(start_idx + self.chunk_size, len(text))
            chunk_text = text[start_idx:end_idx]

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=chunk_id,
                text=chunk_text,
                start_idx=start_idx,
                end_idx=end_idx,
                source=source,
                metadata=metadata.copy(),
            )

            chunks.append(chunk)
            chunk_id += 1

        logging.info(
            f"Document {document_id} chunked into {len(chunks)} chunks "
            f"with chunk_size={self.chunk_size} and overlap={self.overlap}"
        )
        return chunks
