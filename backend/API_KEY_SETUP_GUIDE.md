# API Key Setup Guide for Label Police

This guide walks you through obtaining API keys for all supported services.

## Quick Start (Recommended - FREE)

For immediate testing, you only need **one free API key**:

### 1. Gemini API (Google AI Studio) - **FREE TIER AVAILABLE** ⭐

**Why start here:** 
- Completely free tier with generous limits
- Best performance for label extraction
- No credit card required

**Steps:**
1. Visit: https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)
5. Paste into your `.env` file:
   ```env
   GEMINI_API_KEY=AIzaSyAbc123YourActualKeyHere
   ```

**Free Tier Limits:**
- 15 requests per minute
- 1 million tokens per minute
- 1,500 requests per day
- **Perfect for development and moderate production use**

---

## Additional Vision AI Providers (Fallback & Enhanced Reliability)

### 2. OpenAI API (GPT-4o) - **PAID**

**When to add:**
- You need fallback when Gemini hits rate limits
- You want the absolute best accuracy (GPT-4o is slightly better on complex labels)

**Steps:**
1. Visit: https://platform.openai.com/signup
2. Sign up and verify your account
3. Add payment method (required, but you only pay for usage)
4. Go to: https://platform.openai.com/api-keys
5. Click **"Create new secret key"**
6. Name it: "Label Police Backend"
7. Copy the key (starts with `sk-proj-...` or `sk-...`)
8. Add to `.env`:
   ```env
   OPENAI_API_KEY=sk-proj-YourActualKeyHere
   ```

**Pricing:**
- GPT-4o: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Estimate:** ~$0.01-0.05 per label scan

**Free Credits:**
- New accounts often get $5-18 in free credits (varies by region/promotion)

---

### 3. Anthropic API (Claude 3.5 Sonnet) - **PAID**

**When to add:**
- You want a third fallback layer
- You prefer Claude's vision capabilities

**Steps:**
1. Visit: https://console.anthropic.com/
2. Sign up for an account
3. Add payment method
4. Go to: https://console.anthropic.com/settings/keys
5. Click **"Create Key"**
6. Copy the key (starts with `sk-ant-...`)
7. Add to `.env`:
   ```env
   ANTHROPIC_API_KEY=sk-ant-YourActualKeyHere
   ```

**Pricing:**
- Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- **Estimate:** ~$0.02-0.06 per label scan

---

### 4. OpenRouter (100+ Models Gateway) - **FREEMIUM**

**When to add:**
- You want access to many free models
- You want to experiment with different models

**Steps:**
1. Visit: https://openrouter.ai/
2. Sign up with Google/GitHub
3. Go to: https://openrouter.ai/keys
4. Click **"Create Key"**
5. Copy the key (starts with `sk-or-...`)
6. Add to `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-YourActualKeyHere
   OPENROUTER_SITE_URL=https://labelpolice.yourapp.com
   ```

**Free Models Available:**
- Google Gemma 2 9B (free)
- Meta Llama 3.1 8B (free)
- Many more community-hosted models

---

## Dedicated OCR Services (Optional - for text-only extraction)

### 5. Azure Computer Vision - **FREE TIER AVAILABLE**

**When to add:**
- You want pure OCR without multimodal AI
- You need Microsoft Azure compliance

**Steps:**
1. Visit: https://portal.azure.com/
2. Sign in or create a free Azure account
3. Click **"Create a resource"**
4. Search for **"Computer Vision"**
5. Click **Create** and fill in:
   - **Subscription:** Your subscription
   - **Resource group:** Create new or select existing
   - **Region:** Choose closest to you (e.g., Central India)
   - **Name:** `label-police-vision`
   - **Pricing tier:** F0 (Free) or S1 (Standard)
6. Click **Review + Create**, then **Create**
7. After deployment, go to your resource
8. Under **Resource Management** → **Keys and Endpoint**
9. Copy:
   - **KEY 1** → `AZURE_VISION_KEY`
   - **Endpoint** → `AZURE_VISION_ENDPOINT`
10. Add to `.env`:
    ```env
    AZURE_VISION_KEY=1234567890abcdef1234567890abcdef
    AZURE_VISION_ENDPOINT=https://label-police-vision.cognitiveservices.azure.com
    ```

**Free Tier:**
- 5,000 transactions per month
- After free tier: $1 per 1,000 transactions

---

### 6. Google Cloud Vision API - **FREE TIER AVAILABLE**

**When to add:**
- You want Google's dedicated OCR service
- You're already using Google Cloud

**Steps:**
1. Visit: https://console.cloud.google.com/
2. Create a new project: "Label Police"
3. Enable **Vision API**:
   - Search for "Vision API" in the search bar
   - Click **Enable**
4. Create API credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **API Key**
   - Copy the key
   - (Recommended) Click **Restrict Key** and limit to Vision API only
5. Add to `.env`:
   ```env
   GOOGLE_CLOUD_VISION_KEY=AIzaSyYourCloudVisionKeyHere
   ```

**Free Tier:**
- 1,000 units per month (1 text detection = 1 unit)
- After free tier: $1.50 per 1,000 units

---

## Product Database APIs (Optional - for barcode enrichment)

### 7. Open Food Facts - **FREE** ⭐

**Already configured!** No API key needed.

This is a free, open-source database of food products worldwide.

```env
OPEN_FOOD_FACTS_URL=https://world.openfoodfacts.org
```

**For India-specific products:**
```env
OPEN_FOOD_FACTS_URL=https://in.openfoodfacts.org
```

---

### 8. Barcode Lookup API - **PAID**

**When to add:**
- Open Food Facts doesn't have good coverage for your products
- You need comprehensive commercial product database

**Steps:**
1. Visit: https://www.barcodelookup.com/api
2. Choose a plan:
   - Starter: $29.95/month (5,000 lookups)
   - Pro: $49.95/month (15,000 lookups)
3. Sign up and get your API key
4. Add to `.env`:
   ```env
   BARCODE_LOOKUP_API_KEY=your-api-key-here
   ```

---

## Web Verification APIs (Optional - for FSSAI/manufacturer lookup)

### 9. Tavily Search API - **FREEMIUM**

**When to add:**
- You want to verify manufacturer details online
- You want to look up FSSAI license numbers

**Steps:**
1. Visit: https://tavily.com/
2. Sign up for an account
3. Go to your dashboard
4. Copy your API key
5. Add to `.env`:
   ```env
   TAVILY_API_KEY=tvly-YourKeyHere
   ```

**Free Tier:**
- 1,000 searches per month

---

### 10. SerpAPI (Google Search) - **FREEMIUM**

**When to add:**
- Fallback for Tavily
- You need more comprehensive Google search results

**Steps:**
1. Visit: https://serpapi.com/
2. Sign up for an account
3. Go to: https://serpapi.com/manage-api-key
4. Copy your API key
5. Add to `.env`:
   ```env
   SERPAPI_KEY=your-serpapi-key-here
   ```

**Free Tier:**
- 100 searches per month

---

## Recommended Setup for Different Use Cases

### **Minimum Setup (FREE)** - Development & Testing
```env
GEMINI_API_KEY=AIzaSy...  # Google AI Studio (FREE)
OPEN_FOOD_FACTS_URL=https://world.openfoodfacts.org  # Already set (FREE)
```

### **Reliable Setup (FREEMIUM)** - Small Production
```env
GEMINI_API_KEY=AIzaSy...  # Primary (FREE)
OPENAI_API_KEY=sk-proj-...  # Fallback ($5 free credits usually)
OPEN_FOOD_FACTS_URL=https://world.openfoodfacts.org
```

### **Enterprise Setup (PAID)** - High Volume Production
```env
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
AZURE_VISION_KEY=...
BARCODE_LOOKUP_API_KEY=...
TAVILY_API_KEY=tvly-...
```

---

## After Adding Keys

1. **Save your `.env` file**

2. **Verify configuration:**
   ```bash
   cd backend
   python -c "from app.config import settings; import json; print(json.dumps(settings.provider_status(), indent=2))"
   ```

   Expected output:
   ```json
   {
     "gemini": true,
     "openai": false,
     "anthropic": false,
     ...
   }
   ```

3. **Run tests:**
   ```bash
   pytest
   ```

4. **Start the server:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Test with a real image:**
   - Use your mobile app to scan a product label
   - Check the logs to see which provider was used
   - Look for: `"Vision extraction succeeded via gemini"`

---

## Security Reminders

✅ **Never commit `.env` to git** (already in `.gitignore`)

✅ **Use different keys for development vs production**

✅ **Rotate keys periodically**

✅ **Restrict API keys by IP/domain when possible**

✅ **Monitor usage in each provider's dashboard**

---

## Troubleshooting

### "No vision providers configured"
**Solution:** Add at least `GEMINI_API_KEY` to `.env`

### "VisionProviderBusyError: All providers rate-limited"
**Solution:** Add more fallback providers (OpenAI, Anthropic)

### "Invalid API key"
**Solution:** Double-check the key format and regenerate if needed

### Keys not loading
**Solution:** 
- Restart the server after editing `.env`
- Check for extra spaces or quotes around keys
- Verify `.env` is in the `backend/` directory

---

## Cost Estimation

For a typical Label Police deployment scanning **1,000 labels per day**:

| Provider | Monthly Cost | Notes |
|----------|-------------|-------|
| Gemini (free tier) | **$0** | Works for ~1,500 scans/day |
| Gemini (paid) | ~$15-30 | If you exceed free tier |
| OpenAI GPT-4o | ~$30-50 | As fallback only |
| Anthropic Claude | ~$40-60 | As fallback only |
| Open Food Facts | **$0** | Always free |
| Barcode Lookup | $30-50 | Paid subscription |
| Tavily/SerpAPI | **$0-20** | Free tier usually enough |

**Recommended budget:** $0-50/month depending on scale.

---

## Next Steps

1. ✅ Get your Gemini API key (5 minutes, free)
2. ✅ Add it to `.env`
3. ✅ Test with `pytest`
4. ✅ Deploy and scan your first label!
5. (Optional) Add fallback providers as you scale

---

**Need help?** Check the logs in `backend/` or the main `API_INFRASTRUCTURE.md` documentation.
