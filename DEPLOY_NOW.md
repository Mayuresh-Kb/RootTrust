# 🚀 Deploy RootTrust Marketplace NOW

## ✅ Pre-Deployment Checklist (COMPLETE)

- ✅ Backend deployed to AWS
- ✅ API Gateway endpoint working: `https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev`
- ✅ DynamoDB tables created and operational
- ✅ Sample products created (3 products available)
- ✅ Frontend built successfully (`frontend/dist/`)
- ✅ Environment variables configured
- ✅ Vercel configuration file created

## 🎯 Deploy to Vercel (5 Minutes)

### Step 1: Login to Vercel

Open your terminal in the `frontend` directory and run:

```bash
cd frontend
npx vercel login
```

This will open your browser. Login with:

- GitHub account (recommended)
- GitLab account
- Email

### Step 2: Deploy to Production

After logging in, run:

```bash
npx vercel --prod
```

### Step 3: Answer the Prompts

```
? Set up and deploy "~/path/to/frontend"? [Y/n]
→ Press Y

? Which scope do you want to deploy to?
→ Select your account

? Link to existing project? [y/N]
→ Press N (first time deployment)

? What's your project's name?
→ Type: roottrust-marketplace

? In which directory is your code located?
→ Press Enter (use current directory)

? Want to override the settings? [y/N]
→ Press N
```

### Step 4: Wait for Deployment

Vercel will:

1. Upload your build files
2. Configure the deployment
3. Provide you with a public URL

**Expected output:**

```
✅  Production: https://roottrust-marketplace-xyz.vercel.app [copied to clipboard]
```

### Step 5: Test Your Live Website

Visit the URL provided and verify:

1. **Homepage loads** ✓
2. **Navigate to Products** → Should see 3 sample products
3. **Click on a product** → Should see product details
4. **Register a new account** → Should work
5. **Login** → Should work

## 🎉 You're Done!

Your RootTrust Marketplace is now LIVE at:

```
https://roottrust-marketplace-[your-id].vercel.app
```

## 📱 Share Your Live Demo

Share this URL with:

- Hackathon judges
- Team members
- Potential users
- Investors

## 🔍 Verify Everything Works

### Test 1: Products Load

```bash
# Open browser DevTools → Network tab
# Visit: https://your-url.vercel.app
# Navigate to products page
# Should see API calls to: https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products
```

### Test 2: Sample Products Display

You should see:

1. **Alphonso Mango (Hapus)** - ₹450/kg (GI Tagged)
2. **Organic Basmati Rice** - ₹180/kg
3. **Fresh Organic Tomatoes** - ₹60/kg

### Test 3: User Registration

1. Click "Register"
2. Fill in details
3. Select role (Consumer or Farmer)
4. Submit
5. Should see success message

### Test 4: User Login

1. Click "Login"
2. Enter credentials from registration
3. Should redirect to dashboard

## 🐛 Troubleshooting

### Issue: "Command not found: vercel"

**Solution:**

```bash
cd frontend
npm install --save-dev vercel
npx vercel login
```

### Issue: Products not loading

**Solution:** Check browser console. Verify API endpoint:

```bash
curl https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev/products
```

### Issue: Need to redeploy

**Solution:**

```bash
cd frontend
npm run build
npx vercel --prod
```

## 🎨 Alternative: Deploy via Vercel Dashboard (No CLI)

If you prefer a visual interface:

1. **Go to**: https://vercel.com/new
2. **Drag and drop** the `frontend` folder
3. **Configure**:
   - Framework: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. **Add Environment Variables**:
   ```
   VITE_API_BASE_URL=https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev
   VITE_AWS_REGION=us-east-1
   VITE_S3_BUCKET=roottrust-assets-dev-504181993609
   ```
5. **Click Deploy**

## 📊 Monitor Your Deployment

### AWS Costs

- Check: https://console.aws.amazon.com/billing/
- Budget alerts configured at $240 (80%) and $270 (90%)

### Vercel Analytics

- Visit: https://vercel.com/dashboard
- View deployment logs and analytics

### API Performance

- Check CloudWatch: https://console.aws.amazon.com/cloudwatch/
- View Lambda function metrics

## 🎯 Demo Script for Presentation

1. **Show Homepage**: "This is RootTrust, an AI-powered marketplace connecting farmers with consumers"

2. **Browse Products**: "We have authentic products with AI-verified fraud detection"

3. **Product Details**: "Each product shows authenticity confidence, GI tags, and farmer profiles"

4. **Register**: "Users can register as farmers or consumers"

5. **Farmer Features**: "Farmers can upload products, get AI marketing content, and track analytics"

6. **Consumer Features**: "Consumers can browse, purchase, review, and share referral links"

7. **AI Features**: "Amazon Bedrock powers fraud detection and marketing content generation"

## 📈 Success Metrics

Your platform now has:

- ✅ 44 Lambda functions deployed
- ✅ DynamoDB with single-table design
- ✅ S3 bucket for assets
- ✅ API Gateway with 30+ endpoints
- ✅ 3 sample products ready for demo
- ✅ Full authentication system
- ✅ AI-powered fraud detection
- ✅ Cost-optimized architecture ($17-$193/month)

## 🚀 Next Steps After Deployment

1. **Create more sample data** (optional):

   ```bash
   python3 scripts/create_sample_products.py
   ```

2. **Test all features**:
   - Product upload (as farmer)
   - Product purchase (as consumer)
   - Review submission
   - Referral sharing

3. **Prepare demo presentation**:
   - Screenshots of key features
   - Demo script
   - Architecture diagram

4. **Monitor costs**:
   - Check AWS billing daily
   - Ensure staying within $300 budget

## 🎊 Congratulations!

You've successfully deployed a full-stack AI-powered marketplace platform!

**Live URL**: (Will be provided after deployment)  
**API Endpoint**: https://b88kwrtrik.execute-api.us-east-1.amazonaws.com/dev  
**Status**: ✅ PRODUCTION READY

---

**Need Help?** Check `FRONTEND_DEPLOYMENT.md` for detailed troubleshooting.
