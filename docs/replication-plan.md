# Production Agentic RAG replication plan

Status: proposed implementation backlog. No implementation or deployment is included in this change.

Upstream scanned: 19 October 2026. Local file structure reviewed: 11 November 2026.

Reference: [jamwithai/production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course), `main` at commit `424a0eb99edf841994f2a9a053912b489d2a94ff`.

## Goal and approach

Extend this repository into an arXiv research assistant with the reference project's end-to-end capabilities: scheduled paper ingestion, PDF parsing, persistent metadata, keyword and semantic retrieval, grounded answers with citations, streaming chat, tracing, caching, and bounded agentic retrieval. Use the current `src` package layout and preserve the accepted decisions in [architecture-decision.md](architecture-decision.md).

Build a working vertical slice first: ingest a small paper collection, persist and index its text, retrieve relevant chunks, and answer a question with source links. Add scheduling, observability, and agent behavior once that slice works. The phases below are dependency ordered milestones, not calendar estimates.

## What was inspected

The scan covered the upstream tracked file inventory, dependency manifest, Compose configuration, API route registration, retrieval query builder and index mappings, indexing orchestration, chunker, agent graph/configuration, ingestion DAG, and test inventory. Local ingestion, document models, chunk strategies, existing tests, dependency files, and architecture documents were also reviewed. Neither application was started, and upstream test success has not been verified.

Key upstream implementation references, pinned to the scanned commit:

- [Dependencies](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/pyproject.toml): Python `>=3.12,<3.13`, FastAPI, SQLAlchemy, Docling, OpenSearch, Gradio, Redis, Langfuse, LangGraph, and Telegram support.
- [Infrastructure](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/compose.yml): API, PostgreSQL 16, OpenSearch 2.19 and Dashboards, Airflow, Ollama, Redis, plus Langfuse's PostgreSQL, Redis, ClickHouse, and MinIO dependencies. Gradio and Telegram code exist separately from these Compose services.
- [Ingestion DAG](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/airflow/dags/arxiv_paper_ingestion.py): setup → fetch/store → hybrid index → report → cleanup; weekday schedule at 06:00 UTC, retries, and one active run.
- [Indexer](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/src/services/indexing/hybrid_indexer.py): section-aware paper chunking, batched passage embeddings, metadata denormalization, bulk indexing, and reindex support.
- [Index mapping](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/src/services/opensearch/index_config_hybrid.py): text and metadata fields with 1,024-dimensional Jina v3 vectors.
- [API registration](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/src/main.py) and [routers](https://github.com/jamwithai/production-agentic-rag-course/tree/424a0eb99edf841994f2a9a053912b489d2a94ff/src/routers): health, hybrid search, regular/streaming answers, agentic answers, and feedback.
- [Agent graph](https://github.com/jamwithai/production-agentic-rag-course/blob/424a0eb99edf841994f2a9a053912b489d2a94ff/src/services/agents/agentic_rag.py): scope guardrail → retrieval tool → relevance grading → answer or query rewrite/retry. Defaults include two retrieval attempts, top-k three, and `llama3.2:1b`.
- [Tests](https://github.com/jamwithai/production-agentic-rag-course/tree/424a0eb99edf841994f2a9a053912b489d2a94ff/tests): unit, API, integration, and agent tests are present; use their coverage areas as a reference.

## Current local state and gaps

Reusable foundations:

- `src/ingestion/arxiv.py`: arXiv search, pagination, metadata parsing, and download orchestration.
- `src/ingestion/metadata.py` and `pdf.py`: JSON/CSV metadata persistence and PDF downloading. Downloading is distinct from extracting PDF content.
- `src/processing/`: `Document`, `DocumentChunk`, preprocessing, a strategy manager, and fixed, recursive, sentence, and semantic chunkers.
- `notebooks/`: setup, arXiv exploration, and chunking experiments.
- `src/test/test_arxiv_downloader.py`: two mocked downloader checks.

Existing scaffolds include `src/main.py`, `src/config.py`, database session/factory/adapter modules, and `.env.example`; these still need integration and validation. Missing foundations include project metadata in the empty `pyproject.toml`, services in the empty `compose.yml`, paper models/repositories and migrations, PDF extraction, active API routes, search/indexing services, generation, orchestration, monitoring, and chat interfaces. `src/processing/pipeline.py` is also empty. Existing requirements pin older FastAPI/Pydantic versions than upstream; resolve one coherent dependency set rather than mixing the files.

Issues to address before extending chunking:

- Local fixed-size chunking measures characters; upstream's baseline targets 600 words with 100 words overlap and a 100-word minimum. Do not copy numeric settings between those units.
- The semantic chunker defaults to constant dummy embeddings, and its single-sentence branch calls `_create_chunk` without the required `start_idx` argument. Treat this strategy as experimental until repaired and supplied with a real embedding function.
- Sentence overlap zero currently uses `[-0:]`, retaining all previous sentences. Recursive/sentence offset calculations also need validation against actual source spans.
- Chunk IDs must be globally stable at the indexing boundary; the fixed strategy's per-document integer IDs are insufficient as standalone search document IDs.
- `docs/flow.md` references a sample metadata JSON file absent from the tracked inventory. Add a small fixture and align the notebook/documentation paths.

The working tree contains the move from `rag_curator/` to `src/` and additional scaffolding. Preserve these changes when implementing this plan. Imports and test patch targets still referring to `rag_curator` must be migrated to `src`.

## Proposed package boundaries

Keep ingestion and processing independent of infrastructure. Extend the current `src` package incrementally; retain the existing application entry point, database adapters, and configuration schemas.

```text
src/                        # application package (imports use src.*)
  __init__.py
  main.py                   # existing FastAPI entry point and lifespan
  config.py                 # existing typed settings and feature flags
  dependencies.py           # API dependency providers
  database.py               # database instance/session access
  exceptions.py             # shared application exceptions
  middlewares.py            # request logging and error middleware
  ingestion/                # existing arXiv/downloader + PDF parser adapter
  processing/               # existing models/strategies + pipeline.py orchestration
  db/
    factory.py              # existing database construction
    interfaces/             # existing base and PostgreSQL adapters
    models/                 # planned SQLAlchemy paper/processing models
    repositories/           # planned persistence operations and upserts
  schemas/
    database/               # existing database configuration schema
    api/                    # planned request/response schemas
  routers/                  # planned health, search, answer, agent, feedback routes
  retrieval/                # planned OpenSearch mappings, indexing, queries
  embeddings/               # planned passage/query embedding client
  generation/               # planned Ollama client, prompts, context assembly
  agents/                   # planned LangGraph state, tools, bounded workflow
  observability/            # planned optional tracing and cache adapters
  interfaces/               # planned Gradio and Telegram entry points
  test/                     # current downloader tests; move into tests/unit/
tests/                      # planned test layout outside application package
  unit/
  api/
  integration/
  fixtures/                 # deterministic metadata/text/parser fixtures
airflow/dags/               # planned thin scheduling wrappers around src services
migrations/                 # planned versioned database schema
notebooks/                  # existing setup and exploration notebooks
docs/                       # architecture, flow, and replication plan
pyproject.toml              # project metadata and dependency source of truth
uv.lock                     # planned reproducible dependency lockfile
Dockerfile                  # planned application image
compose.yml                 # existing empty file; populate core services
.env.example                # existing configuration template; align with settings
```

This is the target local layout, combining existing files with planned additions. Keep API wiring in `src/main.py`, `src/dependencies.py`, `src/routers/`, and `src/schemas/api/`. Update legacy `rag_curator.*` imports, notebook references, documentation links, and mocked patch targets to `src.*`. Move the existing downloader checks from `src/test/` into `tests/unit/` when establishing test discovery; remove the old test directory only after migration is verified.

## Phase 0 — Reproducible baseline

- [ ] Complete the `src` package migration: update legacy imports, notebook/documentation paths, and test patch targets; move `src/test/` to `tests/unit/` and configure test discovery.
- [ ] Populate `pyproject.toml` for Python 3.12 and choose uv with a committed lockfile. Consolidate `requirements.txt` or generate it from the chosen source of truth.
- [ ] Add separate runtime, development, and optional interface/observability dependency groups. Resolve compatible LangGraph/LangChain versions before adopting upstream graph APIs.
- [ ] Document configuration in `.env.example`: database/search URLs, arXiv limits, embedding model/dimension and API key, Ollama endpoint/model, and optional Langfuse/Telegram credentials. Distinguish container hostnames from host URLs.
- [ ] Repair the chunking issues above, define size/overlap units per strategy, and validate IDs, source metadata, and cleaned-text offsets.
- [ ] Add a small deterministic metadata/text fixture and offline checks for chunk coverage, zero overlap, single sentences, and provenance. Retain the existing downloader checks.

Acceptance: a clean checkout installs with one command; offline tests pass; every baseline chunk has stable paper identity and provenance. Start with fixed or recursive chunking; semantic chunking is optional.

## Phase 1 — API, persistence, and core infrastructure

- [ ] Complete existing typed settings and FastAPI lifespan/dependencies; add routers under `src/routers/`, request/response schemas under `src/schemas/api/`, structured errors, and `GET /api/v1/health` with explicit dependency status.
- [ ] Add SQLAlchemy models and Alembic migrations for papers, arXiv ID/version, authors/categories, dates, PDF location, parsed text/sections, processing status, and failure details.
- [ ] Add repository upserts with unique paper/version identity; keep JSON export as an interchange/debug feature.
- [ ] Add Dockerfile, core Compose services for API/PostgreSQL/OpenSearch, persistent volumes, readiness checks, and repeatable setup commands. Enable Redis/Ollama as subsequent phases need them.

Acceptance: the API starts against healthy dependencies, migrations work on an empty database, and restarting services preserves a saved paper.

## Phase 2 — Complete and restartable ingestion

- [ ] Connect existing arXiv metadata fetching and PDF downloads to the database repository, with explicit date/category limits, request timeouts, retries/backoff, and rate limiting.
- [ ] Add a Docling parser adapter returning text and optional section/page metadata. Cache parsed output by paper version and parser version.
- [ ] Implement `src/processing/pipeline.py`: paper → parse → preprocess → chunk → attach provenance. Preserve abstracts as a clearly labeled fallback when full text is unavailable.
- [ ] Record stage status and make failed papers independently retryable. Avoid silently treating partial fetches as completed runs.
- [ ] Add a bounded CLI command to ingest a small fixture-backed batch before scheduling it.

Acceptance: ingest 10–20 papers; a second run adds no duplicate paper records; a failed PDF leaves usable metadata and an explicit retryable status. Offline fixtures cover malformed metadata and parse/download failures.

## Phase 3 — BM25 retrieval baseline

- [ ] Add an OpenSearch client, explicit text/keyword/date mappings, bulk indexing, and deterministic IDs based on paper version, chunker version, and chunk index.
- [ ] Map `DocumentChunk` into search records with title, abstract, text, category, authors, publication date, source URL, section, and offsets.
- [ ] Add `POST /api/v1/hybrid-search/` with BM25 mode first, bounded pagination/top-k, category filters, and useful hit provenance.
- [ ] Handle partial bulk failures; replace obsolete chunks on paper updates. Keep PostgreSQL authoritative so the index can be rebuilt.
- [ ] Build 20–30 representative evaluation queries with expected relevant papers/chunks; record Recall@k, ranking quality, and latency as a baseline.

Acceptance: known fixture queries retrieve the expected papers, filters behave correctly, and reindexing does not multiply chunks. Record measured results rather than inventing a quality threshold.

## Phase 4 — Embeddings and hybrid retrieval

- [ ] Implement Jina v3 query/passage embedding methods with batching, API timeout/retry handling, and vector count/dimension validation. Match the upstream 1,024-dimensional mapping for initial parity.
- [ ] Add k-NN mapping and the reference's hybrid search behavior. Inspect and document its score combination before tuning; do not assume a particular fusion algorithm from the README.
- [ ] Version indexes and use aliases for schema/model changes; changing embedding dimension requires a new index and re-embedding.
- [ ] Preserve an explicit BM25 fallback when query embedding fails, and expose which mode actually ran.
- [ ] Compare BM25, vector, and hybrid retrieval over the same evaluation set. Record the tradeoff before changing chunk size or adding reranking.

Acceptance: batch/vector validation passes, hybrid search returns attributed hits, embedding outages exercise the lexical fallback, and evaluation results can be reproduced. Reranking is a later experiment, not required parity.

## Phase 5 — Grounded answers and streaming UI

- [ ] Add Ollama generation with explicit model preparation; start with upstream's `llama3.2:1b`, then measure answer quality before choosing a larger model.
- [ ] Add context selection/deduplication, a token budget, and a source-grounded prompt. Return paper titles, arXiv links, and chunk identity with answers.
- [ ] Implement regular and streaming `/api/v1` answer routes using the upstream route/schema definitions as the contract reference.
- [ ] Handle empty retrieval, generation timeouts, stream cancellation, and terminal stream errors. Return an evidence-insufficient response when appropriate.
- [ ] Add a Gradio client using the API, with streamed output and visible sources.

Acceptance: a user can ask a question over the ingested collection and receive a cited answer in the UI; empty evidence and interrupted streams have predictable behavior. This completes the first usable product slice.

## Phase 6 — Scheduling, cache, and tracing

- [ ] Wrap ingestion/indexing services in an Airflow DAG with bounded batches, retries, reports, and no catchup by default. Use the upstream weekday 06:00 UTC schedule as an explicit starting configuration.
- [ ] Pass paper IDs/status summaries between tasks rather than PDFs or large parsed documents. Scope cleanup to this project's temporary directory.
- [ ] Add Redis caching with configurable TTL; upstream's config defaults to six hours. Include query, filters, model, prompt/retrieval settings, and corpus/index version in keys.
- [ ] Add optional Langfuse spans for embedding, retrieval, generation, and agent execution plus feedback correlation. Keep cache/tracing outages from breaking otherwise valid answers.
- [ ] Add optional Compose profiles for Airflow, Dashboards, and the full Langfuse stack; document resource requirements after measuring locally.

Acceptance: rerunning an ingestion task is safe; repeated identical requests hit cache; a corpus change invalidates stale answers; a complete request trace is visible; cache/tracing failures degrade cleanly.

## Phase 7 — Bounded agentic RAG and Telegram

- [ ] Implement LangGraph state/context and the reference graph: scope check → retrieval tool → document grading → generate, or rewrite → retrieve again; out-of-scope queries terminate early.
- [ ] Start with two retrieval attempts and top-k three for parity. Enforce attempt, graph recursion, timeout, and context limits independently of model decisions.
- [ ] Keep original and rewritten queries, retained sources, and execution events available for debugging. Define a clear no-evidence outcome after attempts are exhausted.
- [ ] Add `POST /api/v1/ask-agentic` and feedback support, then expose agent mode in Gradio.
- [ ] Add an optional Telegram bot using the same service/API; handle message length, concurrent users, token configuration, and shutdown.

Acceptance: deterministic tests exercise scope rejection, relevant-first-retrieval, rewrite success, exhausted attempts, and upstream service failure. An optional Telegram smoke test answers a question and includes source links.

## Verification and completion

Use offline unit tests for processing, query/schema construction, retry routing, and cache keys; API tests with fake clients for request validation and streaming behavior; and Docker-backed integration tests for persistence, real index queries, and reindex consistency. Keep live arXiv/Jina/Ollama checks separate from the default test suite.

The replication is complete when a fresh checkout can start the documented services, ingest a bounded collection twice without duplication, retrieve with BM25 and hybrid modes, produce sourced regular/streaming answers, execute the bounded agent, and demonstrate scheduling, cache invalidation, tracing, and optional Telegram access. Capture retrieval metrics and answer/citation review results. No numerical quality or latency claim is established by this scan.

## Deliberate adaptations and operational notes

- Reuse local document abstractions and strategy selection; add an index adapter rather than replacing the processing package with upstream schemas.
- Upstream Compose maps Langfuse to host port **3001**, although the README lists 3000. Derive the local runbook from actual configuration. Gradio and Telegram need explicit launch instructions or optional services.
- Upstream Compose includes development credentials and disabled OpenSearch security. Keep the initial reproduction local; require authentication, secret management, and appropriate network exposure before deployment.
- Add schema migrations and index versioning as explicit local requirements even where upstream bootstraps state in application startup.
- Avoid copying upstream cleanup commands that scan all of `/tmp`, or reset commands that remove persistent volumes.
- Pin dependency/image versions after a successful installation and smoke run; the upstream manifest has broad lower bounds and does not by itself guarantee compatibility with newly resolved releases.
- Preserve upstream MIT copyright/license notices if copying implementation. Deployment, provisioning paid services, and copying entire upstream modules are outside this planning change.

## First implementation batch

Start with Phase 0 as a small change: complete the `src` package and test migration, project/dependency configuration, fixture data, chunking correctness fixes, and focused offline tests. Follow with API/database/Compose foundations, then deliver the ingestion → BM25 → cited answer slice before enabling the optional stack.
