# Playwright Setup Guide

## Why Playwright?

Your job search results degraded because job sites (Indeed, Monster, Careerbuilder, Simplyhired, etc.) now use **anti-bot detection** (Cloudflare/WAF, JavaScript-rendered content, bot fingerprinting). The original `requests` + `BeautifulSoup` scrapers cannot execute JavaScript, so they return empty or CAPTCHA pages.

Playwright uses a **real Chromium browser engine** to:
- Execute JavaScript (render dynamic content)
- Bypass bot detection (stealth mode, realistic browser fingerprint)
- Handle Cloudflare challenges

## Installation

### Option 1: Automatic (recommended)
```bash
pip install playwright
playwright install chromium
```

### Option 2: Using the setup script
```bash
# Windows
python -m backend.setup_playwright

# Or run directly
pip install playwright && playwright install chromium
```

### Option 3: Docker (for production)
Playwright is included in the Docker image automatically.

## How It Works

1. When the `requests`-based scrapers return 0 results (due to anti-bot detection), the backend automatically falls back to Playwright scrapers.
2. Playwright launches a headless Chromium browser with stealth plugins to bypass detection.
3. The scrapers navigate to job sites, wait for content to render, and extract job listings.

## New French Job Sources Added

In addition to Playwright, the following new French job sources have been added:

| Source | Description |
|--------|-------------|
| **Welcome to the Jungle** | Premium French tech/startup job board with public API |
| **HelloWork** | Major French job board (formerly Pôle Emploi Entreprises) |
| **APEC** | Executive/cadre job board (requires login for full access) |
| **JobTeaser** | Student/recent graduate job platform |

These sources are more reliable because they either:
- Have public APIs that don't require scraping
- Are less aggressive with anti-bot detection
- Focus on the French market (better relevance for French job seekers)

## Configuration

No additional configuration is needed. The Playwright scrapers are automatically enabled when:
1. Playwright is installed (`pip install playwright`)
2. Browser binaries are installed (`playwright install chromium`)
3. The `requests`-based scrapers return 0 results for a source

If Playwright is not installed, the backend gracefully falls back to the original `requests`-based scrapers.

## Troubleshooting

### "Playwright scrapers not available" warning
Install Playwright: `pip install playwright && playwright install chromium`

### Browser fails to launch
- Ensure Chromium is installed: `playwright install chromium`
- On Linux, you may need system dependencies: `playwright install-deps chromium`
- On Windows, ensure you have the latest Visual C++ Redistributable

### Slow performance
Playwright is slower than `requests` because it launches a real browser. This is expected.
- Each scraper launches and closes a browser instance
- Results are cached for 1 hour (Redis) to avoid repeated scraping
- Only sources with 0 results trigger the Playwright fallback

### Still getting 0 results
- Check that your API keys are configured in `.env` (Adzuna, SerpApi, Jooble)
- Try enabling more sources in the frontend
- Check the backend logs for specific error messages
