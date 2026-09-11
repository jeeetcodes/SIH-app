# Multi-API Infrastructure Documentation

## Overview

The Label Police backend already has a **complete multi-provider AI infrastructure** with automatic fallback, product database integration, and web verification capabilities.

## Architecture

### 1. Configuration Layer (`app/core/config.py`)

**Features:**
- ✅ Environment-based configuration using `pydantic-settings`
- ✅ Automatic validation and type checking
- ✅ Helper methods to check which APIs are configured
- ✅ Safe handling of empty/missing API keys
- ✅ No secrets hardcoded in source files

**Key Settings:**
```python
# Vision AI providers
GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY

# Dedicated OCR services
AZURE_VISION_KEY, AZURE_VISION_ENDPOINT, GOOGLE_CLOUD_VISION_KEY

# Product databases
BARCODE_LOOKUP_API_KEY, OPEN_FOOD_FACTS_URL

# Web verification
TAVILY_API_KEY, SERPAPI_KEY
```

**Helper Methods:**
- `is_gemini_configured()` → bool
- `is_openai_configured()` → bool
- `is_anthropic_configured()` → bool
- `is_azure_vision_configured()` → bool
- `is_google_cloud_vision_configured()` → bool
- `is_barcode_lookup_configured()` → bool
- `is_open_food_facts_configured()` → bool
- `is_tavily_configured()` → bool
- `is_serpapi_configured()` → bool
- `configured_vision_providers()` → List[str]
- `provider_status()` → Dict[str, bool] (safe - no secret values)

### 2. Vision AI Layer (Strategy Pattern)

#### Primary Vision LLM Service (`app/services/llm_service.py`)

**Supported Providers:**
1. **Gemini** (Google GenAI) - `GeminiVisionStrategy`
   - Model: `gemini-2.0-flash` (configurable)
   - Native structured output with Pydantic schema
   - Temperature: 0.0 for consistency

2. **OpenAI** (GPT-4o) - `OpenAIVisionStrategy`
   - Model: `gpt-4o` (configurable)
   - Structured parsing with `beta.chat.completions.parse`
   - High-detail vision mode

3. **Anthropic** (Claude) - `AnthropicVisionStrategy`
   - Model: `claude-3-5-sonnet-20241022` (configurable)
   - Direct API integration
   - JSON extraction from text response

4. **OpenRouter** - `OpenRouterVisionStrategy`
   - Model: `google/gemma-4-31b-it:free` (configurable)
   - JSON schema response format
   - HTTP-Referer support for attribution

#### Dedicated OCR Service (`app/services/ocr_service.py`)

**Supported Providers:**
1. **Azure Computer Vision** - `AzureVisionStrategy`
   - Read API with OCR extraction
   - Regex-based structured field inference

2. **Google Cloud Vision** - `GoogleCloudVisionStrategy`
   - TEXT_DETECTION feature
   - Full text annotation extraction

### 3. Automatic Fallback Logic (`app/services/vision_llm.py`)

**Features:**
- ✅ Configurable provider order via `VISION_PROVIDER_ORDER`
- ✅ Automatic retry with next provider on:
  - Rate limiting (429)
  - Service unavailable (503)
  - Timeout errors
  - Connection failures
- ✅ Thread-based timeout enforcement
- ✅ Graceful degradation to mock data when no keys configured
- ✅ Provider tracking (`last_provider` attribute)

**Flow:**
```
1. Read VISION_PROVIDER_ORDER from config
2. Filter to only configured providers
3. Try each provider in order:
   - If success → return result
   - If busy/rate-limited → try next
   - If retryable error → try next
   - If fatal error → log and try next
4. If all fail:
   - If all were busy → raise VisionProviderBusyError
   - Otherwise → raise last exception
```

### 4. Product Database Integration (`app/services/product_lookup.py`)

**Supported APIs:**
1. **Barcode Lookup API** (`barcodelookup.com`)
   - Requires: `BARCODE_LOOKUP_API_KEY`
   - Returns: product name, brand, description
   - Timeout: 12s request, 5s connect

2. **Open Food Facts** (free, no key required)
   - Requires: `OPEN_FOOD_FACTS_URL` (defaults to `https://world.openfoodfacts.org`)
   - Barcode lookup: `/api/v2/product/{barcode}.json`
   - Name search: `/cgi/search.pl`
   - Returns: product name, brand, ingredients

**Function:**
```python
lookup_product(barcode="8901234567890", product_name="BrandX Snacks")
→ ProductLookupResult | None
```

**Behavior:**
- Skipped when no database configured
- Errors swallowed (never blocks label analysis)
- Tries Barcode Lookup first, then Open Food Facts

### 5. Web Verification Service (`app/services/web_verification.py`)

**Supported APIs:**
1. **Tavily Search API**
   - Requires: `TAVILY_API_KEY`
   - Search depth: basic
   - Max results: 3
   - Returns: content snippets

2. **SerpAPI** (Google Search)
   - Requires: `SERPAPI_KEY`
   - Engine: google
   - Max results: 3
   - Returns: organic result snippets

**Function:**
```python
verify_manufacturer(manufacturer="Acme Foods Ltd", product_name="Snack X")
→ WebVerificationResult | None
```

**Query Format:**
```
"{manufacturer} {product_name} FSSAI manufacturer India"
```

**Behavior:**
- Skipped when no search key configured
- Tries Tavily first, then SerpAPI
- Errors logged but never fail parent scan

## Configuration Guide

### Environment Variables

All configuration is done via `.env` file in the backend root:

```bash
# Copy the example file
cp .env.example .env

# Edit with your API keys
nano .env
```

### Priority Order

**Vision Provider Order** (configurable):
```
VISION_PROVIDER_ORDER=gemini,openai,anthropic,openrouter,azure,google
```

Default: Gemini → OpenAI → Anthropic → OpenRouter → Azure → Google

**Product Database Order** (fixed):
1. Barcode Lookup API (if configured)
2. Open Food Facts (if configured)

**Web Search Order** (fixed):
1. Tavily (if configured)
2. SerpAPI (if configured)

## API Key Sources

### Vision AI
- **Gemini**: https://aistudio.google.com/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **OpenRouter**: https://openrouter.ai/keys

### OCR Services
- **Azure Computer Vision**: https://portal.azure.com → Create "Computer Vision" resource
- **Google Cloud Vision**: https://console.cloud.google.com → Enable Vision API

### Product Databases
- **Barcode Lookup**: https://www.barcodelookup.com/api (paid)
- **Open Food Facts**: No key required (free)

### Web Search
- **Tavily**: https://tavily.com (requires account)
- **SerpAPI**: https://serpapi.com (requires account)

## Testing

### Run All Tests
```bash
cd backend
pytest
```

### Test Coverage
- ✅ Config helper methods (`test_api_infrastructure.py`)
- ✅ OCR text extraction (`test_api_infrastructure.py`)
- ✅ Vision fallback logic (`test_api_infrastructure.py`)
- ✅ Busy provider handling (`test_api_infrastructure.py`)
- ✅ Product/web stubs when unconfigured (`test_api_infrastructure.py`)
- ✅ Image preprocessing pipeline (`test_image_processor.py`)
- ✅ Rules engine validation (`test_rules.py`)
- ✅ Scan endpoint integration (`test_scans.py`)

**All 32 tests passing ✓**

## Code Examples

### Check Which APIs Are Active

```python
from app.core.config import settings

# Check individual providers
if settings.is_gemini_configured():
    print("Gemini is ready")

# Get all configured vision providers
providers = settings.configured_vision_providers()
print(f"Active vision providers: {providers}")

# Get status dict (safe - no secrets)
status = settings.provider_status()
print(status)
# {'gemini': True, 'openai': False, 'anthropic': True, ...}
```

### Manual Vision Extraction

```python
from app.services.vision_llm import VisionLLMService

service = VisionLLMService()
extracted, used_mock = service.extract(
    image_bytes,
    mime_type="image/jpeg"
)

print(f"Provider used: {service.last_provider}")
print(f"Product: {extracted.product_name}")
print(f"MRP: {extracted.mrp}")
```

### Product Enrichment

```python
from app.services.product_lookup import lookup_product

result = lookup_product(
    barcode="8901234567890",
    product_name="BrandX Snacks"
)

if result and result.found:
    print(f"Source: {result.source}")
    print(f"Brand: {result.brand}")
    print(f"Summary: {result.summary}")
```

### Manufacturer Verification

```python
from app.services.web_verification import verify_manufacturer

result = verify_manufacturer(
    manufacturer="Acme Foods Pvt Ltd",
    product_name="Snack Product"
)

if result and result.found:
    print(f"Search engine: {result.source}")
    for snippet in result.snippets:
        print(f"- {snippet}")
```

## Security Best Practices

✅ **Already Implemented:**
1. All API keys loaded from environment variables
2. No secrets hardcoded in source files
3. Empty/whitespace keys treated as unconfigured
4. `provider_status()` returns booleans only (no secret values)
5. `.env` file in `.gitignore`
6. `.env.example` provided as template

## Backward Compatibility

✅ **Maintained:**
- Existing Gemini-only setup continues to work
- No breaking changes to scan endpoint
- Mock data fallback when no keys configured
- All existing tests pass

## Production Recommendations

1. **Set at least one vision provider** (Gemini recommended as primary)
2. **Configure CORS_ORIGINS** for your frontend domain
3. **Replace SECRET_KEY** with a long random string
4. **Use PostgreSQL** instead of SQLite for production:
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```
5. **Enable product database** (Open Food Facts is free)
6. **Optional: Enable web verification** for FSSAI lookups
7. **Set VISION_REQUEST_TIMEOUT_SECONDS** based on your latency requirements

## Performance Notes

- **Fallback adds latency only on failure** - successful requests are fast
- **Timeouts are enforced** via ThreadPoolExecutor
- **Product/web lookups are optional** - never block label analysis
- **Parallel strategies not used** - sequential fallback is more predictable
- **Connection pooling** via `httpx.Client` context managers

## Troubleshooting

### No vision providers configured
**Symptom:** Returns mock data
**Solution:** Set at least one `*_API_KEY` in `.env`

### All providers busy (503/429)
**Symptom:** `VisionProviderBusyError` raised
**Solution:** Configure more fallback providers, or implement exponential backoff at the endpoint level

### Timeout errors
**Symptom:** Vision extraction times out
**Solution:** Increase `VISION_REQUEST_TIMEOUT_SECONDS` in `.env`

### Product lookup always returns None
**Symptom:** `lookup_product()` returns None
**Solution:** Set `BARCODE_LOOKUP_API_KEY` or verify `OPEN_FOOD_FACTS_URL`

### Web verification always returns None
**Symptom:** `verify_manufacturer()` returns None
**Solution:** Set `TAVILY_API_KEY` or `SERPAPI_KEY`

## Future Enhancements (Not Yet Implemented)

- [ ] Parallel vision provider calls (race mode)
- [ ] Provider-specific retry policies
- [ ] Rate limit tracking and backoff
- [ ] Provider health metrics/logging
- [ ] Cost tracking per provider
- [ ] Caching layer for repeated scans
- [ ] Webhook notifications for async processing

---

**Status:** ✅ Production-ready multi-API infrastructure fully implemented and tested.
