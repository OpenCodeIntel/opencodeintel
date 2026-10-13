# OpenCodeIntel: Project Report

**Course:** Generative AI  
**Project:** AI-Powered Code Intelligence System  
**Author:** Devanshu Chicholikar  
**Institution:** Northeastern University  
**Report date (snapshot):** April 2026  
**Live System:** https://opencodeintel.com  
**Repository:** https://github.com/OpenCodeIntel/opencodeintel  

---

## 1. Project Overview

OpenCodeIntel (OCI) is an open-source, production-grade generative AI system that solves a real problem: AI coding assistants like Claude Code, Cursor, and Copilot do not know your codebase. They hallucinate function names, use wrong patterns, and put code in wrong files because they lack context.

OCI builds a persistent, semantic knowledge base from your codebase and delivers exactly the right context (the relevant files, functions, and project rules) to any AI assistant the moment it needs them, via the Model Context Protocol (MCP).

This is the open-source alternative to Augment Code, which raised $252M to solve the same problem for enterprise teams. OCI solves it for every developer, free and self-hostable.

**Generative AI components implemented:**
- Retrieval-Augmented Generation (RAG): primary component
- Prompt Engineering: per-task context assembly with systematic rule injection

---

## 2. System Architecture

See [`docs/architecture.md`](./architecture.md) for full diagrams.

The system has four layers:

**Layer 1: Indexing (RAG Knowledge Base Construction)**  
Repositories are parsed with tree-sitter at the function level. Each function is embedded using OpenAI `text-embedding-3-small` and stored in Pinecone (vector database). Import relationships are extracted into a dependency graph stored in Supabase.

**Layer 2: Retrieval (RAG Query Pipeline)**  
Given a natural language task description, the system expands the query into semantic variants, runs cosine similarity search against Pinecone, expands results by one hop through the dependency graph, and matches project rules from `CLAUDE.md` / `AGENTS.md` / `.cursorrules`.

**Layer 3: Context Assembly (Prompt Engineering)**  
Retrieved chunks are ranked by relevance score and packed into a token budget (default 1,500 tokens). Matched rules are injected. The result is a structured markdown context package delivered to the AI assistant.

**Layer 4: MCP Protocol**  
An MCP server exposes all capabilities as tools consumable by any MCP-compatible AI client (Claude Code, Cursor, Copilot, Gemini CLI) via stdio or streamable HTTP.

### Architecture Diagram

```text
Repository → tree-sitter parsing → OpenAI embeddings → Pinecone
                                 ↘ import graph     → Supabase

Query → expansion → Pinecone search → dep expansion → rule matching
     → token-budget packing → context package → MCP → AI assistant
```

*Full detailed diagrams with all component interactions: [`docs/architecture.md`](./architecture.md)*

![System Architecture](https://github.com/user-attachments/assets/5c4f5846-184f-46ec-b4c4-a444cbb6540d)

---

## 3. Generative AI Components

### 3.1 Retrieval-Augmented Generation (RAG)

RAG is the architectural foundation of OpenCodeIntel.

**Knowledge Base Construction**

The knowledge base is built by parsing source code at function granularity using tree-sitter (an incremental parsing library that produces ASTs for Python, JavaScript, TypeScript, and TSX). Each parsed function is converted into rich embedding text:

```text
File: backend/middleware/auth.py
Function: _validate_jwt
Parameters: token: str
Returns: Optional[AuthContext]
Docstring: Validates a JWT token and returns AuthContext or None.
Body: [function source code]
```

This rich format (as opposed to raw code) significantly improves semantic retrieval because the embedding model can understand intent, not just syntax.

Embeddings are generated using OpenAI `text-embedding-3-small` (1536 dimensions) or `text-embedding-3-large` (3072 dimensions) in batches of 100, with 10 files processed in parallel for throughput. Vectors are upserted to Pinecone (Serverless, AWS us-east-1, cosine similarity metric) in batches of 100.

**Chunking Strategy**

The chunking unit is the function (extracted by tree-sitter AST), not a fixed character window. This is a deliberate design choice: code meaning is function-scoped. Fixed-window chunking (e.g., 512 tokens) splits functions at arbitrary points, degrading retrieval precision. Function-level chunking ensures each vector represents a complete, semantically coherent unit.

**Retrieval Pipeline**

Retrieval uses query expansion: the user's task description is sent to GPT-4o-mini, which generates 3 semantic variants. All 4 queries (original + 3 variants) are embedded and run against Pinecone. Results are deduplicated and re-ranked by combined cosine similarity score, with a keyword-boost for exact token matches.

The top results are expanded by one hop through the dependency graph: if `auth.py` is returned, files that import `auth.py` and files that `auth.py` imports are added to the candidate set. This ensures the AI gets the full picture, not just the most similar file in isolation.

**Vector Database**

Pinecone Serverless was chosen for:
- Managed queries with no database servers to run
- Native metadata filtering (filter by `repo_id` for multi-tenant isolation)
- Serverless pricing (no idle costs)
- Cosine similarity, which outperforms dot product for normalized embedding vectors

Each vector stores metadata: `file_path`, `function_name`, `repo_id`, `chunk_type`, `language`.

### 3.2 Prompt Engineering

**Per-Task Context Assembly**

The `get_context_for_task` tool is the primary prompt engineering component. It solves a specific problem: even with the right files retrieved, an AI assistant still needs to know the project's conventions (what exception class to use, what auth pattern to follow, where to put new files). Without this, the AI generates correct-looking but wrong code.

The context assembler reads rule files in priority order:
```text
CLAUDE.md → AGENTS.md → .cursorrules → .codeintel/rules.md
→ CONVENTIONS.md → .github/copilot-instructions.md
→ CODING_GUIDELINES.md
```

Rules files are split by `##` markdown headers into discrete sections. Each section is matched against the user's task using regex patterns and keyword overlap scoring. Only relevant rule sections are included (not the entire file) to stay within the token budget.

**Token Budget Management**

Context is packed greedily within a configurable token budget (default: 1,500 tokens, estimated at 1 token per 4 characters). Files are ordered by relevance score. The assembler stops adding files when the budget would be exceeded. This constraint forces precision: the system returns exactly what's needed, not everything it finds.

**System Prompt Design for DNA Extraction**

The `get_codebase_dna` tool uses tree-sitter to statically analyze the codebase and extract architectural patterns (auth patterns, service patterns, DB patterns, error patterns, naming conventions) without calling an LLM. This deterministic extraction produces machine-readable rules that serve as grounding context for AI code generation, reducing hallucination of project-specific names and patterns.

---

## 4. Implementation Details

### 4.1 Backend (FastAPI, Python 3.11+)

**Key services:**

| Service | Responsibility |
|---|---|
| `indexer_optimized.py` | Code parsing, embedding, Pinecone upsert |
| `context_assembler.py` | Per-task context retrieval and assembly |
| `dependency_analyzer.py` | Import graph extraction (tree-sitter AST) |
| `dna_extractor.py` | Architectural pattern extraction |
| `search_enhancer.py` | Query expansion (GPT-4o-mini) |
| `search_v2/` | Function-level extraction (tree-sitter) |
| `middleware/auth.py` | JWT + API key authentication |

All services use the singleton pattern (instantiated once in `dependencies.py`, injected via FastAPI `Depends()`). This is critical for Pinecone connection reuse; creating a new connection per request would add ~800ms of latency.

**Multi-tenancy:** Every Pinecone query filters by `repo_id` (UUID). Supabase Row-Level Security (RLS) enforces that users can only access their own repositories at the database level, independent of application logic.

**API design:** All endpoints follow `/api/v1/{resource}` prefix. Auth is dual-mode: JWT (for browser sessions) with API key fallback (for MCP clients). API keys are stored as SHA-256 hashes in the database; the raw key is shown to the user once and never stored.

### 4.2 MCP Server (FastMCP, Python)

The MCP server is a thin protocol adapter. It handles MCP JSON-RPC messages, authenticates the `MCP_API_KEY`, and proxies tool calls to the backend REST API. Dual transport (stdio + streamable HTTP) means the same server works for local development (Claude Code, Cursor) and hosted deployment (any HTTP-capable MCP client).

Tools exposed: `search_code`, `get_context_for_task`, `get_codebase_dna`, `get_dependency_graph`, `analyze_impact`, `analyze_code_style`, `add_repository`, `index_repository`, `list_repositories`.

### 4.3 Frontend (React 18, TypeScript, Vite)

Dashboard for repository management, API key generation, and indexing status. Built with shadcn/ui components and Tailwind CSS. All server state managed via TanStack Query (`useQuery`/`useMutation`); no raw `fetch` in `useEffect`.

### 4.4 Infrastructure

- **Backend + MCP:** Railway (separate services, shared environment; uses `MCP_API_KEY` to avoid collision with backend's `API_KEY`)
- **Frontend:** Vercel
- **CI/CD:** GitHub Actions with path-filtered jobs (backend tests only run when `backend/**` changes)
- **Domains:** GoDaddy → Vercel/Railway

---

## 5. Performance Metrics

> **Correction (October 2026).** The latency, indexing-throughput and retrieval-quality tables first published in this section were not backed by a recorded benchmark, so they have been removed. The measured numbers below replace them.

### 5.1 Search Latency (production, measured 2026-10-09)

Measured on production (api.opencodeintel.com) on 2026-10-09, through the public playground: 30 unique cache-miss queries, then 15 of them repeated. The playground runs search v3 without the reranker: vector search with keyword and code-graph boosts. The MCP `search_code` path (search v2: vector top 50, BM25 over those 50, RRF, Cohere rerank on the top 20) was not part of this run.

| Search | p50 | p95 | Measured as |
|---|---|---|---|
| Cold (cache miss: embedding, vector search, keyword and code-graph boosts) | 641ms | 1,380ms | server-reported search time |
| Cached repeat | 242ms | 385ms | client wall time from Boston, network included |

n is small (30 cold, 15 cached), so treat p95 as tail-indicative. The script and raw results live outside this repo; rerun the same playground queries to reproduce.

### 5.2 Retrieval Quality

The production regression eval in [`backend/evals`](../backend/evals) uses human-labelled queries whose expected files are chosen by reading the repo, never by looking at what search returns. Its baseline (June 2026, 10 queries on one repository): Recall@10 0.80 without reranking and 0.85 with it; MRR 0.80 without reranking and 0.66 with it. On this set, reranking finds more of the right files but ranks the top hit lower, so it is not a clear win yet.

The research that shaped the retrieval design (December 2025, 14 open-source codebases, 665 queries, 94% average Hit@1 with Voyage `rerank-2` on a research harness) is published with its query sets, raw results and caveats at [OpenCodeIntel/retrieval-research](https://github.com/OpenCodeIntel/retrieval-research). Those numbers come from a different harness and reranker than production, so they are not a production score.

### 5.4 Test Coverage

| Component | Tests | Status |
|---|---|---|
| Backend | 400+ pytest tests (407 test functions, Oct 2026) | Passing |
| MCP Server | 60 pytest tests (Oct 2026) | Passing |
| Frontend | TypeScript build | Passing |

---

## 6. Challenges and Solutions

**Challenge 1: JWT auth blocking API key fallback**  
`_validate_jwt` raised `HTTPException(401)` on invalid tokens, which short-circuited the middleware before it could try the API key path. Fixed by returning `None` instead of raising, allowing the fallback to proceed. (PR #285)

**Challenge 2: Railway shared environment variables**  
Backend and MCP server share environment variables in Railway. Backend's `API_KEY=dev-secret-key` was overriding the MCP server's intended auth key. Fixed by using `MCP_API_KEY` as the distinct variable name for the MCP server. (PR #286)

**Challenge 3: tree-sitter startup crash**  
`import tree_sitter_typescript` failed at startup on Railway if the native binary wasn't compiled for the container architecture. Hard import crashed the entire backend. Fixed with `try/except ModuleNotFoundError` that falls back to a JavaScript parser. (PR #281)

**Challenge 4: include_paths filtering bug**  
String-based `startswith` matching for path filtering matched `src/app` against `src/application`, causing wrong files to be indexed in subset indexing. Fixed by comparing `Path.parts` tuples, which ensures exact path component matching. (PR #280)

**Challenge 5: Empty include_paths silently indexing everything**  
`if include_paths:` evaluates `[]` as falsy, causing the entire repo to be indexed when the intent was to index nothing. Fixed by using `if include_paths is not None:`. (PR #287)

**Challenge 6: Pinecone dimension mismatch**  
Switching embedding models between `text-embedding-3-small` (1536d) and `text-embedding-3-large` (3072d) required recreating the Pinecone index. The system now reads the existing index dimension on startup and validates it matches the configured model, logging a warning if mismatched.

---

## 7. Future Improvements

**Near-term:**
- VS Code extension for zero-config setup
- `codeintel init` CLI command for one-command MCP configuration
- Cursor-native integration docs
- Greptile config (`greptile.json`) for team rules

**Medium-term:**
- Incremental re-indexing (currently full re-index on change)
- Streaming context assembly for large repos
- Branch-aware indexing (index feature branches separately)
- Private LLM support (Ollama, local embeddings via ONNX)

**Long-term:**
- Multi-language expansion (Go, Rust, Java, C++)
- Cross-repo context (monorepo-aware search)
- Code change impact prediction (before-commit analysis)
- GitHub App for automatic indexing on push

---

## 8. Ethical Considerations

**Data Privacy**  
Code is a form of intellectual property. OCI's hosted service stores repository embeddings (vector representations, not raw source code) in Pinecone and metadata in Supabase. API keys are stored as SHA-256 hashes; the raw key is shown once and never persisted. Users retain full ownership of their data and can delete repositories at any time. The self-hosted deployment option (Docker Compose) gives users complete control over data residency.

**Access Control**  
Multi-tenancy is enforced at two layers: application-level (all queries filter by `repo_id` tied to the authenticated user) and database-level (Supabase Row-Level Security). These two independent layers prevent cross-user data leakage even if one layer has a bug.

**Potential Misuse**  
The context assembly feature could theoretically be used to extract sensitive patterns from a codebase (auth logic, secret handling). OCI mitigates this by requiring user authentication for all repository access and by not storing raw source code, only embeddings.

**Bias and Representation**  
The embedding model (OpenAI `text-embedding-3-small`) may perform better on English-language identifiers and comments than on other languages. Codebases with non-English naming conventions may see lower retrieval recall. This is a known limitation.

**Copyright**  
OCI does not reproduce or redistribute source code. It stores vector embeddings (real-valued floating point arrays) which significantly reduces the risk of reconstructing original source code. Retrieval returns file paths and function signatures to help the AI locate relevant code, not the code itself verbatim (unless the user has authorized access to that repo).

**Content Filtering**  
The system does not filter for malicious code patterns. It indexes whatever the user points it at. Users are responsible for ensuring they have authorization to index the repositories they connect.

---

## 9. References

- Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
- Anthropic. (2024). Model Context Protocol Specification. https://modelcontextprotocol.io
- Pinecone. (2024). Serverless Vector Database. https://pinecone.io
- OpenAI. (2024). text-embedding-3-small model card. https://platform.openai.com
- tree-sitter. (2024). Incremental parsing library. https://tree-sitter.github.io
- ETH Zurich. (2024). REPOCONTENTS: Can Long Context LLMs Handle Entire Codebases?

---

## Appendix: Repository Structure

```text
opencodeintel/
├── backend/                  FastAPI backend (Python 3.11+)
│   ├── services/
│   │   ├── indexer_optimized.py    RAG indexing pipeline
│   │   ├── context_assembler.py    Per-task context assembly
│   │   ├── dependency_analyzer.py  Import graph (tree-sitter)
│   │   ├── dna_extractor.py        Architectural pattern extraction
│   │   ├── search_enhancer.py      Query expansion
│   │   └── search_v2/              Function-level extraction
│   ├── middleware/
│   │   └── auth.py                 JWT + API key auth
│   ├── routes/                     API endpoints (/api/v1/*)
│   └── tests/                      400+ pytest tests
├── mcp-server/               MCP protocol server (FastMCP)
│   ├── server.py                   FastMCP app, dual transport
│   ├── tools.py                    Tool schema definitions
│   ├── handlers.py                 Tool execution logic
│   └── tests/                      45+ pytest tests
├── frontend/                 React 18 dashboard (TypeScript, Bun)
│   └── src/
├── supabase/                 Database migrations
├── docs/
│   ├── architecture.md             System architecture diagrams
│   ├── examples/README.md          Example outputs
│   ├── project-report.md           This document
│   ├── mcp-setup.md                MCP setup guide
│   └── docker-quickstart.md        Self-host guide
└── docker-compose.yml        Full stack local setup
```
