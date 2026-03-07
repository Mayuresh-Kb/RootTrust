#!/bin/bash

# RootTrust Marketplace - Vercel Deployment Script

echo "🚀 RootTrust Marketplace - Deploying to Vercel"
echo "================================================"
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from frontend directory"
    exit 1
fi

# Check if build exists
if [ ! -d "dist" ]; then
    echo "📦 Building production bundle..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "❌ Build failed!"
        exit 1
    fi
    echo "✅ Build complete!"
    echo ""
fi

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
echo ""
echo "Please follow the prompts:"
echo "  - Set up and deploy? Y"
echo "  - Which scope? Select your account"
echo "  - Link to existing project? N (first time) or Y (subsequent)"
echo "  - Project name? roottrust-marketplace"
echo "  - Directory? ./ (press Enter)"
echo "  - Override settings? N"
echo ""

npx vercel --prod

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✅ Deployment successful!"
    echo ""
    echo "Your RootTrust Marketplace is now live!"
    echo ""
    echo "Next steps:"
    echo "1. Visit the URL provided above"
    echo "2. Test user registration and login"
    echo "3. Browse the 3 sample products"
    echo "4. Share the URL with stakeholders"
    echo ""
    echo "API Endpoint: https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev"
    echo "================================================"
else
    echo ""
    echo "❌ Deployment failed!"
    echo "Please check the error messages above."
    exit 1
fi
