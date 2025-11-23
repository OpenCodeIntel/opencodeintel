.PHONY: help dev prod build test clean deploy

# Default target
help:
	@echo "CodeIntel - Development Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  make dev          - Start all services with hot reload"
	@echo "  make prod         - Start production-like environment"
	@echo "  make build        - Build Docker images"
	@echo "  make stop         - Stop all services"
	@echo "  make clean        - Stop and remove all containers/volumes"
	@echo "  make logs         - View all logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run backend tests"
	@echo "  make test-watch   - Run tests in watch mode"
	@echo "  make coverage     - Run tests with coverage report"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-backend  - Deploy backend to Railway"
	@echo "  make deploy-frontend - Deploy frontend to Vercel"
	@echo "  make deploy-all      - Deploy both backend and frontend"

# Development with hot reload
dev:
	docker compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "✅ Development environment started!"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Redis:    localhost:6379"
	@echo ""
	@echo "View logs: make logs"

# Production-like environment
prod:
	docker compose up -d
	@echo ""
	@echo "✅ Production environment started!"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"

# Build images
build:
	docker compose build

# Stop services
stop:
	docker compose down
	docker compose -f docker-compose.dev.yml down

# Clean everything (including volumes)
clean:
	docker compose down -v
	docker compose -f docker-compose.dev.yml down -v
	@echo "✅ Cleaned all containers and volumes"

# View logs
logs:
	docker compose logs -f

# Run backend tests
test:
	cd backend && python -m pytest tests/ -v

# Run tests in watch mode
test-watch:
	cd backend && python -m pytest tests/ -v --looponfail

# Run tests with coverage
coverage:
	cd backend && python -m pytest tests/ --cov=. --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report: backend/htmlcov/index.html"

# Deploy backend to Railway
deploy-backend:
	@echo "🚀 Deploying backend to Railway..."
	railway up
	@echo "✅ Backend deployed!"

# Deploy frontend to Vercel
deploy-frontend:
	@echo "🚀 Deploying frontend to Vercel..."
	cd frontend && vercel --prod
	@echo "✅ Frontend deployed!"

# Deploy everything
deploy-all: deploy-backend deploy-frontend
	@echo "✅ All services deployed!"

# Quick restart of backend (for dev)
restart-backend:
	docker compose restart backend
	@echo "✅ Backend restarted"

# Quick restart of frontend (for dev)
restart-frontend:
	docker compose restart frontend
	@echo "✅ Frontend restarted"

# Shell into backend container
shell-backend:
	docker compose exec backend bash

# Shell into Redis
shell-redis:
	docker compose exec redis redis-cli

# View Redis stats
redis-stats:
	docker compose exec redis redis-cli INFO

# Check service health
health:
	@echo "Checking services..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Backend not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend is up" || echo "❌ Frontend not responding"
	@docker compose exec redis redis-cli ping > /dev/null && echo "✅ Redis is up" || echo "❌ Redis not responding"

# Install dependencies (local dev without Docker)
install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# Run locally without Docker
run-backend-local:
	cd backend && uvicorn main:app --reload --port 8000

run-frontend-local:
	cd frontend && npm run dev
