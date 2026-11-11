import re

from ..document import Document, DocumentChunk
from .base import ChunkingStrategy


class SentenceChunker(ChunkingStrategy):
    """
    Groups sentences until the approximate word limit is reached.
    """

    SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")

    def __init__(
        self,
        max_words: int = 500,
        overlap_sentences: int = 1,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ):
        if chunk_size is not None:
            max_words = chunk_size

        if overlap is not None:
            overlap_sentences = max(0, min(overlap, max_words))

        if max_words <= 0:
            raise ValueError("max_words must be greater than 0")

        if overlap_sentences < 0:
            raise ValueError("overlap_sentences cannot be negative")

        self.max_words = max_words
        self.overlap_sentences = overlap_sentences

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

        chunks: list[DocumentChunk] = []
        current_sentences: list[str] = []
        current_word_count = 0
        chunk_index = 0
        cursor = 0

        for sentence in sentences:
            sentence_word_count = len(sentence.split())

            if current_sentences and current_word_count + sentence_word_count > self.max_words:
                chunks.append(
                    self._create_chunk(
                        document_id,
                        current_sentences,
                        chunk_index,
                        cursor,
                        metadata,
                        source,
                    )
                )

                chunk_index += 1
                overlap = current_sentences[-self.overlap_sentences:]
                current_sentences = overlap.copy()
                current_word_count = sum(len(s.split()) for s in current_sentences)
                cursor = max(0, cursor - len(" ".join(overlap)))

            current_sentences.append(sentence)
            current_word_count += sentence_word_count

        if current_sentences:
            chunks.append(
                self._create_chunk(
                    document_id,
                    current_sentences,
                    chunk_index,
                    cursor,
                    metadata,
                    source,
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        sentences = self.SENTENCE_PATTERN.split(text)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

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
                "max_words": self.max_words,
                "overlap_sentences": self.overlap_sentences,
            },
        )
