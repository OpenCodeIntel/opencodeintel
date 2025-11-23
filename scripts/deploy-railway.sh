#!/bin/bash

# CodeIntel Railway Deployment Script
# This script automates the Railway deployment setup

set -e  # Exit on error

echo "🚀 CodeIntel Railway Deployment Setup"
echo "========================================"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found!"
    echo ""
    echo "Install it with: npm i -g @railway/cli"
    echo "Or visit: https://docs.railway.app/develop/cli"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# Login to Railway
echo "📝 Logging into Railway..."
railway login

echo ""
echo "🔧 Setting up Railway project..."
echo ""
echo "Choose an option:"
echo "1. Create new Railway project"
echo "2. Link to existing Railway project"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "Creating new Railway project..."
    railway init
elif [ "$choice" = "2" ]; then
    echo ""
    echo "Linking to existing project..."
    railway link
else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo ""
echo "✅ Railway project configured!"
echo ""

# Ask about environment variables
echo "📋 Environment Variables Setup"
echo "=============================="
echo ""
echo "You need to set these environment variables in Railway dashboard:"
echo ""
echo "Required:"
echo "  - OPENAI_API_KEY"
echo "  - PINECONE_API_KEY"
echo "  - PINECONE_INDEX_NAME"
echo "  - SUPABASE_URL"
echo "  - SUPABASE_KEY"
echo "  - API_KEY (production secret - CHANGE from default!)"
echo ""
echo "Optional (set automatically by Railway Redis):"
echo "  - REDIS_URL (auto-set when you add Redis service)"
echo ""

read -p "Have you set these in Railway dashboard? (y/n): " env_set

if [ "$env_set" != "y" ]; then
    echo ""
    echo "⚠️  Please set environment variables first:"
    echo "   1. Go to Railway dashboard"
    echo "   2. Select your project"
    echo "   3. Go to Variables tab"
    echo "   4. Add all required variables"
    echo ""
    echo "Then run this script again."
    exit 0
fi

# Ask about Redis
echo ""
echo "🗄️  Redis Setup"
echo "==============="
echo ""
read -p "Have you added Redis service in Railway dashboard? (y/n): " redis_added

if [ "$redis_added" != "y" ]; then
    echo ""
    echo "⚠️  Add Redis service:"
    echo "   1. Railway Dashboard → New → Database → Redis"
    echo "   2. Railway will automatically set REDIS_URL"
    echo ""
    echo "Then run this script again."
    exit 0
fi

# Deploy
echo ""
echo "🚀 Deploying to Railway..."
echo ""
railway up

echo ""
echo "✅ Deployment initiated!"
echo ""
echo "📊 Check deployment status:"
echo "   railway logs -f"
echo ""
echo "🔗 Get deployment URL:"
echo "   railway domain"
echo ""
echo "Next steps:"
echo "1. Wait for deployment to complete (check Railway dashboard)"
echo "2. Get your backend URL: railway domain"
echo "3. Update VITE_API_URL in frontend with backend URL"
echo "4. Deploy frontend to Vercel"
echo ""
echo "🎉 Done! Your backend is deploying to Railway!"
