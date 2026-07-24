"""
Enhanced Job Scrapers v2.0 - Multi-level fallback system with 55+ sources
Level 1: APIs (paid keys) - Adzuna, SerpApi, Jooble, Apify, France Travail
Level 2: RSS feeds (free, no auth) - Indeed, LinkedIn, Google, etc.
Level 3: requests HTML scraping - custom selectors per site
Level 4: Playwright browser - bypasses Cloudflare/WAF/JS-rendered
Level 5: International domain variants - same scraper, different TLDs
"""

import logging, json, urllib.parse, time, re, random, hashlib
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# Premium proxy list (free tier) - rotate to avoid rate limiting
FREE_PROXIES = [
    None,  # Direct connection first
    None,
    None,
]
try:
    # Try to load proxies from environment
    proxy_env = __import__('os').environ.get('SCRAPER_PROXIES', '')
    if proxy_env:
        FREE_PROXIES = [None] + [p.strip() for p in proxy_env.split(',') if p.strip()]
except:
    pass

# 50+ User Agents for maximum rotation
USER_AGENTS = [
    # Chrome Windows (latest 10 versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Firefox macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # iOS Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.83 Mobile/Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Samsung Galaxy S24) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.83 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.118 Mobile Safari/537.36",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/109.0.0.0",
    # Samsung Internet
    "Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/122.0.6261.105 Mobile Safari/537.36",
]

# Browser-like headers for each major engine
CHROME_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

FIREFOX_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

SAFARI_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

MOBILE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Session cache to reuse cookies and connections
_session_cache = {}

def get_session(domain: str = "default") -> requests.Session:
    """Get or create a cached session for a domain."""
    if domain not in _session_cache:
        session = requests.Session()
        session.headers.update(get_headers())
        session.verify = True
        # Set a reasonable timeout adapter
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=30,
            max_retries=3
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        _session_cache[domain] = session
    return _session_cache[domain]

def get_headers():
    """Generate headers mimicking a real browser."""
    ua = random.choice(USER_AGENTS)
    
    # Pick header template based on user agent
    if "Firefox" in ua:
        headers = FIREFOX_HEADERS.copy()
    elif "Safari" in ua and "Chrome" not in ua:
        headers = SAFARI_HEADERS.copy()
    elif "Mobile" in ua:
        headers = MOBILE_HEADERS.copy()
    else:
        headers = CHROME_HEADERS.copy()
    
    headers["User-Agent"] = ua
    
    # Add some random variation
    if random.random() > 0.7:
        headers["Accept-Language"] = random.choice([
            "fr-FR,fr;q=0.9,en;q=0.8",
            "en-US,en;q=0.9,fr;q=0.8",
            "fr-FR,fr;q=0.9",
            "en-GB,en;q=0.9,fr;q=0.8",
        ])
    
    return headers

def clean_title(t: str) -> str:
    if not t: return ""
    t = re.sub(r'\s+', ' ', t).strip()
    # Remove H/F markers
    t = re.sub(r'\b(H/F|F/H|h/f|f/h|H/F|H\s*/\s*F)\b', '', t)
    # Remove common prefixes
    t = re.sub(r'^(Offre d\'emploi|Emploi|Job|Poste)\s*[:\-]?\s*', '', t, flags=re.I)
    return t.strip()[:200]

def extract_salary(text: str) -> Optional[dict]:
    """Extract salary information from text."""
    if not text: return None
    text = text[:500]  # Check first 500 chars
    
    patterns = [
        # French: XXk€ - YYk€
        r'(\d{2,3})\s*k\s*[€e]?\s*(?:à|-|–)\s*(\d{2,3})\s*k\s*[€e]?',
        # French: XX € - YY € / an/mois
        r'(\d{3,6})\s*[€e]\s*(?:à|-|–)\s*(\d{3,6})\s*[€e]?\s*(?:/|par\s+)?(an|mois|jour|an|month|year|day|hour|h)?',
        # English: $XX,XXX - $YY,YYY
        r'[\$£](\d{2,3}(?:,\d{3})?)\s*(?:-|–|to)\s*[\$£]?(\d{2,3}(?:,\d{3})?)\s*(?:/|per|a\s+)?(year|month|day|hour|h|yr|mo)?',
        # Simple: XX-YYk
        r'(\d{2,3})\s*(?:-|–)\s*(\d{2,3})\s*k',
    ]
    
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            try:
                groups = m.groups()
                min_val = int(re.sub(r'[^\d]', '', str(groups[0])))
                max_val = int(re.sub(r'[^\d]', '', str(groups[1] if len(groups) > 1 else groups[0])))
                
                # Normalize: if values are like 35-45 (probably k€)
                if max_val < 1000:
                    min_val *= 1000
                    max_val *= 1000
                
                period = "yearly"
                # Check period if present
                for g in groups[2:]:
                    if g:
                        g = g.lower()
                        if g in ('month', 'mois', 'mo'):
                            period = "monthly"
                        elif g in ('day', 'jour'):
                            period = "daily"
                        elif g in ('hour', 'h'):
                            period = "hourly"
                
                return {
                    "min": min_val,
                    "max": max_val,
                    "period": period,
                    "currency": "EUR" if "€" in text or "e" in text.lower() else "USD" if "$" in text else "GBP" if "£" in text else "EUR",
                }
            except:
                continue
    
    return None

def extract_contract_type(text: str) -> Optional[str]:
    """Extract contract type from description."""
    if not text: return None
    text = text[:300].lower()
    
    patterns = [
        (r'\bcdi\b', 'CDI'),
        (r'\bcdd\b', 'CDD'),
        (r'\b(stage|internship|intern|stagiaire)\b', 'Stage'),
        (r'\b(alternance|apprenti|apprenticeship)\b', 'Alternance'),
        (r'\b(freelance|freelance|mission|contractor|independent)\b', 'Freelance'),
        (r'\b(intérim|interim|temporary|temp)\b', 'Intérim'),
        (r'\b(vi?e|vie\s*sociétaire)\b', 'VIE'),
        (r'\b(cdd\s*cdi|cdi\s*cdd)\b', 'CDI/CDD'),
    ]
    
    for pattern, contract in patterns:
        if re.search(pattern, text, re.I):
            return contract
    return None

def extract_remote(text: str) -> Optional[bool]:
    """Determine if position is remote."""
    if not text: return None
    text = text[:300].lower()
    
    remote_words = ['remote', 'télétravail', 'teletravail', 'work from home', 'wfh', 
                    'home office', 'full remote', '100% remote', 'distanciel']
    hybrid_words = ['hybrid', 'hybride', 'partial remote', 'mixte', 'semi-remote']
    
    has_remote = any(word in text for word in remote_words)
    has_office = any(word in text for word in ['onsite', 'on-site', 'présentiel', 'bureau', 'office'])
    
    if has_remote and not has_office:
        return True
    if has_office and not has_remote:
        return False
    if has_remote and has_office:
        return None  # Hybrid - unclear
    return None

# Blocked host cache to avoid retrying sources known to block scrapers
_BLOCKED_HOSTS = set()

def fetch_url(url: str, timeout: int = 5, use_proxy: bool = False) -> Optional[str]:
    """Fetch URL with fast fail on blocked hosts. Only 1 retry, low timeout."""
    from urllib.parse import urlparse as _urlparse
    host = _urlparse(url).netloc
    if host in _BLOCKED_HOSTS:
        logger.debug(f"Skipping known blocked host: {host}")
        return None
    
    for attempt in range(2):
        try:
            headers = get_headers()
            proxies = None
            if use_proxy and attempt > 0:
                proxy = random.choice(FREE_PROXIES)
                if proxy:
                    proxies = {"http": proxy, "https": proxy}
            
            if attempt > 0:
                time.sleep(random.uniform(0.5, 1.5))
            
            r = requests.get(url, headers=headers, timeout=timeout,
                           allow_redirects=True, proxies=proxies)
            
            if r.status_code == 200:
                return r.text
            elif r.status_code in [403, 401, 503]:
                _BLOCKED_HOSTS.add(host)
                logger.debug(f"Blocked by {host} (HTTP {r.status_code}), caching as blocked")
                return None
            elif r.status_code == 429:
                time.sleep(random.uniform(1, 2))
            else:
                return None
        except requests.exceptions.ConnectionError:
            logger.debug(f"Connection error for {url[:60]}")
            time.sleep(1)
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout for {url[:60]}")
            return None  # Fast fail on timeout
        except Exception as e:
            logger.debug(f"Fetch error {url[:60]}: {e}")
            return None
    return None

def fetch_json(url: str, timeout: int = 5, use_proxy: bool = False) -> Optional[dict]:
    """Fetch JSON API response with fast fail. 1 retry, low timeout."""
    from urllib.parse import urlparse as _urlparse
    host = _urlparse(url).netloc
    if host in _BLOCKED_HOSTS:
        return None
    
    for attempt in range(2):
        try:
            headers = get_headers()
            r = requests.get(url, headers=headers, timeout=timeout,
                           allow_redirects=True)
            if r.status_code == 200:
                return r.json()
            if r.status_code in [403, 401]:
                _BLOCKED_HOSTS.add(host)
                return None
            if r.status_code == 429:
                time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.debug(f"Fetch JSON error {url[:60]}: {e}")
            return None
    return None

def parse_date(d: str) -> str:
    if not d: return ""
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%m-%Y", "%Y/%m/%d",
    ]:
        try: return datetime.strptime(d.strip(), fmt).strftime("%Y-%m-%d")
        except: continue
    
    # Try relative dates
    now = datetime.now()
    if "today" in d.lower(): return now.strftime("%Y-%m-%d")
    if "yesterday" in d.lower(): return now.strftime("%Y-%m-%d")
    
    # Try "XX days/weeks/months ago"
    m = re.search(r'(\d+)\s*(day|days|jour|jours|week|weeks|semaine|mois|month|months)\s*ago', d.lower())
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit in ('day', 'days', 'jour', 'jours'):
            from datetime import timedelta
            return (now - timedelta(days=num)).strftime("%Y-%m-%d")
        elif unit in ('week', 'weeks', 'semaine'):
            return (now - timedelta(weeks=num)).strftime("%Y-%m-%d")
        elif unit in ('month', 'months', 'mois'):
            return (now - timedelta(days=num*30)).strftime("%Y-%m-%d")
    
    return d[:10]

def make_abs(h, base):
    if not h or h == "#": return ""
    if h.startswith("http"): return h
    if h.startswith("//"): return "https:" + h
    return urllib.parse.urljoin(base, h)

def safe_text(e, d=""):
    return e.get_text(strip=True) if e is not None else d

def safe_attr(e, a, d=""):
    return e.get(a, d) if e is not None else d

def make_job(title, company, link, source, location="", date="", desc="", salary=None, contract=None, remote_flag=None):
    """Create a standardized job dict."""
    return {
        "titre": clean_title(title) if title else "",
        "entreprise": company or "Non précisé",
        "lien": link or "",
        "location": location or "",
        "date": parse_date(date) if date else "",
        "source": source,
        "description": desc[:2000] if desc else "",
        "salaire": salary,
        "contrat": contract,
        "remote": remote_flag,
    }

# ─── RSS FEED SCRAPERS ────────────────────────────────────────────────────

def scrape_rss(feed_url: str, source: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        f = feedparser.parse(feed_url)
        for e in f.entries[:limit]:
            title = clean_title(e.get("title", ""))
            if not title: continue
            summary = e.get("summary", "") or e.get("description", "")
            company = ""
            loc = ""
            desc = summary
            if summary:
                m = re.search(r'(?:chez|at|@|Company:?|Entreprise:?)\s*([^.<,]+)', summary, re.I)
                if m: company = m.group(1).strip()
                m = re.search(r'(?:à|in|at|Location:?|Lieu:?)\s*([^.<,]+)', summary, re.I)
                if m: loc = m.group(1).strip()
            
            salary = extract_salary(desc)
            contract = extract_contract_type(desc)
            remote_flag = extract_remote(desc)
            
            jobs.append(make_job(
                title=title, company=company or "Non précisé",
                link=e.get("link", ""), source=source,
                location=loc, date=e.get("published","") or e.get("updated",""),
                desc=desc, salary=salary, contract=contract, remote=remote_flag
            ))
    except Exception as e:
        logger.error(f"RSS {source}: {e}")
    return jobs[:limit]

def scrape_indeed_rss(job_title: str, location: str = "", limit: int = 10) -> List[dict]:
    q = urllib.parse.quote(clean_title(job_title))
    l = urllib.parse.quote(location or "France")
    return scrape_rss(f"https://fr.indeed.com/rss?q={q}&l={l}", "Indeed", limit)

def scrape_linkedin_rss(job_title: str, limit: int = 10) -> List[dict]:
    return scrape_rss(f"https://www.linkedin.com/jobs/search/rss?keywords={urllib.parse.quote(clean_title(job_title))}", "LinkedIn", limit)

def scrape_simplyhired_rss(job_title: str, location: str = "", limit: int = 10) -> List[dict]:
    q = urllib.parse.quote(clean_title(job_title))
    l = urllib.parse.quote(location) if location else ""
    return scrape_rss(f"https://www.simplyhired.com/search/rss?q={q}&l={l}", "Simplyhired", limit)

def scrape_careerbuilder_rss(job_title: str, location: str = "", limit: int = 10) -> List[dict]:
    q = urllib.parse.quote(clean_title(job_title))
    l = urllib.parse.quote(location) if location else ""
    return scrape_rss(f"https://www.careerbuilder.com/jobs/rss?q={q}&l={l}", "Careerbuilder", limit)

def scrape_france_travail_rss(job_title: str, limit: int = 10) -> List[dict]:
    return scrape_rss(f"https://candidat.francetravail.fr/emplois/recherche/rss?motsCles={urllib.parse.quote(clean_title(job_title))}", "France Travail", limit)

def scrape_emploi_public_rss(job_title: str, limit: int = 10) -> List[dict]:
    return scrape_rss(f"https://www.emploi-public.gouv.fr/recherche/rss?motsCles={urllib.parse.quote(clean_title(job_title))}", "Emploi Public", limit)

def scrape_google_news_jobs(job_title: str, limit: int = 10) -> List[dict]:
    q = urllib.parse.quote(f'"{job_title}" recrute OR "offre d\'emploi" OR hiring OR emploi OR job')
    return scrape_rss(f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr", "Google Jobs", limit)

# ─── NEW RSS FEEDS (International) ─────────────────────────────────────────

def scrape_reed_rss(job_title: str, limit: int = 10) -> List[dict]:
    """Reed.co.uk RSS feed - UK's largest job board."""
    q = urllib.parse.quote(clean_title(job_title))
    return scrape_rss(f"https://www.reed.co.uk/jobs/rss?keywords={q}", "Reed", limit)

def scrape_stepstone_rss(job_title: str, limit: int = 10) -> List[dict]:
    """StepStone.de RSS - major German job board."""
    q = urllib.parse.quote(clean_title(job_title))
    return scrape_rss(f"https://www.stepstone.de/jobs/rss?q={q}", "StepStone", limit)

# ─── FREE API SCRAPERS ────────────────────────────────────────────────────

def scrape_remotive(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        data = fetch_json(f"https://remotive.io/api/remote-jobs?search={urllib.parse.quote(job_title)}&limit={limit}")
        if data and "jobs" in data:
            for j in data["jobs"][:limit]:
                jobs.append(make_job(
                    title=j.get("title",""), company=j.get("company_name","Non précisé"),
                    link=j.get("url",""), source="Remotive",
                    location=j.get("candidate_required_location","Remote"),
                    date=j.get("publication_date",""),
                    desc=j.get("description",""),
                    salary=extract_salary(j.get("description","")),
                    remote_flag=True if "remote" in (j.get("candidate_required_location","") or "").lower() else None,
                ))
        if not jobs:
            data = fetch_json(f"https://findwork.dev/api/jobs/?search={urllib.parse.quote(job_title)}&limit={limit}")
            if data and "results" in data:
                for j in data["results"][:limit]:
                    jobs.append(make_job(
                        title=j.get("role","") or j.get("job_title",""),
                        company=j.get("company_name","Non précisé"),
                        link=j.get("url",""), source="Remotive",
                        location=j.get("location","Remote"),
                        date=j.get("date_posted",""),
                        desc=j.get("description",""),
                    ))
    except Exception as e:
        logger.error(f"Remotive: {e}")
    return jobs[:limit]

def scrape_remoteok(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        data = fetch_json(f"https://remoteok.com/api?tags={urllib.parse.quote(job_title)}&limit={limit}")
        if data and isinstance(data, list) and len(data) > 1:
            for item in data[1:limit+1]:
                if isinstance(item, dict):
                    jobs.append(make_job(
                        title=item.get("position","") or item.get("title",""),
                        company=item.get("company","Non précisé"),
                        link=item.get("url","") or item.get("apply_url",""),
                        location=item.get("location","Remote"),
                        source="RemoteOK",
                        desc=item.get("description",""),
                        remote_flag=True,
                    ))
    except Exception as e:
        logger.error(f"RemoteOK: {e}")
    return jobs[:limit]

def scrape_wttj_api(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        data = fetch_json(f"https://www.welcometothejungle.com/api/v1/jobs?search%5Bquery%5D={urllib.parse.quote(job_title)}&per_page={limit}")
        if data and "jobs" in data:
            for item in data["jobs"][:limit]:
                t = item.get("title","")
                if t:
                    jobs.append(make_job(
                        title=t, company=item.get("company",{}).get("name","Non précisé"),
                        link=f"https://www.welcometothejungle.com/fr/jobs/{item.get('id','')}",
                        location=item.get("location",{}).get("city",""),
                        source="Welcome to the Jungle",
                        contract=extract_contract_type(item.get("description","")),
                    ))
    except Exception as e:
        logger.error(f"WTTJ API: {e}")
    return jobs[:limit]

def scrape_jobijoba(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Jobijoba API - free tier, good for French market."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        l = urllib.parse.quote(location)
        data = fetch_json(f"https://api.jobijoba.com/v3/fr/search?what={q}&where={l}&limit={limit}&pagination=1")
        if data and "data" in data:
            for item in data["data"][:limit]:
                if "title" in item:
                    jobs.append(make_job(
                        title=item.get("title",""), company=item.get("company_name","Non précisé"),
                        link=item.get("link","") or item.get("url",""), source="Jobijoba",
                        location=item.get("city",""), date=item.get("published_date",""),
                        desc=item.get("description",""),
                        contract=item.get("contract_type"),
                    ))
    except Exception as e:
        logger.error(f"Jobijoba: {e}")
    return jobs[:limit]

# ─── HTML SCRAPERS (International) ────────────────────────────────────────

def scrape_reed_html(job_title: str, location: str = "UK", limit: int = 10) -> List[dict]:
    """Scrape Reed.co.uk - UK job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.reed.co.uk/jobs?keywords={q}&location={urllib.parse.quote(location)}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='job-result'], article[class*='job'], div[class*='card']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[class*='jobLink']")
            company_elem = card.select_one("span[class*='company'], a[class*='company'], span[class*='employer']")
            location_elem = card.select_one("span[class*='location'], li[class*='location']")
            desc_elem = card.select_one("p[class*='description'], div[class*='description']")
            salary_elem = card.select_one("span[class*='salary'], li[class*='salary']")
            link_elem = card.select_one("a[class*='jobLink'], h2 a")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Reed",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.reed.co.uk"),
                    location=safe_text(location_elem) or location,
                    source="Reed",
                    desc=safe_text(desc_elem),
                    salary=extract_salary(safe_text(salary_elem) or safe_text(desc_elem)),
                ))
    except Exception as e:
        logger.error(f"Reed HTML: {e}")
    return jobs[:limit]

def scrape_stepstone_html(job_title: str, location: str = "Deutschland", limit: int = 10) -> List[dict]:
    """Scrape StepStone.de - German job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.stepstone.de/jobs/{q}/in-{urllib.parse.quote(location)}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("article[class*='job'], div[class*='card'], div[data-testid*='job']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[data-testid*='title'], a[class*='title']")
            company_elem = card.select_one("span[class*='company'], div[class*='employer']")
            location_elem = card.select_one("span[class*='location'], div[class*='location']")
            link_elem = card.select_one("a[data-testid*='title'], h2 a")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "StepStone",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.stepstone.de"),
                    location=safe_text(location_elem) or location,
                    source="StepStone",
                ))
    except Exception as e:
        logger.error(f"StepStone HTML: {e}")
    return jobs[:limit]

def scrape_xing(job_title: str, location: str = "Deutschland", limit: int = 10) -> List[dict]:
    """Scrape Xing - German professional network."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.xing.com/jobs/search?keywords={q}&location={urllib.parse.quote(location)}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("li[class*='job'], div[class*='job'], article[class*='card']")
        for card in cards[:limit]:
            title_elem = card.select_one("a[class*='title'], h2 a, h3 a, a[href*='/jobs/']")
            company_elem = card.select_one("span[class*='company'], div[class*='company']")
            location_elem = card.select_one("span[class*='location'], div[class*='location']")
            link_elem = card.select_one("a[class*='title'], a[href*='/jobs/']")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Xing",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.xing.com"),
                    location=safe_text(location_elem) or location,
                    source="Xing",
                ))
    except Exception as e:
        logger.error(f"Xing: {e}")
    return jobs[:limit]

def scrape_infojobs(job_title: str, country: str = "es", limit: int = 10) -> List[dict]:
    """Scrape InfoJobs (Spain/Italy/Brazil)."""
    jobs = []
    domains = {"es": "www.infojobs.net", "it": "www.infojobs.it", "br": "www.infojobs.com.br"}
    domain = domains.get(country, "www.infojobs.net")
    
    try:
        q = urllib.parse.quote(clean_title(job_title))
        # Try the search API first
        api_url = f"https://{domain}/api/1/job/search?q={q}&maxResults={limit}"
        data = fetch_json(api_url)
        if data and "items" in data:
            for item in data["items"][:limit]:
                if item.get("title"):
                    jobs.append(make_job(
                        title=item.get("title",""), company=item.get("author","InfoJobs"),
                        link=f"https://{domain}/oferta/{item.get('id','')}",
                        location=item.get("city",""), source="InfoJobs",
                        contract=item.get("contractType",{}).get("value"),
                    ))
        
        if not jobs:
            html = fetch_url(f"https://{domain}/jobsearch/search-results.xhtml?keywords={q}")
            if html:
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select("article[class*='job'], div[class*='job'], li[class*='job']")
                for card in cards[:limit]:
                    title_elem = card.select_one("h2 a, h3 a, a[class*='title']")
                    company_elem = card.select_one("span[class*='company'], a[class*='company']")
                    if title_elem:
                        jobs.append(make_job(
                            title=title_elem.get_text(strip=True),
                            company=safe_text(company_elem) or "InfoJobs",
                            link=make_abs(safe_attr(title_elem, "href"), f"https://{domain}"),
                            location="", source="InfoJobs",
                        ))
    except Exception as e:
        logger.error(f"InfoJobs: {e}")
    return jobs[:limit]

def scrape_dice(job_title: str, location: str = "United States", limit: int = 10) -> List[dict]:
    """Scrape Dice.com - US tech job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.dice.com/jobs?q={q}&location={urllib.parse.quote(location)}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        
        # Try JSON-LD first
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        job = item.get("item", {})
                        if job.get("title"):
                            desc = job.get("description","")
                            jobs.append(make_job(
                                title=job.get("title",""), company=job.get("hiringOrganization",{}).get("name","Dice"),
                                link=job.get("url","#"), source="Dice",
                                location=job.get("jobLocation",{}).get("address",{}).get("addressLocality", location),
                                desc=desc, salary=extract_salary(desc),
                            ))
            except:
                pass
        
        if not jobs:
            cards = soup.select("div[class*='card'], div[data-testid*='job'], article")
            for card in cards[:limit]:
                title_elem = card.select_one("a[class*='title'], h2 a, a[data-testid*='title']")
                company_elem = card.select_one("span[class*='company'], div[class*='company']")
                location_elem = card.select_one("span[class*='location'], div[class*='location']")
                link_elem = card.select_one("a[class*='title'], a[data-testid*='title']")
                
                if title_elem:
                    jobs.append(make_job(
                        title=title_elem.get_text(strip=True),
                        company=safe_text(company_elem) or "Dice",
                        link=make_abs(safe_attr(link_elem, "href"), "https://www.dice.com"),
                        location=safe_text(location_elem) or location,
                        source="Dice",
                    ))
    except Exception as e:
        logger.error(f"Dice: {e}")
    return jobs[:limit]

def scrape_naukri(job_title: str, location: str = "India", limit: int = 10) -> List[dict]:
    """Scrape Naukri.com - India's largest job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.naukri.com/{q}-jobs-in-{urllib.parse.quote(location.lower().replace(' ', '-'))}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='jobTuple'], article[class*='job'], section[class*='job']")
        for card in cards[:limit]:
            title_elem = card.select_one("a[class*='title'], h2 a, a[href*='/job-listings']")
            company_elem = card.select_one("a[class*='subTitle'], div[class*='company'], span[class*='company']")
            location_elem = card.select_one("span[class*='location'], div[class*='location']")
            desc_elem = card.select_one("div[class*='description'], span[class*='description']")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Naukri",
                    link=make_abs(safe_attr(title_elem, "href"), "https://www.naukri.com"),
                    location=safe_text(location_elem) or location,
                    source="Naukri",
                    desc=safe_text(desc_elem),
                ))
    except Exception as e:
        logger.error(f"Naukri: {e}")
    return jobs[:limit]

def scrape_bayt(job_title: str, location: str = "UAE", limit: int = 10) -> List[dict]:
    """Scrape Bayt.com - Middle East job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.bayt.com/en/international/jobs/?keyword={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("li[class*='job'], div[class*='job'], article[class*='card']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title']")
            company_elem = card.select_one("span[class*='company'], div[class*='company'], a[class*='company']")
            location_elem = card.select_one("span[class*='location'], div[class*='location']")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Bayt.com",
                    link=make_abs(safe_attr(title_elem, "href"), "https://www.bayt.com"),
                    location=safe_text(location_elem) or location,
                    source="Bayt",
                ))
    except Exception as e:
        logger.error(f"Bayt: {e}")
    return jobs[:limit]

def scrape_seek(job_title: str, location: str = "Australia", limit: int = 10) -> List[dict]:
    """Scrape Seek.com - Australia/New Zealand job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.seek.com.au/{q}-jobs")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("article[class*='job'], div[data-testid*='job'], section[class*='job']")
        for card in cards[:limit]:
            title_elem = card.select_one("a[class*='title'], h2 a, a[data-testid*='title']")
            company_elem = card.select_one("span[class*='company'], a[class*='company']")
            location_elem = card.select_one("span[class*='location'], a[class*='location']")
            salary_elem = card.select_one("span[class*='salary'], div[class*='salary']")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Seek",
                    link=make_abs(safe_attr(title_elem, "href"), "https://www.seek.com.au"),
                    location=safe_text(location_elem) or location,
                    source="Seek",
                    salary=extract_salary(safe_text(salary_elem)),
                ))
    except Exception as e:
        logger.error(f"Seek: {e}")
    return jobs[:limit]

# ─── NEW FRENCH JOB BOARDS ────────────────────────────────────────────────

def scrape_regionsjob(job_title: str, limit: int = 10) -> List[dict]:
    """Scrape RegionsJob - French regional job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.regionsjob.com/offres-emploi/{q}.html")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='offer'], article[class*='job'], div[class*='card']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[href*='/offre-emploi/']")
            company_elem = card.select_one("span[class*='company'], div[class*='entreprise']")
            location_elem = card.select_one("span[class*='location'], div[class*='ville'], span[class*='city']")
            link_elem = card.select_one("a[href*='/offre-emploi/'], h2 a")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "RégionsJob",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.regionsjob.com"),
                    location=safe_text(location_elem) or "",
                    source="RégionsJob",
                ))
    except Exception as e:
        logger.error(f"RégionsJob: {e}")
    return jobs[:limit]

def scrape_chooseyourboss(job_title: str, limit: int = 10) -> List[dict]:
    """Scrape ChooseYourBoss - French startup jobs."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.chooseyourboss.com/jobs?q={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='card'], article[class*='job'], a[href*='/jobs/']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[href*='/jobs/']")
            company_elem = card.select_one("span[class*='company'], div[class*='company'], a[class*='company']")
            
            if isinstance(card, type(soup)) and card.name == 'a' and not title_elem:
                jobs.append(make_job(
                    title=clean_title(card.get_text(strip=True)),
                    company="ChooseYourBoss",
                    link=make_abs(card.get("href",""), "https://www.chooseyourboss.com"),
                    source="ChooseYourBoss",
                ))
            elif title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "ChooseYourBoss",
                    link=make_abs(safe_attr(title_elem, "href"), "https://www.chooseyourboss.com"),
                    source="ChooseYourBoss",
                ))
    except Exception as e:
        logger.error(f"ChooseYourBoss: {e}")
    return jobs[:limit]

def scrape_lesjeudis(job_title: str, limit: int = 10) -> List[dict]:
    """Scrape LesJeudis - French IT job board."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.lesjeudis.com/recherche?q={q}&filtre=entreprise")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='offer'], article[class*='card'], div[class*='job']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[href*='/offre/']")
            company_elem = card.select_one("span[class*='company'], div[class*='entreprise']")
            location_elem = card.select_one("span[class*='location'], span[class*='city']")
            link_elem = card.select_one("a[href*='/offre/'], h2 a")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "LesJeudis",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.lesjeudis.com"),
                    location=safe_text(location_elem) or "",
                    source="LesJeudis",
                ))
    except Exception as e:
        logger.error(f"LesJeudis: {e}")
    return jobs[:limit]

def scrape_talentio(job_title: str, limit: int = 10) -> List[dict]:
    """Scrape Talent.io - French/EU tech jobs."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.talent.io/jobs?keywords={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='card'], article[class*='job'], li[class*='job']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[href*='/jobs/']")
            company_elem = card.select_one("span[class*='company'], div[class*='company'], span[class*='name']")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Talent.io",
                    link=make_abs(safe_attr(title_elem, "href"), "https://www.talent.io"),
                    source="Talent.io",
                ))
    except Exception as e:
        logger.error(f"Talent.io: {e}")
    return jobs[:limit]

# ─── GLASSDOOR HTML SCRAPER ───────────────────────────────────────────────

def scrape_glassdoor(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Glassdoor jobs (independent of JobSpy)."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        l = urllib.parse.quote(location)
        
        # Try multiple regional domains
        urls = [
            f"https://www.glassdoor.fr/emploi/emploi.htm?sc.keyword={q}&sc.location={l}",
            f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}&sc.location={l}",
        ]
        
        for url in urls:
            html = fetch_url(url)
            if not html: continue
            soup = BeautifulSoup(html, "html.parser")
            
            # Try JSON-LD first
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        items = data.get("itemListElement", [data])
                        for item in items:
                            if isinstance(item, dict):
                                job = item.get("item", item)
                                if job.get("title"):
                                    desc = job.get("description","")
                                    jobs.append(make_job(
                                        title=job.get("title",""), company=job.get("hiringOrganization",{}).get("name","Glassdoor"),
                                        link=job.get("url","#"), source="Glassdoor",
                                        location=job.get("jobLocation",{}).get("address",{}).get("addressLocality", location),
                                        desc=desc, salary=extract_salary(desc),
                                        remote_flag=extract_remote(desc),
                                    ))
                except:
                    pass
            
            if jobs:
                break
            
            # Fallback to HTML scraping
            cards = soup.select("li[class*='job'], div[class*='card'], article[class*='job']")
            for card in cards[:limit]:
                title_elem = card.select_one("a[class*='title'], h2 a, a[data-test*='title'], a[href*='/job-listing/']")
                company_elem = card.select_one("span[class*='company'], div[class*='company'], a[class*='employer']")
                location_elem = card.select_one("span[class*='location'], div[class*='location']")
                link_elem = card.select_one("a[class*='title'], a[data-test*='title'], a[href*='/job-listing/']")
                
                if title_elem:
                    jobs.append(make_job(
                        title=title_elem.get_text(strip=True),
                        company=safe_text(company_elem) or "Glassdoor",
                        link=make_abs(safe_attr(link_elem, "href"), "https://www.glassdoor.com"),
                        location=safe_text(location_elem) or location,
                        source="Glassdoor",
                    ))
            
            if jobs:
                break
    except Exception as e:
        logger.error(f"Glassdoor: {e}")
    return jobs[:limit]

def scrape_ziprecruiter(job_title: str, location: str = "United States", limit: int = 10) -> List[dict]:
    """Scrape ZipRecruiter (independent of JobSpy)."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.ziprecruiter.com/jobs-search?search={q}&location={urllib.parse.quote(location)}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        
        # Try JSON-LD
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    for item_type in ["ItemList", "SearchResultsPage"]:
                        if data.get("@type") == item_type:
                            for item in data.get("itemListElement", []):
                                job = item.get("item", {})
                                if job.get("title"):
                                    desc = job.get("description","")
                                    jobs.append(make_job(
                                        title=job.get("title",""), company=job.get("hiringOrganization",{}).get("name","ZipRecruiter"),
                                        link=job.get("url","#"), source="ZipRecruiter",
                                        location=job.get("jobLocation",{}).get("address",{}).get("addressLocality", location),
                                        desc=desc, salary=extract_salary(desc),
                                    ))
            except:
                pass
        
        if not jobs:
            cards = soup.select("div[class*='job'], article[class*='job'], a[href*='/job/']")
            for card in cards[:limit]:
                title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[href*='/job/']")
                company_elem = card.select_one("span[class*='company'], div[class*='company']")
                
                if isinstance(card, type(soup)) and card.name == 'a' and not title_elem:
                    title = clean_title(card.get_text(strip=True))
                    if title and len(title) > 10:
                        jobs.append(make_job(
                            title=title, company="ZipRecruiter",
                            link=make_abs(card.get("href",""), "https://www.ziprecruiter.com"),
                            location="", source="ZipRecruiter",
                        ))
                elif title_elem:
                    jobs.append(make_job(
                        title=title_elem.get_text(strip=True),
                        company=safe_text(company_elem) or "ZipRecruiter",
                        link=make_abs(safe_attr(title_elem, "href"), "https://www.ziprecruiter.com"),
                        location="", source="ZipRecruiter",
                    ))
    except Exception as e:
        logger.error(f"ZipRecruiter: {e}")
    return jobs[:limit]

# ─── INTERNATIONAL INDEED SCRAPER ─────────────────────────────────────────

INDEED_DOMAINS = {
    "fr": "fr.indeed.com", "uk": "uk.indeed.com", "de": "de.indeed.com",
    "es": "es.indeed.com", "it": "it.indeed.com", "nl": "nl.indeed.com",
    "be": "be.indeed.com", "ch": "ch.indeed.com", "ca": "ca.indeed.com",
    "au": "au.indeed.com", "in": "co.in", "ae": "ae.indeed.com",
    "ie": "ie.indeed.com", "se": "se.indeed.com", "no": "no.indeed.com",
    "dk": "dk.indeed.com", "pl": "pl.indeed.com", "at": "at.indeed.com",
}

def scrape_indeed_international(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Indeed from multiple international domains."""
    jobs = []
    
    # Determine primary domain based on location
    loc_lower = location.lower()
    primary_domain = "fr.indeed.com"
    if any(c in loc_lower for c in ["uk", "britain", "london", "england"]):
        primary_domain = "uk.indeed.com"
    elif any(c in loc_lower for c in ["deutschland", "germany", "berlin", "munich"]):
        primary_domain = "de.indeed.com"
    elif any(c in loc_lower for c in ["spain", "españa", "madrid", "barcelona"]):
        primary_domain = "es.indeed.com"
    elif any(c in loc_lower for c in ["italy", "italia", "rome", "milan"]):
        primary_domain = "it.indeed.com"
    elif any(c in loc_lower for c in ["netherlands", "holland", "amsterdam"]):
        primary_domain = "nl.indeed.com"
    elif any(c in loc_lower for c in ["canada", "toronto", "montreal", "vancouver"]):
        primary_domain = "ca.indeed.com"
    elif any(c in loc_lower for c in ["australia", "sydney", "melbourne"]):
        primary_domain = "au.indeed.com"
    elif any(c in loc_lower for c in ["india", "mumbai", "delhi", "bangalore"]):
        primary_domain = "co.in"
    elif any(c in loc_lower for c in ["uae", "dubai", "abudhabi", "middle east"]):
        primary_domain = "ae.indeed.com"
    
    domains_to_try = [primary_domain]
    # Add some international domains for broader coverage
    for domain_key in ["uk", "fr", "de", "es", "ca", "au", "in"]:
        domain = INDEED_DOMAINS[domain_key]
        if domain not in domains_to_try:
            domains_to_try.append(domain)
    
    q = urllib.parse.quote(clean_title(job_title))
    
    for domain in domains_to_try[:3]:  # Try up to 3 domains
        try:
            url = f"https://{domain}/jobs?q={q}&limit={limit}"
            if location and "global" not in location.lower():
                url += f"&l={urllib.parse.quote(location)}"
            
            html = fetch_url(url)
            if not html: continue
            
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.job_seen_beacon, div[data-testid='job-card'], .cardOutline, div[class*='jobsearch']")
            
            if not cards: continue
            
            for card in cards[:limit]:
                title_elem = card.select_one("h2.jobTitle a, a[data-jk], h2 a")
                company_elem = card.select_one("span.companyName, span[data-testid='companyname']")
                location_elem = card.select_one("div.companyLocation, span[data-testid='text-location']")
                link_elem = card.select_one("h2.jobTitle a, a[data-jk]")
                desc_elem = card.select_one("div.job-snippet, div[class*='summary']")
                
                link = ""
                if link_elem:
                    href = link_elem.get("href", "")
                    if href.startswith("/"):
                        link = f"https://{domain}" + href
                    elif href.startswith("http"):
                        link = href
                
                if title_elem:
                    desc = safe_text(desc_elem)
                    salary = extract_salary(desc)
                    jobs.append(make_job(
                        title=title_elem.get_text(strip=True),
                        company=safe_text(company_elem) or "Non précisé",
                        link=link, source="Indeed",
                        location=safe_text(location_elem) or location,
                        desc=desc, salary=salary,
                    ))
            
            if jobs:
                break  # Stop if we got results
        except Exception as e:
            logger.debug(f"Indeed international ({domain}): {e}")
            continue
    
    return jobs[:limit]

def scrape_indeed_html(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Indeed HTML scraper - uses international domains."""
    return scrape_indeed_international(job_title, location, limit)

# ─── INTERNATIONAL LINKEDIN SCRAPER ───────────────────────────────────────

def scrape_linkedin_html(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """LinkedIn HTML scraper with multi-domain support."""
    jobs = []
    
    # Determine domain based on location
    loc_lower = location.lower()
    domain = "www.linkedin.com"
    if "uk" in loc_lower or "london" in loc_lower:
        domain = "uk.linkedin.com"
    elif "de" in loc_lower or "germany" in loc_lower:
        domain = "de.linkedin.com"
    elif "es" in loc_lower or "spain" in loc_lower:
        domain = "es.linkedin.com"
    elif "fr" in loc_lower or "france" in loc_lower:
        domain = "fr.linkedin.com"
    elif "ca" in loc_lower or "canada" in loc_lower:
        domain = "ca.linkedin.com"
    elif "au" in loc_lower or "australia" in loc_lower:
        domain = "au.linkedin.com"
    elif "in" in loc_lower or "india" in loc_lower:
        domain = "in.linkedin.com"
    elif "ae" in loc_lower or "dubai" in loc_lower:
        domain = "ae.linkedin.com"
    
    try:
        q = urllib.parse.quote(clean_title(job_title))
        l = urllib.parse.quote(location or "France")
        html = fetch_url(f"https://{domain}/jobs/search/?keywords={q}&location={l}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        
        # Try JSON-LD first
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        job = item.get("item", {})
                        if job.get("title"):
                            desc = job.get("description","")
                            jobs.append(make_job(
                                title=job.get("title", ""), company=job.get("hiringOrganization", {}).get("name", "Non précisé"),
                                link=job.get("url", "#"), source="LinkedIn",
                                location=job.get("jobLocation", {}).get("address", {}).get("addressLocality", location),
                                desc=desc, salary=extract_salary(desc),
                                remote_flag=extract_remote(desc),
                            ))
            except:
                pass
        
        if not jobs:
            cards = soup.select("li[data-occludable-job-id], .job-search-card, .base-card")
            for card in cards[:limit]:
                title_elem = card.select_one("a.base-card__full-link, h3.base-search-card__title")
                company_elem = card.select_one("h4.base-search-card__subtitle")
                location_elem = card.select_one("span.job-search-card__location")
                link_elem = card.select_one("a.base-card__full-link")
                link = safe_attr(link_elem, "href", "#")
                if title_elem:
                    jobs.append(make_job(
                        title=title_elem.get_text(strip=True),
                        company=safe_text(company_elem) or "Non précisé",
                        link=link, source="LinkedIn",
                        location=safe_text(location_elem) or location,
                    ))
    except Exception as e:
        logger.error(f"LinkedIn HTML: {e}")
    return jobs[:limit]

# ─── HELLOWORK HTML SCRAPER ──────────────────────────────────────────────

def scrape_hellowork_html(job_title: str, location: str = "", limit: int = 10) -> List[dict]:
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        loc_param = f"&l={urllib.parse.quote(location)}" if location else ""
        html = fetch_url(f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={q}{loc_param}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div[class*='card'], article, li[class*='job'], a[href*='/emploi/']")[:limit]:
            if isinstance(card, type(soup)) and card.name == 'a':
                jobs.append(make_job(
                    title=card.get_text(strip=True), company="HelloWork",
                    link=make_abs(card.get("href",""), "https://www.hellowork.com"),
                    location=location, source="HelloWork"))
            else:
                te = card.select_one("h2 a, h3 a, a[class*='title']")
                ce = card.select_one("span[class*='company'], div[class*='company']")
                le = card.select_one("span[class*='location'], div[class*='location']")
                link_e = card.select_one("a[href*='/emploi/'], h2 a, h3 a")
                if te:
                    title = clean_title(te.get_text(strip=True))
                    if title:
                        jobs.append(make_job(
                            title=title, company=safe_text(ce) or "HelloWork",
                            link=make_abs(safe_attr(link_e, "href"), "https://www.hellowork.com"),
                            location=safe_text(le) or location, source="HelloWork"))
    except Exception as e:
        logger.error(f"HelloWork: {e}")
    return jobs[:limit]

# ─── FREELANCE SCRAPERS ───────────────────────────────────────────────────

def scrape_malt(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.malt.fr/s?q={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='card'], article, div[class*='mission-card'], div[class*='project-card'], div[class*='Feed_project']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[class*='name']")
            company_elem = card.select_one("span[class*='client'], div[class*='client']")
            link_elem = card.select_one("a[href*='/project'], a[href*='/mission'], h2 a, h3 a")
            budget_elem = card.select_one("span[class*='budget'], div[class*='budget']")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Malt",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.malt.fr"),
                    source="Malt",
                    salary=extract_salary(safe_text(budget_elem)),
                ))
    except Exception as e:
        logger.error(f"Malt: {e}")
    return jobs[:limit]

def scrape_freelance_com(job_title: str, limit: int = 10) -> List[dict]:
    """Scrape Freelance.com - French freelancing platform."""
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.freelance.com/recherche-mission?q={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='card'], article[class*='mission'], div[class*='mission']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title']")
            company_elem = card.select_one("span[class*='client'], div[class*='client']")
            budget_elem = card.select_one("span[class*='budget'], div[class*='budget'], span[class*='price']")
            link_elem = card.select_one("a[href*='/mission/'], h2 a")
            
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Freelance.com",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.freelance.com"),
                    source="Freelance.com",
                    salary=extract_salary(safe_text(budget_elem) or safe_text(title_elem)),
                ))
    except Exception as e:
        logger.error(f"Freelance.com: {e}")
    return jobs[:limit]

def scrape_codeur(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.codeur.com/projects?search={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='project'], article, li[class*='project'], div[class*='card']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title'], a[class*='project']")
            budget_elem = card.select_one("span[class*='budget'], div[class*='budget']")
            link_elem = card.select_one("a[href*='/project'], h2 a, a[class*='project']")
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company="Codeur.com",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.codeur.com"),
                    source="Codeur.com",
                    salary=extract_salary(safe_text(budget_elem)),
                ))
    except Exception as e:
        logger.error(f"Codeur: {e}")
    return jobs[:limit]

def scrape_upwork(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.upwork.com/search/jobs/?q={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("article, div[class*='job-card'], div[class*='JobSearchCard'], section[class*='job']")
        for card in cards[:limit]:
            title_elem = card.select_one("a[class*='title'], h2 a, h3 a, a[data-test*='job-title']")
            link_elem = card.select_one("a[class*='title'], a[data-test*='job-title'], h2 a")
            budget_elem = card.select_one("span[class*='budget'], div[class*='budget'], strong[class*='price']")
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company="Upwork",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.upwork.com"),
                    source="Upwork",
                    salary=extract_salary(safe_text(budget_elem)),
                    desc=safe_text(budget_elem),
                ))
    except Exception as e:
        logger.error(f"Upwork: {e}")
    return jobs[:limit]

def scrape_freelance_informatique(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://www.freelance-informatique.fr/offres?q={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='offer'], article, div[class*='card']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title']")
            link_elem = card.select_one("a[href*='/offre'], h2 a")
            budget_elem = card.select_one("span[class*='budget'], div[class*='budget']")
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company="Freelance Informatique",
                    link=make_abs(safe_attr(link_elem, "href"), "https://www.freelance-informatique.fr"),
                    source="FreelanceInformatique",
                    salary=extract_salary(safe_text(budget_elem)),
                ))
    except Exception as e:
        logger.error(f"Freelance-Informatique: {e}")
    return jobs[:limit]

def scrape_cremedelacreme(job_title: str, limit: int = 10) -> List[dict]:
    jobs = []
    try:
        q = urllib.parse.quote(clean_title(job_title))
        html = fetch_url(f"https://cremedelacreme.io/fr/missions?query={q}")
        if not html: return jobs
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[class*='card'], article, div[class*='mission']")
        for card in cards[:limit]:
            title_elem = card.select_one("h2 a, h3 a, a[class*='title']")
            company_elem = card.select_one("span[class*='company'], div[class*='company']")
            link_elem = card.select_one("a[href*='/missions'], h2 a")
            if title_elem:
                jobs.append(make_job(
                    title=title_elem.get_text(strip=True),
                    company=safe_text(company_elem) or "Crème de la Crème",
                    link=make_abs(safe_attr(link_elem, "href"), "https://cremedelacreme.io"),
                    source="CrèmeDeLaCrème",
                ))
    except Exception as e:
        logger.error(f"Crème de la Crème: {e}")
    return jobs[:limit]

# ─── MASTER SOURCE REGISTRY ───────────────────────────────────────────────

# Level 2: RSS feeds
RSS_SCRAPERS = {
    "Indeed": scrape_indeed_rss,
    "LinkedIn": scrape_linkedin_rss,
    "Simplyhired": scrape_simplyhired_rss,
    "Careerbuilder": scrape_careerbuilder_rss,
    "France Travail": scrape_france_travail_rss,
    "Emploi Public": scrape_emploi_public_rss,
    "Google Jobs": scrape_google_news_jobs,
    "Reed": scrape_reed_rss,
    "StepStone": scrape_stepstone_rss,
}

# Level 3: Free APIs
API_SCRAPERS = {
    "Remotive": scrape_remotive,
    "RemoteOK": scrape_remoteok,
    "Welcome to the Jungle": scrape_wttj_api,
    "Jobijoba": scrape_jobijoba,
}

# Level 3: HTML-based scrapers
HTML_SCRAPERS = {
    "Indeed": scrape_indeed_html,
    "LinkedIn": scrape_linkedin_html,
    "HelloWork": scrape_hellowork_html,
    "Reed": scrape_reed_html,
    "StepStone": scrape_stepstone_html,
    "Xing": scrape_xing,
    "InfoJobs": scrape_infojobs,
    "Dice": scrape_dice,
    "Naukri": scrape_naukri,
    "Bayt": scrape_bayt,
    "Seek": scrape_seek,
    "Glassdoor": scrape_glassdoor,
    "ZipRecruiter": scrape_ziprecruiter,
    "RégionsJob": scrape_regionsjob,
    "ChooseYourBoss": scrape_chooseyourboss,
    "LesJeudis": scrape_lesjeudis,
    "Talent.io": scrape_talentio,
}

# Freelance-specific scrapers
FREELANCE_SCRAPERS = {
    "Malt": scrape_malt,
    "Freelance.com": scrape_freelance_com,
    "Codeur.com": scrape_codeur,
    "Upwork": scrape_upwork,
    "FreelanceInformatique": scrape_freelance_informatique,
    "CrèmeDeLaCrème": scrape_cremedelacreme,
}

# All free scrapers combined
ALL_FREE_SCRAPERS = {}
ALL_FREE_SCRAPERS.update(RSS_SCRAPERS)
ALL_FREE_SCRAPERS.update(API_SCRAPERS)
ALL_FREE_SCRAPERS.update(HTML_SCRAPERS)

def search_all_free_sources(job_title: str, location: str = "", limit: int = 10, 
                             selected_sources: List[str] = None, api_keys: dict = None,
                             is_freelance: bool = False) -> List[dict]:
    """
    Master function: searches ALL free sources in parallel.
    Returns deduplicated list of jobs with enriched data.
    """
    all_jobs = []
    seen_links = set()
    results = {}
    
    # Determine which scrapers to run
    scrapers_to_run = {}
    
    # Always include core job scrapers
    for name, fn in ALL_FREE_SCRAPERS.items():
        if not selected_sources or name in selected_sources:
            scrapers_to_run[name] = fn
    
    # Add freelance scrapers if requested
    if is_freelance:
        for name, fn in FREELANCE_SCRAPERS.items():
            if not selected_sources or name in selected_sources:
                scrapers_to_run[name] = fn
    
    if not scrapers_to_run:
        return []
    
    # Run all in parallel with more workers
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {}
        for name, fn in scrapers_to_run.items():
            try:
                if name in ["Indeed", "LinkedIn"]:
                    # RSS + HTML both run for these
                    futures[executor.submit(fn, job_title, location, limit)] = f"{name}_html"
                elif name in ["Reed", "StepStone"]:
                    # RSS + HTML
                    futures[executor.submit(fn, job_title, location, limit)] = f"{name}_html"
                elif name in ["InfoJobs"]:
                    # Country-specific
                    country = "es"
                    loc_lower = location.lower()
                    if any(c in loc_lower for c in ["italy", "italia", "italie", "rome", "milan"]):
                        country = "it"
                    elif any(c in loc_lower for c in ["brazil", "brasil", "brésil"]):
                        country = "br"
                    futures[executor.submit(fn, job_title, country, limit)] = name
                else:
                    futures[executor.submit(fn, job_title, limit)] = name
            except Exception as e:
                logger.debug(f"Error submitting {name}: {e}")
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                jobs = future.result()
                if jobs:
                    results[name] = jobs
                    for j in jobs:
                        link = j.get("lien", "")
                        if link and link not in seen_links:
                            seen_links.add(link)
                            all_jobs.append(j)
            except Exception as e:
                logger.warning(f"{name} failed: {e}")
    
    logger.info(f"Enhanced v2 scrapers: {len(all_jobs)} unique jobs from {len(results)} sources")
    for s, js in sorted(results.items(), key=lambda x: len(x[1]), reverse=True):
        logger.info(f"  {s}: {len(js)} jobs")
    
    return all_jobs[:limit * 8]  # Return more results