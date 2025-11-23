#!/bin/bash
# CodeIntel Docker & Deployment Verification Script

set -e

echo "🔍 CodeIntel Setup Verification"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "1️⃣ Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker installed"
    
    if docker info &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker daemon running"
    else
        echo -e "${RED}✗${NC} Docker daemon not running"
        echo -e "${YELLOW}Start Docker Desktop and run this script again${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Docker not installed"
    echo "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check Docker Compose
echo ""
echo "2️⃣ Checking Docker Compose..."
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose available"
else
    echo -e "${RED}✗${NC} Docker Compose not available"
    exit 1
fi

# Check .env file
echo ""
echo "3️⃣ Checking environment variables..."
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} Root .env file exists"
    
    # Check required variables
    required_vars=("OPENAI_API_KEY" "PINECONE_API_KEY" "SUPABASE_URL" "SUPABASE_KEY" "API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env; then
            echo -e "${GREEN}✓${NC} $var is set"
        else
            echo -e "${RED}✗${NC} $var is missing or empty"
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Set these variables in .env before deployment${NC}"
    fi
else
    echo -e "${RED}✗${NC} .env file not found"
    echo "Copy .env.example to .env and fill in your API keys"
    exit 1
fi

# Check Dockerfiles
echo ""
echo "4️⃣ Checking Dockerfiles..."
if [ -f backend/Dockerfile ]; then
    echo -e "${GREEN}✓${NC} Backend Dockerfile exists"
else
    echo -e "${RED}✗${NC} Backend Dockerfile missing"
fi

if [ -f frontend/Dockerfile ]; then
    echo -e "${GREEN}✓${NC} Frontend Dockerfile exists"
else
    echo -e "${RED}✗${NC} Frontend Dockerfile missing"
fi

# Check deployment files
echo ""
echo "5️⃣ Checking deployment configuration..."
if [ -f railway.json ]; then
    echo -e "${GREEN}✓${NC} railway.json exists"
else
    echo -e "${YELLOW}⚠${NC}  railway.json missing"
fi

if [ -f DEPLOYMENT.md ]; then
    echo -e "${GREEN}✓${NC} DEPLOYMENT.md exists"
else
    echo -e "${YELLOW}⚠${NC}  DEPLOYMENT.md missing"
fi

# Check CLI tools (optional)
echo ""
echo "6️⃣ Checking deployment CLI tools (optional)..."
if command -v railway &> /dev/null; then
    echo -e "${GREEN}✓${NC} Railway CLI installed"
else
    echo -e "${YELLOW}⚠${NC}  Railway CLI not installed (needed for Railway deployment)"
    echo "   Install: npm i -g @railway/cli"
fi

if command -v vercel &> /dev/null; then
    echo -e "${GREEN}✓${NC} Vercel CLI installed"
else
    echo -e "${YELLOW}⚠${NC}  Vercel CLI not installed (needed for Vercel deployment)"
    echo "   Install: npm i -g vercel"
fi

# Summary
echo ""
echo "================================"
echo "📊 Summary"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "🏠 Local Development:"
echo "   docker compose up -d"
echo "   # Frontend: http://localhost:3000"
echo "   # Backend: http://localhost:8000"
echo "   # API Docs: http://localhost:8000/docs"
echo ""
echo "☁️  Deploy Backend to Railway:"
echo "   ./scripts/deploy-railway.sh"
echo ""
echo "☁️  Deploy Frontend to Vercel:"
echo "   ./scripts/deploy-vercel.sh"
echo ""
echo "📝 Check logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker compose down"
echo ""
echo "✅ Setup verification complete!"
