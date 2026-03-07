#!/bin/bash

# RootTrust Marketplace - One-Command Frontend Deployment
# This script will deploy your frontend to Vercel

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   🚀 RootTrust Marketplace - Frontend Deployment          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if dist exists, if not build
if [ ! -d "dist" ]; then
    echo "🔨 Building production bundle..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "❌ Build failed!"
        exit 1
    fi
    echo "✅ Build complete"
    echo ""
fi

# Check if Vercel CLI is available
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npx not found. Please install Node.js"
    exit 1
fi

echo "🌐 Deploying to Vercel..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Please answer the following prompts:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Set up and deploy? → Y"
echo "  2. Which scope? → Select your account"
echo "  3. Link to existing project? → N (first time)"
echo "  4. Project name? → roottrust-marketplace"
echo "  5. Directory? → Press Enter"
echo "  6. Override settings? → N"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Deploy to Vercel
npx vercel --prod

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   ✅ DEPLOYMENT SUCCESSFUL!                                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🎉 Your RootTrust Marketplace is now LIVE!"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Visit the URL provided above"
    echo "   2. Test user registration and login"
    echo "   3. Browse the 3 sample products"
    echo "   4. Share the URL with stakeholders"
    echo ""
    echo "🔗 Backend API:"
    echo "   https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev"
    echo ""
    echo "📚 Documentation:"
    echo "   - DEPLOY_NOW.md - Quick start guide"
    echo "   - FRONTEND_DEPLOYMENT.md - Detailed instructions"
    echo "   - FINAL_DEPLOYMENT_STATUS.md - Complete status"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   🎊 CONGRATULATIONS! Your platform is production-ready!  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
else
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   ❌ DEPLOYMENT FAILED                                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Please check the error messages above."
    echo ""
    echo "Common issues:"
    echo "  - Not logged in to Vercel → Run: npx vercel login"
    echo "  - Build errors → Check frontend/dist/ exists"
    echo "  - Network issues → Check internet connection"
    echo ""
    echo "For help, see: FRONTEND_DEPLOYMENT.md"
    exit 1
fi
