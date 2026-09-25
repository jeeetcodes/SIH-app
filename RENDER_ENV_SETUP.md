# Render Environment Variables Configuration Guide

## How to Add Multiple Gemini API Keys

Your backend now supports **multiple API keys** for better rate limit handling and automatic fallback.

### Steps to Configure on Render:

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Select your service**: `label-police-api`
3. **Navigate to**: Environment tab (left sidebar)
4. **Add/Update these environment variables**:

### Required Variables:

```bash
# NEW: Multiple Gemini keys (recommended)
GEMINI_API_KEYS=key1,key2,key3

# Format: Comma-separated, NO SPACES between keys
# Example: GEMINI_API_KEYS=AIzaSyA...abc123,AIzaSyB...xyz789,AIzaSyC...def456
```

### Optional Variables:

```bash
# Legacy single key (backward compatible)
GEMINI_API_KEY=your-single-key-here

# OpenRouter fallback (Layer 2 backup when all Gemini keys exhausted)
OPENROUTER_API_KEY=your-openrouter-key-here
```

### Important Notes:

- **You do NOT need to touch your local `.env` file** for production changes
- Your **local `.env`** is only for local development/testing
- **Render** reads environment variables from the dashboard, not from `.env`
- After adding variables, Render will automatically redeploy your service

### Cascade Priority:

1. **Layer 1**: Tries all keys in `GEMINI_API_KEYS` across multiple models
2. **Layer 2**: Falls back to OpenRouter free models (if `OPENROUTER_API_KEY` is set)
3. **Layer 3**: Falls back to OpenAI (if `OPENAI_API_KEY` is set)

### Testing After Adding Keys:

After deploying, test your API endpoint:
```bash
curl -X POST https://your-render-url.onrender.com/api/v1/scans/analyze \
  -F "file=@test-image.jpg"
```

Check logs on Render dashboard to see which provider/key was used.

### How It Works:

```
Code reads from settings:
  settings.gemini_api_keys_list
     ↓
  Checks environment: GEMINI_API_KEYS or GEMINI_API_KEY
     ↓
  Local Dev: reads from backend/.env
  Production: reads from Render dashboard env vars
```

---

## Summary:

✅ **For Production**: Add `GEMINI_API_KEYS` on Render Dashboard  
✅ **For Local Dev**: Add to `backend/.env`  
✅ **Format**: `key1,key2,key3` (comma-separated, no spaces)  
✅ **Zero Code Changes**: Just update environment variables
