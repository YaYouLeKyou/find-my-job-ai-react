# FindMyJobAI Backend - New Architecture

## 📁 Directory Structure

```
backend/
└── app/
    ├── __init__.py              # Package initialization
    ├── main.py                  # FastAPI app with /api/jobs/stream endpoint
    ├── config.py                # Environment configuration management
    ├── services/
    │   ├── __init__.py
    │   ├── scorer.py            # TF-IDF + Cosine Similarity scoring (< 50ms/job)
    │   └── aggregator.py        # Async orchestrator & SSE generator
    └── scrapers/
        ├── __init__.py
        ├── api_sources.py       # France Travail API v2 (async httpx, 2 parallel pages)
        └── web_sources.py       # Lightweight HTTP scrapers (LinkedIn, Indeed, etc.) - 6s timeout
```

## 🚀 Key Features

### 1. **Streaming Endpoint** (`/api/jobs/stream`)
- Uses **Server-Sent Events (SSE)** for real-time progress updates
- Returns `StreamingResponse` with events: `STARTED`, `PROGRESS`, `SCORES_UPDATED`, `COMPLETED`, `ERROR`
- Rate limited to 5 requests/minute per IP

### 2. **Fast AI Scoring** (`services/scorer.py`)
- **TF-IDF + Cosine Similarity** for semantic matching
- Target: **< 50ms per job**
- Batch processing for efficiency
- No external API calls - fully local

### 3. **Async Aggregator** (`services/aggregator.py`)
- Orchestrates parallel searches from multiple sources
- Uses `ThreadPoolExecutor` for concurrent execution
- Configurable timeout per source (default: 6s)
- Generates SSE events automatically

### 4. **API Sources** (`scrapers/api_sources.py`)
- **France Travail API v2** with async `httpx`
- Fetches **2 pages in parallel** for speed
- OAuth2 token caching with expiry
- Retry logic with exponential backoff

### 5. **Web Scrapers** (`scrapers/web_sources.py`)
- Lightweight `requests`-based scrapers
- **6-second timeout** per request
- Browser-like headers to avoid blocking
- Sources: Indeed, LinkedIn, Monster, HelloWork

### 6. **Configuration** (`config.py`)
- Centralized environment variable management
- Validation methods for API keys
- Default model selection based on available keys

## 📦 Dependencies

### Required (in `requirements.txt`)
```
fastapi
uvicorn
httpx>=0.27.0              # Async HTTP client
scikit-learn>=1.3.0        # TF-IDF + Cosine Similarity
beautifulsoup4             # HTML parsing
requests                   # Synchronous HTTP
python-dotenv              # Environment variables
slowapi>=0.1.8             # Rate limiting
```

### Optional
```
tenacity                   # Retry logic (for api_sources.py)
sentence-transformers      # Advanced ML scoring (fallback)
playwright                 # Browser automation (for JS-heavy sites)
```

## 🔄 Migration from `api.py`

The new architecture **reuses** existing code from `api.py`:

### Reused Components
- ✅ Helper functions: `clean_title()`, `clean_html()`, `filter_viable_jobs()`
- ✅ AI functions from `shared/ai.py`: `rank_jobs_with_ai()`, `analyze_cv()`
- ✅ France Travail API logic (rewritten with async httpx)
- ✅ Web scraper selectors (Indeed, LinkedIn, Monster)

### Key Differences
| Aspect | Old (`api.py`) | New (`app/`) |
|--------|----------------|--------------|
| **Structure** | Monolithic (2166 lines) | Modular (6 focused files) |
| **Scoring** | AI-based (Groq/Gemini) | TF-IDF (fast, local) |
| **France Travail** | Synchronous `requests` | Async `httpx` + parallel pages |
| **Scrapers** | Mixed sync/async | Clean separation: API vs Web |
| **SSE** | Inline in endpoint | Dedicated `SearchAggregator` class |
| **Config** | Scattered globals | Centralized `Settings` class |

## 🎯 Performance Targets

| Metric | Target | Implementation |
|--------|--------|----------------|
| **Scoring speed** | < 50ms/job | TF-IDF + batch processing |
| **France Travail** | 2 pages in parallel | `asyncio.gather()` |
| **Scraper timeout** | 6s | `requests` timeout parameter |
| **Parallel sources** | Up to 30 | `ThreadPoolExecutor` |
| **SSE latency** | < 100ms | Direct yield, no buffering |

## 🔧 Usage

### Running the Server
```bash
cd backend
python -m app.main
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Calling the Streaming Endpoint
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/jobs/stream?query=developer&location=Paris&selected_sources=LinkedIn,Indeed,France Travail'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data);
};

eventSource.addEventListener('COMPLETED', (event) => {
  console.log('Search complete!', JSON.parse(event.data));
  eventSource.close();
});
```

### Query Parameters
- `query` (required): Job search query
- `location` (default: "Paris, France"): Location
- `num_ads` (default: 100): Number of results
- `contract` (default: "CDI"): Contract type
- `remote` (default: false): Remote only
- `selected_sources` (default: ""): Comma-separated sources
- `cv_data` (optional): JSON string of CV data for AI scoring

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Diagnostic
curl http://localhost:8000/api/diagnostic

# Stream jobs
curl "http://localhost:8000/api/jobs/stream?query=developer&location=Paris&selected_sources=Indeed,LinkedIn"
```

## 📋 Priority Sources

| Source | Type | Status | Notes |
|--------|------|--------|-------|
| **LinkedIn** | Web scraper | ✅ | Stable |
| **France Travail** | API v2 officielle | ✅ | Stable |
| **Google Jobs** | SerpApi | ✅ | Quota |
| **Adzuna** | API REST | ✅ | Quota |
| **Enhanced** | Multi-source | ✅ | Stable |
| **JobSpy** | Bibliothèque | ✅ | Stable |

## 📝 Notes

- **Pylance errors** in VS Code are expected if dependencies aren't installed. Run `pip install -r requirements.txt` to resolve.
- All scrapers include **error handling** and **logging** for debugging.
- The architecture is **extensible**: add new sources by creating a new scraper class and registering it in `build_source_registry()`.
- On quota errors (HTTP 429/403), sources return an empty list gracefully instead of crashing the stream.