# CodeIntel Deployment Guide

Complete guide for deploying CodeIntel to production and local development.

## 🏠 Local Development with Docker Compose

### Prerequisites
- Docker Desktop installed
- `.env` file configured (copy from `.env.example`)

### Quick Start
```bash
# Clone and navigate to project
cd pebble

# Copy environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your actual API keys

# Build and start all services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop all services
docker compose down
```

### Services Running
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redis**: localhost:6379

### Development Commands
```bash
# Rebuild after code changes
docker compose up -d --build backend

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f redis

# Execute commands in containers
docker compose exec backend python -c "print('Hello')"
docker compose exec redis redis-cli ping

# Stop and remove volumes (clean slate)
docker compose down -v
```

---

## ☁️ Production Deployment

### Railway (Backend + Redis)

#### 1. Initial Setup
1. Sign up at [railway.app](https://railway.app)
2. Install Railway CLI: `npm i -g @railway/cli`
3. Login: `railway login`

#### 2. Create Project
```bash
# Initialize Railway project
railway init

# Link to existing project (if you created one in dashboard)
railway link
```

#### 3. Deploy Backend
```bash
# Deploy from root directory
railway up

# OR use dashboard:
# 1. Connect GitHub repo
# 2. Select "Backend" service
# 3. Set root directory to "./backend"
# 4. Railway auto-detects Dockerfile
```

#### 4. Add Redis
In Railway dashboard:
1. Click "New" → "Database" → "Add Redis"
2. Railway automatically sets `REDIS_URL` environment variable
3. Update backend to use `REDIS_URL` if provided:

```python
# In services/cache.py
import os
redis_url = os.getenv("REDIS_URL")
if redis_url:
    redis_client = redis.from_url(redis_url)
else:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
```

#### 5. Environment Variables (Railway Dashboard)
Set these in Railway dashboard for Backend service:
```
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=codeintel
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...
API_KEY=production-secret-key-change-this
BACKEND_API_URL=https://your-backend.railway.app
```

#### 6. Custom Domain (Optional)
1. Railway Dashboard → Backend Service → Settings
2. Generate domain or add custom domain
3. Update CORS in `backend/main.py` to allow your frontend domain

---

### Vercel (Frontend)

#### 1. Install Vercel CLI
```bash
npm i -g vercel
```

#### 2. Deploy Frontend
```bash
cd frontend

# Deploy to Vercel
vercel

# Production deployment
vercel --prod
```

#### 3. Environment Variables (Vercel Dashboard)
Set in Vercel project settings:
```
VITE_API_URL=https://your-backend.railway.app
```

#### 4. Build Settings (Vercel Dashboard)
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm ci`

---

## 🔧 Configuration Updates

### Backend CORS
Update `backend/main.py` with your frontend URL:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "http://localhost:3000"  # Keep for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Health Check Endpoint
Ensure `/health` endpoint exists (already implemented):
```python
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

---

## 🔍 Monitoring & Debugging

### Railway Logs
```bash
# View logs in terminal
railway logs

# Or use dashboard
# Railway → Backend Service → Deployments → View Logs
```

### Vercel Logs
```bash
# View logs
vercel logs

# Or use dashboard
# Vercel → Project → Deployments → Logs
```

### Redis Monitoring
```bash
# Connect to Railway Redis
railway run redis-cli

# Monitor commands
MONITOR

# Check memory usage
INFO memory

# View all keys
KEYS *
```

---

## 🐛 Common Issues

### Issue: Backend can't connect to Redis
**Solution**: Ensure `REDIS_URL` is set in Railway or Docker:
```bash
# Railway automatically sets this
# For Docker, use docker-compose networking:
REDIS_HOST=redis
REDIS_PORT=6379
```

### Issue: Frontend can't reach backend
**Solution**: 
1. Check `VITE_API_URL` in frontend environment
2. Verify CORS settings in backend
3. Check Railway backend is actually running

### Issue: Build fails on Railway
**Solution**:
1. Check Dockerfile path in `railway.json`
2. Verify all dependencies in `requirements.txt`
3. Check Railway build logs for specific error

### Issue: Port already in use (local Docker)
**Solution**:
```bash
# Change ports in docker-compose.yml
ports:
  - "3001:80"  # Frontend
  - "8001:8000"  # Backend
```

---

## 📊 Production Checklist

Before going live:
- [ ] Change `API_KEY` from default value
- [ ] Set up Supabase RLS policies
- [ ] Configure rate limiting thresholds
- [ ] Set up monitoring (Railway built-in + Sentry/LogRocket)
- [ ] Add custom domain to Railway backend
- [ ] Add custom domain to Vercel frontend
- [ ] Test all endpoints with production data
- [ ] Set up backup strategy for Redis data
- [ ] Configure WAF/DDoS protection (Cloudflare)
- [ ] Set up SSL certificates (auto with Railway/Vercel)

---

## 🚀 Scaling

### Railway
- Automatic scaling based on traffic
- Upgrade plan for more resources
- Add replicas in dashboard

### Vercel
- Automatic CDN distribution
- Serverless edge functions
- Upgrade for more bandwidth

### Redis
- Railway Redis Pro for persistence
- Consider Redis Cloud for production
- Enable AOF persistence for data durability

---

## 💰 Cost Estimates

**Free Tier (Hobby Projects)**
- Railway: $5/month credit, backend + Redis
- Vercel: Free for personal projects
- Total: ~$0-5/month

**Production (Paid)**
- Railway Pro: $20/month (backend + Redis)
- Vercel Pro: $20/month (team features)
- OpenAI API: ~$10-50/month (depending on usage)
- Pinecone: $70/month (starter)
- Total: ~$120-160/month

---

## 📝 Next Steps

1. **Deploy Backend to Railway**
   ```bash
   railway login
   railway init
   railway up
   ```

2. **Deploy Frontend to Vercel**
   ```bash
   cd frontend
   vercel --prod
   ```

3. **Test Everything**
   - Hit health endpoint
   - Test search functionality
   - Check Redis caching
   - Monitor logs

4. **Set up CI/CD**
   - Connect GitHub to Railway (auto-deploys)
   - Connect GitHub to Vercel (auto-deploys)
   - Both platforms support automatic deployments on push

---

## 🔗 Useful Links

- [Railway Docs](https://docs.railway.app)
- [Vercel Docs](https://vercel.com/docs)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vite Deployment](https://vitejs.dev/guide/static-deploy.html)
