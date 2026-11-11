from ..document import Document, DocumentChunk
from .base import ChunkingStrategy


class RecursiveChunker(ChunkingStrategy):
    """
    Recursively splits text using progressively smaller separators.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 100,
        separators: list[str] | None = None,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be >= 0 and < chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or ["\n\n", "\n", ". ", " "]

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

        pieces = self._recursive_split(text, self.separators)
        chunks = self._merge_pieces(pieces)

        result: list[DocumentChunk] = []
        cursor = 0
        for index, chunk_text in enumerate(chunks):
            start_idx = cursor
            end_idx = start_idx + len(chunk_text)
            result.append(
                DocumentChunk(
                    chunk_id=f"{document_id}_{index}",
                    document_id=document_id,
                    chunk_index=index,
                    text=chunk_text,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    source=source,
                    metadata={
                        **metadata,
                        "chunk_size": self.chunk_size,
                        "overlap": self.overlap,
                    },
                )
            )
            cursor = end_idx
        return result

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text.strip()]

        if not separators:
            return self._split_by_size(text)

        separator = separators[0]

        if separator not in text:
            return self._recursive_split(text, separators[1:])

        parts = text.split(separator)
        results: list[str] = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if len(part) <= self.chunk_size:
                results.append(part)
            else:
                results.extend(self._recursive_split(part, separators[1:]))

        return results

    def _split_by_size(self, text: str) -> list[str]:
        return [
            text[i : i + self.chunk_size]
            for i in range(0, len(text), self.chunk_size - self.overlap)
        ]

    def _merge_pieces(self, pieces: list[str]) -> list[str]:
        chunks: list[str] = []
        current = ""

        for piece in pieces:
            if not current:
                current = piece
                continue

            candidate = f"{current} {piece}"

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                chunks.append(current)
                overlap_text = current[-self.overlap:] if self.overlap else ""
                current = f"{overlap_text} {piece}".strip()

        if current:
            chunks.append(current)

        return chunks
