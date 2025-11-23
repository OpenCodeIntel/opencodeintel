#!/bin/bash

# CodeIntel Vercel Deployment Script
# This script automates the Vercel frontend deployment

set -e  # Exit on error

echo "🚀 CodeIntel Vercel Deployment Setup"
echo "====================================="
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found!"
    echo ""
    echo "Install it with: npm i -g vercel"
    echo "Or visit: https://vercel.com/cli"
    exit 1
fi

echo "✅ Vercel CLI found"
echo ""

# Navigate to frontend
cd frontend

# Check if backend URL is provided
echo "📋 Environment Variables Setup"
echo "=============================="
echo ""
read -p "Enter your Railway backend URL (e.g., https://your-app.railway.app): " backend_url

if [ -z "$backend_url" ]; then
    echo "❌ Backend URL is required!"
    exit 1
fi

# Trim trailing slash
backend_url=${backend_url%/}

echo ""
echo "Backend URL: $backend_url"
echo ""

# Deploy to Vercel
echo "🚀 Deploying to Vercel..."
echo ""
echo "Choose deployment type:"
echo "1. Preview (test deployment)"
echo "2. Production"
read -p "Enter choice (1 or 2): " deploy_choice

if [ "$deploy_choice" = "1" ]; then
    echo ""
    echo "Deploying preview..."
    vercel --env VITE_API_URL="$backend_url"
elif [ "$deploy_choice" = "2" ]; then
    echo ""
    echo "Deploying to production..."
    vercel --prod --env VITE_API_URL="$backend_url"
else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Go to Vercel dashboard to see your deployment"
echo "2. Update CORS settings in backend/main.py with your Vercel URL"
echo "3. Test your application end-to-end"
echo ""
echo "🎉 Done! Your frontend is deployed to Vercel!"
