<p align="center">
  <!-- Logo placeholder - replace with actual logo -->
  <h1 align="center">OpenCodeIntel</h1>
</p>

<p align="center">
  <strong>Finally understand your codebase</strong>
</p>

<p align="center">
  <a href="https://github.com/OpenCodeIntel/opencodeintel/actions/workflows/ci.yml">
    <img src="https://github.com/OpenCodeIntel/opencodeintel/actions/workflows/ci.yml/badge.svg" alt="CI Status" />
  </a>
  <a href="https://github.com/OpenCodeIntel/opencodeintel/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/OpenCodeIntel/opencodeintel" alt="License" />
  </a>
  <a href="https://github.com/OpenCodeIntel/opencodeintel/releases">
    <img src="https://img.shields.io/github/v/release/OpenCodeIntel/opencodeintel?include_prereleases" alt="Release" />
  </a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="./docs/deployment.md">Docs</a> •
  <a href="./CONTRIBUTING.md">Contributing</a>
</p>

---

You know that mass of code you inherited? The one where you spend 20 minutes grep-ing just to find where authentication happens? Where you're scared to change anything because you don't know what might break?

**OpenCodeIntel fixes that.**

Search your code by what it *does*, not what it's named. Ask for "error handling" and find it—even when the function is called `processFailure()`.

<!-- Demo screenshot placeholder -->
<!-- <p align="center">
  <img src="docs/assets/demo.png" alt="OpenCodeIntel Demo" width="800" />
</p> -->

## See it in action

| You search for... | It finds... |
|-------------------|-------------|
| `"authentication logic"` | `validateJWT()`, `checkSession()`, `authMiddleware.ts` |
| `"where we handle payments"` | `stripe/checkout.ts`, `processRefund()`, `PaymentService` |
| `"error handling"` | `processFailure()`, `onError()`, `catch` blocks across the codebase |

No regex. No exact matches. Just describe what you're looking for.

## What else?

**Dependency Graph** — See how your files connect. One glance shows you the architecture.

**Impact Analysis** — About to change `auth.ts`? Know exactly what breaks before you touch it.

**Code Style** — Understand your team's patterns. snake_case or camelCase? How are errors handled?

**Works with Claude** — Connects as an MCP server. Your AI assistant finally understands your codebase.

## Quick Start

```bash
git clone https://github.com/OpenCodeIntel/opencodeintel.git
cd opencodeintel

cp .env.example .env
# Add your API keys

docker compose up -d
```

Open http://localhost:3000. That's it.

<details>
<summary><strong>Manual setup (without Docker)</strong></summary>

**Requirements:** Python 3.11+, Node.js 20+

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py

# Frontend (new terminal)
cd frontend
npm install && npm run dev
```

</details>

<details>
<summary><strong>Connect to Claude Desktop (MCP)</strong></summary>

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "opencodeintel": {
      "command": "python",
      "args": ["/path/to/opencodeintel/mcp-server/server.py"],
      "env": {
        "BACKEND_API_URL": "http://localhost:8000",
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

See [full MCP setup guide](./docs/mcp-setup.md).

</details>

## Architecture

```
┌─────────────────────────────────────────┐
│           Frontend (React)              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│          Backend (FastAPI)              │
└───────┬─────────┬─────────┬─────────────┘
        │         │         │
   ┌────▼───┐ ┌───▼────┐ ┌──▼───┐
   │Pinecone│ │Supabase│ │Redis │
   │vectors │ │database│ │cache │
   └────────┘ └────────┘ └──────┘
```

## Docs

- [Docker Quickstart](./docs/docker-quickstart.md) — Running in 5 minutes
- [Deployment Guide](./docs/deployment.md) — Production setup
- [MCP Integration](./docs/mcp-setup.md) — Claude Desktop setup
- [Troubleshooting](./docs/docker-troubleshooting.md) — Common fixes

## Contributing

We'd love your help. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE)
