# Processing Flow

## High-level flow

1. Metadata is loaded from the arXiv source data.
2. A paper record or abstract text is selected for processing.
3. The text is optionally cleaned by `TextPreprocessor`.
4. A `ChunkManager` chooses a chunking strategy.
5. The selected strategy creates `DocumentChunk` objects.
6. Chunk metadata is attached for retrieval and provenance.
7. Chunks can be serialized to JSON or passed into the retrieval stack.

## Practical flow for this project

```text
JSON metadata file
        |
        v
paper record / abstract text
        |
        v
TextPreprocessor.clean_text()
        |
        v
ChunkManager.chunk(..., strategy=...)
        |
        +--> FixedSizeChunker
        +--> RecursiveChunker
        +--> SentenceChunker
        +--> SemanticChunker
        |
        v
DocumentChunk[]
        |
        v
metadata + source + text persisted for retrieval
```

## Data source path used in experiments

The notebook experiments currently read directly from:

- [data/sample_arxiv_metadata.json](../data/sample_arxiv_metadata.json)

They extract an abstract or paper text and then pass it into the chunking API rather than having the processing package load the JSON file itself.

## Processing package responsibilities

- [rag_curator/processing/cleaner.py](../rag_curator/processing/cleaner.py): normalize and clean raw text
- [rag_curator/processing/document.py](../rag_curator/processing/document.py): define `Document` and `DocumentChunk`
- [rag_curator/processing/chunker.py](../rag_curator/processing/chunker.py): choose and run strategy
- [rag_curator/processing/strategies](../rag_curator/processing/strategies): strategy implementations

## Notes

The processing layer is intentionally text-oriented. It accepts a string or a `Document` object, and it emits chunk objects with a standard schema so the ingestion and retrieval layers can remain decoupled from the specific chunking algorithm.
