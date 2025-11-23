# Docker Troubleshooting Guide

Common issues and solutions for running CodeIntel with Docker.

## Issue: Docker daemon not running

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///Users/.../.docker/run/docker.sock
```

**Solution:**
1. Open Docker Desktop application
2. Wait for it to fully start (whale icon in menu bar should be steady)
3. Run your command again

---

## Issue: Environment variables not found

**Symptoms:**
```
level=warning msg="The \"OPENAI_API_KEY\" variable is not set"
```

**Solution:**
1. Make sure `.env` file exists in project root (not just in backend/)
2. Check `.env` has all required variables:
   - OPENAI_API_KEY
   - PINECONE_API_KEY
   - PINECONE_INDEX_NAME
   - SUPABASE_URL
   - SUPABASE_KEY
   - API_KEY

3. Restart services:
   ```bash
   docker compose down
   docker compose up -d
   ```

---

## Issue: Port already in use

**Symptoms:**
```
Error: bind: address already in use
```

**Solution:**

**Option 1:** Stop conflicting service
```bash
# Find what's using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

**Option 2:** Change ports in `docker-compose.yml`
```yaml
backend:
  ports:
    - "8001:8000"  # External:Internal

frontend:
  ports:
    - "3001:80"
```

---

## Issue: Build fails with dependency errors

**Symptoms:**
```
ERROR [backend 4/7] RUN pip install -r requirements.txt
```

**Solution:**
1. Clear Docker build cache:
   ```bash
   docker compose build --no-cache backend
   ```

2. If still failing, check `requirements.txt` for version conflicts

---

## Issue: Redis connection fails

**Symptoms:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:**
1. Check Redis is running:
   ```bash
   docker compose ps
   ```

2. Redis should show "healthy" status
3. If unhealthy, restart it:
   ```bash
   docker compose restart redis
   ```

---

## Issue: Frontend shows "Network Error"

**Symptoms:**
- Frontend loads but can't connect to backend
- Console shows CORS errors

**Solution:**
1. Check backend is running:
   ```bash
   docker compose logs backend
   ```

2. Verify `VITE_API_URL` is correct in `docker-compose.yml`:
   ```yaml
   frontend:
     environment:
       - VITE_API_URL=http://localhost:8000  # For local dev
   ```

3. Check CORS settings in `backend/main.py`:
   ```python
   allow_origins=[
       "http://localhost:3000",
       "http://localhost",
   ]
   ```

---

## Issue: Tree-sitter parsers not building

**Symptoms:**
```
ERROR: Failed to build tree-sitter parser
```

**Solution:**
Already handled in Dockerfile with build-essential and git. If still failing:

1. Rebuild with no cache:
   ```bash
   docker compose build --no-cache backend
   ```

2. Check logs for specific parser error:
   ```bash
   docker compose logs backend | grep tree-sitter
   ```

---

## Issue: Containers keep restarting

**Symptoms:**
```
docker compose ps
# Shows "Restarting" status
```

**Solution:**
1. Check container logs:
   ```bash
   docker compose logs backend
   docker compose logs frontend
   ```

2. Common causes:
   - Missing environment variables
   - Port conflicts
   - Application crashes on startup

3. Test without restart policy:
   ```bash
   docker compose down
   # Remove restart: unless-stopped from docker-compose.yml temporarily
   docker compose up
   ```

---

## Issue: Database connection fails

**Symptoms:**
```
supabase.exceptions.AuthError: Invalid API key
```

**Solution:**
1. Verify Supabase credentials in `.env`
2. Check SUPABASE_URL and SUPABASE_KEY are correct
3. Test connection manually:
   ```bash
   docker compose exec backend python -c "from services.database import get_repositories; print(get_repositories())"
   ```

---

## Issue: Volume permissions error

**Symptoms:**
```
ERROR: Permission denied: '/app/repos'
```

**Solution:**
1. Check volume permissions in `docker-compose.yml`
2. Create repos directory manually:
   ```bash
   mkdir -p backend/repos
   chmod 755 backend/repos
   ```

---

## Complete Reset (Nuclear Option)

If nothing else works:

```bash
# Stop everything
docker compose down

# Remove all volumes (WARNING: deletes all data)
docker compose down -v

# Remove all containers, images, networks
docker system prune -a

# Rebuild from scratch
docker compose up -d --build
```

---

## Useful Debug Commands

```bash
# View all running containers
docker ps

# View all containers (including stopped)
docker ps -a

# Check logs for specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f redis

# Execute command in running container
docker compose exec backend bash
docker compose exec backend python --version

# Check resource usage
docker stats

# Inspect service configuration
docker compose config

# Check network connectivity
docker compose exec backend ping redis
docker compose exec backend curl http://backend:8000/health
```

---

## Still Having Issues?

1. Check GitHub Issues: https://github.com/DevanshuNEU/v1--codeintel/issues
2. Run verification script: `./scripts/verify-setup.sh`
3. Check DEPLOYMENT.md for step-by-step instructions
4. Make sure Docker Desktop has enough resources (Settings → Resources)
   - Recommended: 4GB RAM, 2 CPUs minimum
