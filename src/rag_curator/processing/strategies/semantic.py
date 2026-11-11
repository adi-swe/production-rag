from collections.abc import Callable

from ..document import Document, DocumentChunk
from .base import ChunkingStrategy


class SemanticChunker(ChunkingStrategy):
    """
    Splits text when semantic similarity between neighboring sentences falls below a threshold.
    """

    def __init__(
        self,
        embed: Callable[[list[str]], list[list[float]]] | None = None,
        similarity_threshold: float = 0.5,
        chunk_size: int = 500,
        overlap: int = 50,
    ):
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")

        self.embed = embed or (lambda texts: [[1.0, 0.0] for _ in texts])
        self.similarity_threshold = similarity_threshold
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        document: Document | str,
        source: str = "",
        document_id: str = "",
    ) -> list[DocumentChunk]:
        text = document.text if isinstance(document, Document) else str(document)
        document_id = document_id or (
            document.document_id if isinstance(document, Document) else source or "document"
        )
        metadata = document.metadata.copy() if isinstance(document, Document) else {}
        source = source or (document.metadata.get("source", "") if isinstance(document, Document) else "")

        sentences = self._split_sentences(text)

        if not sentences:
            return []

        if len(sentences) == 1:
            return [self._create_chunk(document_id, sentences, 0, metadata, source)]

        embeddings = self.embed(sentences)
        chunks: list[DocumentChunk] = []
        current = [sentences[0]]
        chunk_index = 0
        cursor = 0

        for index in range(1, len(sentences)):
            similarity = self._cosine_similarity(embeddings[index - 1], embeddings[index])

            if similarity < self.similarity_threshold:
                chunks.append(self._create_chunk(document_id, current, chunk_index, cursor, metadata, source))
                chunk_index += 1
                cursor += len(" ".join(current))
                current = []

            current.append(sentences[index])

        if current:
            chunks.append(self._create_chunk(document_id, current, chunk_index, cursor, metadata, source))

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    @staticmethod
    def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        magnitude_a = sum(a * a for a in vector_a) ** 0.5
        magnitude_b = sum(b * b for b in vector_b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    def _create_chunk(
        self,
        document_id: str,
        sentences: list[str],
        chunk_index: int,
        start_idx: int,
        metadata: dict,
        source: str,
    ) -> DocumentChunk:
        text = " ".join(sentences)
        return DocumentChunk(
            chunk_id=f"{document_id}_{chunk_index}",
            document_id=document_id,
            chunk_index=chunk_index,
            text=text,
            start_idx=start_idx,
            end_idx=start_idx + len(text),
            source=source,
            metadata={
                **metadata,
                "similarity_threshold": self.similarity_threshold,
            },
        )
