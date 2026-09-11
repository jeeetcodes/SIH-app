# How to Get OCR.space API Key (100% Free - No Credit Card)

## Why OCR.space?
- ✅ **25,000 free requests per month**
- ✅ **No credit card required**
- ✅ Supports 100+ languages including Hindi
- ✅ Good accuracy for packaging labels
- ✅ Simple REST API

---

## Step-by-Step Instructions (Takes 1 minute)

### 1. Visit OCR.space API Page
Go to: **[https://ocr.space/ocrapi](https://ocr.space/ocrapi)**

### 2. Scroll Down to "Register for Free API Key"
Look for the section titled **"Register for Free API Key"** (about halfway down the page)

### 3. Enter Your Email
- Enter your email address in the form
- Click **"Register"** or **"Get API Key"**

### 4. Check Your Email
- You'll receive an email from OCR.space within 1-2 minutes
- Subject: "Your OCR.space API Key"
- The email contains your API key

### 5. Copy Your API Key
Your key will look like: `K12345678901234` or `helloworld`

### 6. Add to Your `.env` File
Open `backend/.env` and add:
```env
OCRSPACE_API_KEY=K12345678901234
```

### 7. Restart Your Backend
```bash
# Stop the server (Ctrl+C)
# Then restart:
uvicorn main:app --reload
```

---

## Verify It Works

### Check Configuration Status:
```bash
python -c "from app.config import settings; print('OCR.space configured:', settings.is_ocrspace_configured())"
```

Expected output:
```
OCR.space configured: True
```

---

## Free Tier Limits

| Feature | Free Tier |
|---------|-----------|
| **Requests per month** | 25,000 |
| **Requests per minute** | No hard limit (reasonable use) |
| **Max file size** | 1 MB per image |
| **Languages supported** | 100+ (including English, Hindi) |
| **OCR Engine** | Engine 1 & 2 (we use Engine 2 - more accurate) |

---

## How It Works in Your App

OCR.space is now integrated into your **automatic fallback chain**:

```
1. Try Gemini (multimodal AI) ← Primary
2. Try OpenAI GPT-4o (if configured)
3. Try Anthropic Claude (if configured)
4. Try OpenRouter (if configured)
5. Try OCR.space (text-only OCR) ← NEW!
6. Try Azure Computer Vision (if configured)
7. Try Google Cloud Vision (if configured)
```

**When OCR.space is used:**
- If vision AI providers fail or are rate-limited
- Extracts pure text from the label image
- Uses regex patterns to find: MRP, Net Quantity, Dates, Barcodes
- Fallback to next provider if OCR.space fails

---

## What If I Don't Get the Email?

### Check Spam Folder
The email might be in your spam/junk folder

### Try a Different Email
Some email providers block automated emails. Try:
- Gmail
- Outlook/Hotmail
- ProtonMail

### Manual Registration
1. Go to: [https://ocr.space/ocrapi/freekey](https://ocr.space/ocrapi/freekey)
2. Fill in the registration form
3. Wait for email

### Contact Support
If still no email after 10 minutes:
- Email: support@ocr.space
- They usually respond within 24 hours

---

## Comparison with Other OCR Services

| Service | Free Tier | Credit Card Required? | Accuracy |
|---------|-----------|----------------------|----------|
| **OCR.space** ⭐ | 25,000/month | ❌ No | Good |
| Google Cloud Vision | 1,000/month | ❌ No (initially) | Excellent |
| Azure Computer Vision | 5,000/month | ✅ Yes | Excellent |
| AWS Textract | 1,000/month | ✅ Yes | Excellent |

**OCR.space is the best free option without credit card requirements.**

---

## Upgrade Options (Optional)

If you exceed 25,000 requests/month, OCR.space offers paid plans:

| Plan | Price | Requests/Month |
|------|-------|----------------|
| **Free** | $0 | 25,000 |
| **PRO** | $60/year | 100,000 |
| **PRO PDF** | $150/year | 100,000 + PDF support |

For most development and small production deployments, the free tier is sufficient.

---

## Troubleshooting

### "Invalid API key"
- Double-check you copied the full key from the email
- Remove any extra spaces before/after the key in `.env`
- Make sure you didn't include quotes around the key

### "Rate limit exceeded"
- You've used 25,000 requests this month
- Wait until next month or upgrade to PRO plan
- Your app will automatically fallback to other providers

### "Image too large"
- OCR.space free tier supports max 1MB images
- Your app automatically resizes images before sending
- This should rarely be an issue

---

## Quick Setup Checklist

- [ ] Visit https://ocr.space/ocrapi
- [ ] Register with your email
- [ ] Check email for API key
- [ ] Copy key to `backend/.env` as `OCRSPACE_API_KEY=...`
- [ ] Restart backend server
- [ ] Verify with: `python -c "from app.config import settings; print(settings.is_ocrspace_configured())"`
- [ ] Test by scanning a label in your mobile app

---

## Combined Setup (Recommended)

For best reliability, set up these **100% free** providers:

```env
# Primary Vision AI (FREE - no credit card)
GEMINI_API_KEY=AIzaSy...                    # Get from: https://aistudio.google.com/apikey

# Fallback Models (FREE - no credit card)
OPENROUTER_API_KEY=sk-or-v1-...             # Get from: https://openrouter.ai/keys

# Dedicated OCR (FREE - no credit card)
OCRSPACE_API_KEY=K12345678901234            # Get from: https://ocr.space/ocrapi

# Product Database (FREE - no key needed)
OPEN_FOOD_FACTS_URL=https://world.openfoodfacts.org

# Web Verification (FREE - no credit card)
TAVILY_API_KEY=tvly-...                     # Get from: https://tavily.com
SERPAPI_KEY=...                             # Get from: https://serpapi.com
```

**This gives you multi-provider redundancy with zero cost and no credit card!**

---

## Next Steps

1. ✅ Get OCR.space API key (1 minute)
2. ✅ Add to `.env` file
3. ✅ Restart backend
4. ✅ Test with a real label scan
5. 🎉 Enjoy robust OCR with automatic fallback!

---

**Questions?** Check the main `API_INFRASTRUCTURE.md` or `API_KEY_SETUP_GUIDE.md` documentation.
