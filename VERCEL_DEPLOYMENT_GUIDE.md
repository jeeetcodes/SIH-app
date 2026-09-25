# 📦 Vercel Deployment Guide - FastAPI Backend Migration

## ✅ Migration Completed

Your FastAPI backend has been successfully migrated from Render to Vercel serverless architecture. All code changes have been applied.

---

## 🚀 Phase 5: Deployment Instructions

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Login to Vercel

```bash
vercel login
```

This will open your browser to authenticate with Vercel (use your GitHub, GitLab, or Bitbucket account).

---

### Step 3: Deploy to Vercel

Navigate to your project root and run:

```bash
cd C:\Users\jeetc\Desktop\Label-polis
vercel
```

**During the setup, answer the prompts as follows:**

- **Set up and deploy?** → `Y` (Yes)
- **Which scope?** → Select your account/team
- **Link to existing project?** → `N` (No, create new project)
- **What's your project's name?** → `packlens` (or your preferred name)
- **In which directory is your code located?** → `./` (press Enter for root)
- **Want to override the settings?** → `N` (No, vercel.json is already configured)

This will deploy to a **preview URL** (e.g., `https://packlens-xyz123.vercel.app`).

---

### Step 4: Add Environment Variables

After the first deployment, add your API keys to Vercel:

#### Option A: Via Vercel CLI (Recommended)

```bash
# Add Gemini API keys (comma-separated for multiple keys)
vercel env add GEMINI_API_KEYS production
# Paste your keys when prompted, e.g.: AIzaSyA...,AIzaSyB...,AIzaSyC...

# Add OpenRouter API key (optional fallback)
vercel env add OPENROUTER_API_KEY production
# Paste your key when prompted

# Add OpenAI API key (optional fallback)
vercel env add OPENAI_API_KEY production
# Paste your key when prompted

# Add Database URL (if using PostgreSQL)
vercel env add DATABASE_URL production
# Paste your database connection string when prompted
```

#### Option B: Via Vercel Dashboard

1. Go to https://vercel.com/dashboard
2. Select your project (`packlens`)
3. Go to **Settings** → **Environment Variables**
4. Add each variable:
   - `GEMINI_API_KEYS` (comma-separated, e.g., `AIzaSyA...,AIzaSyB...`)
   - `OPENROUTER_API_KEY` (optional)
   - `OPENAI_API_KEY` (optional)
   - `DATABASE_URL` (if using PostgreSQL)

---

### Step 5: Deploy to Production

After adding environment variables, deploy to production:

```bash
vercel --prod
```

This will give you your **production URL**, for example:
```
https://packlens.vercel.app
```

---

### Step 6: Update Mobile App with Vercel URL

1. Copy your Vercel production URL (e.g., `https://packlens.vercel.app`)

2. Open `mobile/.env` and update the `EXPO_PUBLIC_API_URL`:

```bash
# Before:
EXPO_PUBLIC_API_URL=https://packlens-3ko8.onrender.com/api/v1

# After (replace with YOUR Vercel URL):
EXPO_PUBLIC_API_URL=https://packlens.vercel.app/api/v1
```

3. Also update the constant in `mobile/src/services/scan-api.ts` (line 68):

```typescript
// Before:
export const PRODUCTION_API_URL = "https://packlens-3ko8.onrender.com/api/v1";

// After (replace with YOUR Vercel URL):
export const PRODUCTION_API_URL = "https://packlens.vercel.app/api/v1";
```

4. Rebuild your Expo app:

```bash
cd mobile
npx expo start --clear
```

---

## 🔍 Testing Your Deployment

### Test the API Health Endpoint

```bash
curl https://YOUR-PROJECT.vercel.app/api/v1/health
```

Expected response:
```json
{"status": "healthy"}
```

### Test the Root Endpoint

```bash
curl https://YOUR-PROJECT.vercel.app/
```

Expected response:
```json
{
  "service": "Label Police API",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

### View API Documentation

Open in your browser:
```
https://YOUR-PROJECT.vercel.app/docs
```

---

## ⚡ Key Changes Made

### Backend Optimizations for Vercel Serverless

1. **Timeout Protection**: Added 9-second internal timeout to return proper JSON errors before Vercel's 10s limit
2. **Reduced HTTP Timeouts**: OpenRouter timeout reduced from 45s → 8s
3. **Fast Provider Cascade**: Zero artificial delays between Gemini/OpenRouter/OpenAI fallbacks
4. **Proper Error Handling**: Returns `503 Service Unavailable` JSON before Vercel timeout HTML

### Frontend Updates

1. **Request Timeout**: Reduced from 120s → 30s (aligned with Vercel execution limits)
2. **Retry Delay**: Reduced from 5s → 3s
3. **Updated Error Messages**: Removed Render-specific cold-start language
4. **API URL Prepared**: Added clear comments for Vercel URL replacement

---

## 📊 Vercel Free Tier Limits

- **Execution Time**: 10 seconds per request (Hobby plan)
- **Bandwidth**: 100 GB/month
- **Deployments**: Unlimited
- **Functions**: Unlimited serverless functions

⚠️ **Important**: If your vision extraction consistently exceeds 10s, consider upgrading to Vercel Pro ($20/month) for 60-second execution limits.

---

## 🐛 Troubleshooting

### Issue: "504 Gateway Timeout"

**Cause**: Vision API took longer than 10 seconds

**Solution**: 
- The backend now returns a proper `503` JSON error before hitting the timeout
- If this persists, upgrade to Vercel Pro for 60s execution limit

### Issue: "No vision providers configured"

**Cause**: Environment variables not set

**Solution**: 
- Verify variables are added via `vercel env ls`
- Redeploy with `vercel --prod` after adding variables

### Issue: Mobile app still hitting Render URL

**Cause**: Environment variables not updated or app not rebuilt

**Solution**:
- Update `mobile/.env` with your Vercel URL
- Run `npx expo start --clear` to clear cache

---

## 🎉 Deployment Complete!

Once you've completed these steps:

1. Your FastAPI backend will be live on Vercel serverless
2. Your Expo mobile app will connect to the new Vercel backend
3. Vision extraction will work within Vercel's 10-second timeout limits
4. No more Render cold-start delays!

---

## 📞 Next Steps

1. Run `vercel --prod` to deploy
2. Copy your production URL
3. Update `mobile/.env` and `mobile/src/services/scan-api.ts`
4. Test the API with curl or Postman
5. Rebuild and test your mobile app
6. Decommission your Render service (optional)

Good luck with your deployment! 🚀
