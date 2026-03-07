# RootTrust Marketplace - Frontend Deployment Guide

## Current Status

✅ **Backend Deployed**: AWS Lambda + API Gateway  
✅ **API Endpoint**: `https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev`  
✅ **Sample Data**: 3 products created in DynamoDB  
✅ **Frontend Built**: Production build ready in `frontend/dist/`

## Quick Deployment to Vercel

### Option 1: Deploy via Vercel CLI (Recommended)

1. **Install Vercel CLI** (if not already installed):

   ```bash
   cd frontend
   npm install --save-dev vercel
   ```

2. **Login to Vercel**:

   ```bash
   npx vercel login
   ```

3. **Deploy to Production**:

   ```bash
   npx vercel --prod
   ```

4. **Follow the prompts**:
   - Set up and deploy? **Y**
   - Which scope? Select your account
   - Link to existing project? **N**
   - Project name? **roottrust-marketplace** (or your choice)
   - Directory? **./frontend** (or just press Enter if already in frontend/)
   - Override settings? **N**

5. **Deployment will complete** and provide you with a public URL like:
   ```
   https://roottrust-marketplace.vercel.app
   ```

### Option 2: Deploy via Vercel Dashboard (No CLI Required)

1. **Go to**: https://vercel.com/new

2. **Import Git Repository**:
   - Click "Import Git Repository"
   - Connect your GitHub/GitLab account
   - Select this repository

3. **Configure Project**:
   - Framework Preset: **Vite**
   - Root Directory: **frontend**
   - Build Command: `npm run build`
   - Output Directory: `dist`

4. **Environment Variables** (Add these):

   ```
   VITE_API_BASE_URL=https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev
   VITE_AWS_REGION=us-east-1
   VITE_S3_BUCKET=roottrust-assets-dev-504181993609
   VITE_RAZORPAY_KEY_ID=test_key_id
   ```

5. **Click Deploy** and wait for completion

### Option 3: Deploy via GitHub Integration (Automatic)

1. **Push code to GitHub**:

   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Connect to Vercel**:
   - Go to https://vercel.com
   - Click "New Project"
   - Import from GitHub
   - Select your repository

3. **Vercel will auto-detect** Vite configuration and deploy

## Alternative: Deploy to AWS Amplify

### Using AWS Amplify Console

1. **Go to AWS Amplify Console**: https://console.aws.amazon.com/amplify/

2. **Create New App**:
   - Click "New app" → "Host web app"
   - Choose "Deploy without Git provider"

3. **Manual Deploy**:

   ```bash
   cd frontend
   npm run build
   zip -r dist.zip dist/
   ```

4. **Upload** `dist.zip` to Amplify Console

5. **Configure**:
   - App name: **RootTrust Marketplace**
   - Environment: **production**

6. **Amplify will provide** a URL like:
   ```
   https://main.d1234567890.amplifyapp.com
   ```

## Verify Deployment

After deployment, test these features:

### 1. Homepage Loads

- Visit your deployment URL
- Should see RootTrust Marketplace homepage

### 2. Product Listing Works

- Navigate to marketplace/products
- Should see 3 sample products:
  - Alphonso Mango (Hapus)
  - Organic Basmati Rice
  - Fresh Organic Tomatoes

### 3. Registration Works

- Click "Register"
- Create a new consumer account
- Should receive success message

### 4. Login Works

- Login with registered credentials
- Should be redirected to dashboard

### 5. API Connection Works

- Open browser DevTools → Network tab
- Navigate to products page
- Should see successful API calls to:
  ```
  https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products
  ```

## Sample Products Available

The marketplace now has 3 demo products:

1. **Alphonso Mango (Hapus)**
   - Category: Fruits
   - Price: ₹450/kg
   - GI Tag: Yes (Ratnagiri)
   - Rating: 4.9/5

2. **Organic Basmati Rice**
   - Category: Grains
   - Price: ₹180/kg
   - GI Tag: No
   - Rating: 4.7/5

3. **Fresh Organic Tomatoes**
   - Category: Vegetables
   - Price: ₹60/kg
   - GI Tag: No
   - Rating: 4.8/5

## Troubleshooting

### Issue: Products not loading

**Solution**: Check browser console for CORS errors. Verify API endpoint in `.env.production`

### Issue: 404 on page refresh

**Solution**: Vercel should handle this automatically with `vercel.json`. If using other hosting, configure SPA routing.

### Issue: Build fails

**Solution**:

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Issue: API calls failing

**Solution**: Verify API Gateway endpoint is accessible:

```bash
curl https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products
```

## Post-Deployment Checklist

- [ ] Frontend is accessible via public URL
- [ ] Products page loads and displays 3 sample products
- [ ] User registration works
- [ ] User login works
- [ ] Product detail pages load
- [ ] Images display correctly
- [ ] API calls succeed (check Network tab)
- [ ] No console errors
- [ ] Mobile responsive design works

## Next Steps

1. **Share the URL** with stakeholders/judges
2. **Create more sample data** if needed (run `scripts/create_sample_products.py` again)
3. **Monitor AWS costs** via CloudWatch dashboard
4. **Test all user flows** before demo/presentation

## Support

If you encounter issues:

1. Check browser console for errors
2. Check Network tab for failed API calls
3. Verify AWS Lambda logs in CloudWatch
4. Test API endpoints directly with curl

## Deployment Complete! 🎉

Your RootTrust Marketplace is now live and accessible to the world!
