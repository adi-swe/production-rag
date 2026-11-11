import logging
from typing import Any, Mapping, Optional

from .cleaner import TextPreprocessor
from .document import DocumentChunk
from .strategies.fixed_size import FixedSizeChunker
from .strategies.recursive import RecursiveChunker
from .strategies.semantic import SemanticChunker
from .strategies.sentence import SentenceChunker


logger = logging.getLogger("rag_curator.processing.chunker")


class ChunkManager:
    """Manages chunking with multiple strategies."""

    def __init__(self):
        self.strategies = {
            "fixed": FixedSizeChunker,
            "recursive": RecursiveChunker,
            "semantic": SemanticChunker,
            "sentence": SentenceChunker,
        }

    @staticmethod
    def preprocess_text(text: str) -> str:
        """Preprocess text before chunking."""
        logger.info("Starting preprocessing for text of length %d", len(text))
        preprocessor = TextPreprocessor()
        text = preprocessor.clean_text(text)
        text = preprocessor.remove_headers_and_footers(text)
        logger.info("Preprocessing complete. Final text length: %d", len(text))
        return text

    def chunk(
        self,
        text: str,
        strategy: str,
        chunk_size: int,
        overlap: int,
        source: str = "",
        preprocess: bool = True,
    ) -> list[DocumentChunk]:
        """
        Chunk text using the specified strategy.
        """
        logger.info(
            "Chunking request: strategy=%s, chunk_size=%s, overlap=%s, source=%s, preprocess=%s",
            strategy,
            chunk_size,
            overlap,
            source,
            preprocess,
        )

        if strategy not in self.strategies:
            raise ValueError(
                f"Unknown strategy: {strategy}. Choose from {list(self.strategies.keys())}"
            )

        if preprocess:
            text = self.preprocess_text(text)

        strategy_cls = self.strategies[strategy]
        chunker = strategy_cls(chunk_size=chunk_size, overlap=overlap)
        chunks = chunker.chunk(text, source=source, document_id=source or "document")
        logger.info("Chunking complete: produced %d chunks for strategy=%s", len(chunks), strategy)
        return chunks

    def chunk_with_metadata(
        self,
        text: str,
        strategy: str = "fixed",
        chunk_size: int = 512,
        overlap: int = 50,
        source: str = "",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> list[DocumentChunk]:
        """Chunk text and add metadata to each chunk."""
        chunks = self.chunk(text, strategy, chunk_size, overlap, source)

        if metadata:
            logger.info("Attaching metadata to %d chunks", len(chunks))
            for chunk in chunks:
                chunk.metadata.update(metadata)

        return chunks
