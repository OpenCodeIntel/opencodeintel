# CodeIntel MCP

**MCP server for AI-powered codebase intelligence.** Semantic search, dependency analysis, and impact prediction for your repositories.

## The Problem

AI coding assistants are powerful, but they're flying blind in large codebases:
- Can't semantically search across thousands of files
- Don't understand dependency relationships
- Can't predict what breaks when you change a file
- Have no context on team coding patterns

## The Solution

CodeIntel is an MCP (Model Context Protocol) server that gives AI agents deep codebase understanding:

```typescript
// Ask Claude (via MCP):
"Find authentication middleware in this repo"

// CodeIntel semantically searches 10,000+ functions
// Returns exact implementations, not keyword matches
```

**Built for production. Not a demo.**

## Key Features

### 🔍 Semantic Code Search
Search by meaning, not keywords. Find `"error handling logic"` even if functions are named `processFailure()`.

### 📊 Dependency Analysis  
Visualize your entire codebase architecture. See which files are critical, which are isolated, and how everything connects.

### ⚡ Impact Prediction
Before changing a file, know exactly what breaks:
```
src/auth/middleware.py
└─ 15 files affected (HIGH RISK)
   ├─ src/api/routes.py
   ├─ src/services/user.py
   └─ ... + 12 more
```

### 🎨 Code Style Analysis
Understand team patterns: naming conventions (camelCase vs snake_case), async adoption %, type hint usage.

### 🚀 Performance That Scales

**Batch Processing:** 100x faster indexing
- Before: 40+ min for 1,000 functions (individual API calls)
- After: 22.9 sec (batch embedding requests)

**Incremental Indexing:** 700x faster re-indexing  
- Full re-index: 51.4s
- Incremental (git diff): 0.07s
- Perfect for active development

**Supabase Caching:** 5x search speedup
- Cold search: 800ms
- Cached: 150ms

## Quick Start

### 🐳 Docker (Recommended)

**Fastest way to get started:**

```bash
# 1. Clone repo
git clone https://github.com/DevanshuNEU/v1--codeintel.git
cd v1--codeintel

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start everything
docker compose up -d

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Docs: http://localhost:8000/docs
```

**Full guide:** [`DOCKER_QUICKSTART.md`](./DOCKER_QUICKSTART.md)  
**Troubleshooting:** [`DOCKER_TROUBLESHOOTING.md`](./DOCKER_TROUBLESHOOTING.md)

---

### 📦 Manual Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- OpenAI API key
- Pinecone account
- Supabase project

### 1. Clone & Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Add your API keys to .env
```

### 2. Run Backend

```bash
python main.py
# Server runs on http://localhost:8000
```

### 3. Setup Frontend

```bash
cd frontend
npm install
npm run dev
# UI at http://localhost:5173
```

### 4. Add a Repository

```bash
# Via API
curl -X POST http://localhost:8000/api/repos \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "zustand", "git_url": "https://github.com/pmndrs/zustand"}'

# Or use the web UI
```

## MCP Integration

CodeIntel works as an MCP server with Claude Desktop:

```json
// Add to Claude Desktop config (~/.config/claude/config.json)
{
  "mcpServers": {
    "codeintel": {
      "command": "python",
      "args": ["/path/to/pebble/mcp-server/server.py"]
    }
  }
}
```

**Available MCP Tools:**
- `search_code` - Semantic code search
- `list_repositories` - View indexed repos
- `get_dependency_graph` - Analyze architecture
- `analyze_code_style` - Team patterns
- `analyze_impact` - Change impact prediction  
- `get_repository_insights` - Comprehensive metrics

Now ask Claude: *"What's the authentication logic in the user service?"* and it searches your actual codebase.

## Architecture

```
┌─────────────┐
│   Frontend  │  React + TypeScript + Tailwind
│  (Vite app) │  Dependency graphs, search UI
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │  Python backend
│   Backend   │  /api/search, /api/repos/{id}/dependencies
└──────┬──────┘
       │
       ├─────► Pinecone (vector search)
       ├─────► OpenAI (embeddings)
       ├─────► Supabase (persistence)
       └─────► Redis (caching)
```

**Tech Stack:**
- **Backend:** FastAPI, tree-sitter (AST parsing), OpenAI embeddings
- **Vector DB:** Pinecone for semantic search
- **Database:** Supabase (PostgreSQL) for metadata + caching
- **Cache:** Redis for 5x search speedup
- **Frontend:** React, TypeScript, Tailwind CSS, shadcn/ui, ReactFlow

## Performance Benchmarks

Real numbers from indexing the Zustand repository (1,174 functions):

| Metric | Value |
|--------|-------|
| Full indexing | 29.5s (39.7 functions/sec) |
| Incremental re-index | 0.07s (700x faster) |
| Batch embedding | 22.9s for 1,174 functions |
| Search (cold) | 800ms |
| Search (cached) | 150ms |

## Use Cases

**For AI Agents (via MCP):**
- Semantic code search during pair programming
- Understanding unfamiliar codebases
- Finding implementation patterns
- Impact analysis before refactoring

**For Development Teams:**
- Onboarding new engineers (visualize architecture)
- Code review prep (see change blast radius)
- Tech debt identification (find highly coupled files)
- Pattern enforcement (analyze style consistency)

## What Makes This Different

**Most code search tools:** Keyword matching (grep, GitHub search)  
**CodeIntel:** Understands *meaning* - finds `error handling` even if the function is called `processFailure()`

**Most dependency tools:** Static analysis only  
**CodeIntel:** Combines AST parsing + semantic understanding + impact prediction

**Most demos:** In-memory, doesn't scale  
**CodeIntel:** Production-grade with Supabase persistence, Redis caching, incremental indexing

## Deployment

### 🐳 Local Development (Docker)
```bash
# Start all services
make dev

# Or using docker compose
docker compose -f docker-compose.dev.yml up -d

# Services available at:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
# - API Docs: http://localhost:8000/docs
```

### ☁️ Production Deployment

**Backend + Redis → Railway**
```bash
# Automated deployment
./scripts/deploy-railway.sh

# Or manually:
railway login
railway init
railway up
```

**Frontend → Vercel**
```bash
# Automated deployment
./scripts/deploy-vercel.sh

# Or manually:
cd frontend
vercel --prod
```

**📚 Full deployment guide:** See [DEPLOYMENT.md](DEPLOYMENT.md) for complete instructions, environment variables, and troubleshooting.

## Contributing

Built in a focused 2-week sprint to demonstrate production-grade AI development tooling.

Contributions welcome! Areas for improvement:
- Support for more languages (currently: Python, JS/TS)
- Advanced graph algorithms (find circular dependencies, suggest refactorings)
- GitHub integration (PR impact analysis)
- Team analytics (who writes what patterns)

## License

MIT License - use it, fork it, build on it.

## Built With

Commitment to shipping production-grade AI tools. Not a side project. Not a demo. Real infrastructure that scales.

---

**Questions?** Open an issue or reach out.
