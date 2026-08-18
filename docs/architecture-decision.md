# Architecture Decision Records

## ADR 001: Use a text-first chunking pipeline

Status: Accepted

Date: 2026-08-18

### Context
The project ingests arXiv paper metadata and abstracts, then prepares text for retrieval-augmented generation. The chunking layer needs to be flexible enough to support different strategies while keeping the processing API simple and testable.

### Decision
We model the pipeline around a `Document` and a `DocumentChunk` abstraction, and we pass raw text strings through a `ChunkManager` that selects a chunking strategy.

This keeps the ingestion and retrieval layers independent from chunk strategy details while still allowing experiments with:

- fixed-size chunking
- recursive chunking
- sentence-based chunking
- semantic chunking

### Consequences
Benefits:
- the chunking logic is pluggable
- chunk metadata can be attached consistently
- strategy experiments are easy to compare in notebooks and scripts

Trade-offs:
- the API must remain consistent across strategies
- chunk boundaries and metadata fields must be normalized
- text preprocessing needs to be clearly separated from chunk boundary logic

---

## ADR 002: Keep preprocessing separate from chunking

Status: Accepted

Date: 2026-08-18

### Context
Text extracted from papers can contain repeated whitespace, header/footer noise, and formatting artifacts. These issues should be handled before final chunk boundaries are created.

### Decision
The `TextPreprocessor` is responsible for cleaning raw text, while `ChunkManager` decides when to run preprocessing for a given chunking task.

### Consequences
Benefits:
- cleaner chunk texts
- less noisy retrieval inputs
- easier debugging of chunking behavior

Trade-offs:
- preprocessing can slightly change token boundaries
- some documents may require custom cleaning passes depending on source format

---

## ADR 003: Metadata is associated with chunks, not only documents

Status: Accepted

Date: 2026-08-18

### Context
Chunks often need provenance such as paper id, source, title, or category information when they are later stored or queried.

### Decision
Each `DocumentChunk` stores a `metadata` dict and a `source` field. The chunk manager can merge source-level metadata into each chunk.

### Consequences
Benefits:
- richer retrieval context
- easier debugging and analytics
- source attribution remains intact after chunking

Trade-offs:
- metadata increases payload size
- some chunkers need to be careful not to duplicate excessive metadata fields
