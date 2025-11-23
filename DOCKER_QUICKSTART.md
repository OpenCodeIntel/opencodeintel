# Docker Quick Start Guide

Get CodeIntel running locally with Docker in 5 minutes.

## Prerequisites

✅ Docker Desktop installed and running  
✅ Git installed  
✅ Terminal/Command Line access

## Step 1: Clone & Navigate

```bash
git clone https://github.com/DevanshuNEU/v1--codeintel.git
cd v1--codeintel
```

## Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Required variables in `.env`:**
```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=codeintel
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...
API_KEY=your-secret-key-here
```

## Step 3: Start Services

```bash
# Build and start all services
docker compose up -d

# Watch logs
docker compose logs -f
```

**Services will start on:**
- 🎨 **Frontend:** http://localhost:3000
- 🚀 **Backend API:** http://localhost:8000
- 📖 **API Docs:** http://localhost:8000/docs
- 🗄️ **Redis:** localhost:6379

## Step 4: Verify Everything Works

```bash
# Run verification script
chmod +x scripts/verify-setup.sh
./scripts/verify-setup.sh

# Or test manually:
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-11-22T22:45:00"
}
```

## Step 5: Use CodeIntel

1. **Open Frontend:** http://localhost:3000
2. **Add a Repository:**
   - Enter GitHub URL
   - Watch it clone and index
3. **Search Code:**
   - Use semantic search to find implementations
   - Get instant results from vector search

## Common Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a service
docker compose restart backend

# Stop everything
docker compose down

# Stop and remove all data
docker compose down -v

# Rebuild after code changes
docker compose up -d --build backend
```

## Troubleshooting

**Issue:** Docker daemon not running  
**Fix:** Open Docker Desktop and wait for it to start

**Issue:** Port 8000 already in use  
**Fix:** 
```bash
# Find what's using it
lsof -i :8000
# Kill it or change port in docker-compose.yml
```

**Issue:** Environment variables not found  
**Fix:** Make sure `.env` exists in project root (not just backend/)

**Full troubleshooting guide:** See `DOCKER_TROUBLESHOOTING.md`

## Development Mode

For hot reload during development:

```bash
# Use dev compose file
docker compose -f docker-compose.dev.yml up

# Backend will auto-reload on file changes
```

## Next Steps

- 📖 Read full deployment guide: `DEPLOYMENT.md`
- 🚀 Deploy to Railway: `./scripts/deploy-railway.sh`
- 🌐 Deploy to Vercel: `./scripts/deploy-vercel.sh`
- 🧪 Run tests: See `backend/README.md`

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Frontend   │─────▶│   Backend   │─────▶│    Redis    │
│  (Vite/React)│      │  (FastAPI)  │      │   (Cache)   │
│  Port 3000  │      │  Port 8000  │      │  Port 6379  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Supabase   │
                     │  (Postgres) │
                     └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Pinecone   │
                     │  (Vectors)  │
                     └─────────────┘
```

## Resource Requirements

**Minimum:**
- 4GB RAM
- 2 CPU cores
- 10GB disk space

**Recommended:**
- 8GB RAM
- 4 CPU cores
- 20GB disk space

Set in Docker Desktop → Settings → Resources

## Production Deployment

Once local dev works, deploy to production:

1. **Backend → Railway:**
   ```bash
   ./scripts/deploy-railway.sh
   ```

2. **Frontend → Vercel:**
   ```bash
   ./scripts/deploy-vercel.sh
   ```

Full deployment guide: `DEPLOYMENT.md`

---

**Need help?** 
- 📖 Check `DOCKER_TROUBLESHOOTING.md`
- 🐛 Open an issue: https://github.com/DevanshuNEU/v1--codeintel/issues
- 📝 See full docs: `README.md`
