"""
Playwright-based scrapers for JavaScript-rendered job sites.
These scrapers bypass anti-bot detection by using a real browser engine,
executing JavaScript, and applying stealth techniques.

Used as a fallback when the requests-based scrapers fail (which is common
on sites like Indeed, Monster, Careerbuilder, Simplyhired that now use
Cloudflare/WAF and JS-rendered content).
"""

import logging
import time
import json
import urllib.parse
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Playwright is imported lazily so the backend still works if it's not installed
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
    logger.info("✅ Playwright available for JS-rendered scraping")
except ImportError:
    logger.warning("⚠️ Playwright not installed. JS-rendered scrapers will be disabled.")
    logger.warning("  Install with: pip install playwright && playwright install chromium")


def _get_browser_context(playwright, headless=True):
    """Create a stealth-configured browser context."""
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
        ],
    )

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        java_script_enabled=True,
        accept_downloads=False,
        bypass_csp=True,
    )

    # Inject stealth scripts to avoid detection
    try:
        context.add_init_script("""
            // Overwrite the `languages` property to return a consistent value
            Object.defineProperty(navigator, 'languages', {
                get: () => ['fr-FR', 'fr', 'en-US', 'en'],
            });
            // Overwrite the `plugins` property to return a non-empty array
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            // Overwrite the `webdriver` property to be undefined
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            // Overwrite the `permissions' property to avoid errors
            if (window.matchMedia === undefined) {
                window.matchMedia = window.matchMedia || function() {
                    return {
                        matches: false,
                        addListener: function() {},
                        removeListener: function() {}
                    };
                };
            }
        """)
    except Exception as e:
        logger.debug(f"Stealth script injection warning: {e}")

    return browser, context


def _extract_jobs_from_page(page, source_name: str, selectors: dict, limit: int) -> List[dict]:
    """
    Generic job extraction from a Playwright page using configurable selectors.
    Returns a list of job dicts.
    """
    jobs = []
    try:
        # Wait for job cards to appear
        page.wait_for_selector(selectors["card"], timeout=15000, state="visible")
    except PlaywrightTimeoutError:
        logger.warning(f"[{source_name}] No job cards found with selector: {selectors['card']}")
        # Try to extract from any links that look like job postings
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass

    try:
        cards = page.query_selector_all(selectors["card"])
    except:
        cards = []

    if not cards:
        # Fallback: try alternative selectors
        for alt_selector in selectors.get("alt_cards", []):
            try:
                cards = page.query_selector_all(alt_selector)
                if cards:
                    logger.info(f"[{source_name}] Found {len(cards)} cards with alt selector: {alt_selector}")
                    break
            except:
                continue

    for card in cards[:limit * 2]:  # Get extra to account for duplicates
        try:
            title_elem = card.query_selector(selectors["title"]) if selectors.get("title") else None
            company_elem = card.query_selector(selectors["company"]) if selectors.get("company") else None
            location_elem = card.query_selector(selectors["location"]) if selectors.get("location") else None
            link_elem = card.query_selector(selectors["link"]) if selectors.get("link") else None

            title = title_elem.inner_text().strip() if title_elem else ""
            company = company_elem.inner_text().strip() if company_elem else "Non précisé"
            location = location_elem.inner_text().strip() if location_elem else ""

            link = "#"
            if link_elem:
                href = link_elem.get_attribute("href") or ""
                if href:
                    if href.startswith("http"):
                        link = href
                    elif href.startswith("/"):
                        link = urllib.parse.urljoin(selectors.get("base_url", ""), href)
                    else:
                        link = href

            if title:
                jobs.append({
                    "titre": title,
                    "entreprise": company,
                    "lien": link,
                    "location": location,
                    "date": "",
                    "source": source_name,
                })
        except Exception as e:
            logger.debug(f"[{source_name}] Error extracting card: {e}")
            continue

    return jobs[:limit]


def scrape_indeed_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Indeed using Playwright to bypass bot detection."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://fr.indeed.com/jobs?q={query}&l={loc}&limit={limit * 2}"
            logger.info(f"[Indeed-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to load
            time.sleep(2)

            selectors = {
                "card": "div.job_seen_beacon, .jobsearch-SerpJobCard, div[data-testid='job-card']",
                "alt_cards": ["div[class*='jobsearch-SerpJobCard']", "div[data-jk]", "a[data-jk]"],
                "title": "h2.jobTitle a, a.jobtitle, h2 a",
                "company": "span.companyName, .company, span[data-testid='companyname']",
                "location": "div.companyLocation, span[data-testid='text-location'], .location",
                "link": "h2.jobTitle a, a.jobtitle, a[data-jk]",
                "base_url": "https://fr.indeed.com",
            }

            jobs = _extract_jobs_from_page(page, "Indeed", selectors, limit)
            logger.info(f"[Indeed-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[Indeed-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_monster_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Monster using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.monster.fr/emploi/recherche?q={query}&where={loc}"
            logger.info(f"[Monster-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            selectors = {
                "card": "div[class*='card'], section[class*='card'], .job-row, article",
                "alt_cards": ["div[data-job-id]", "a[data-testid='jobTitle']", "div[class*='jobCard']"],
                "title": "h2 a, h3 a, a[data-testid='jobTitle'], a[class*='title']",
                "company": "span[class*='company'], div[class*='company'], span[data-testid='company']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "h2 a, h3 a, a[data-testid='jobTitle']",
                "base_url": "https://www.monster.fr",
            }

            jobs = _extract_jobs_from_page(page, "Monster", selectors, limit)
            logger.info(f"[Monster-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[Monster-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_careerbuilder_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Careerbuilder using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.careerbuilder.com/jobs?q={query}&location={loc}"
            logger.info(f"[Careerbuilder-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            selectors = {
                "card": "div[data-job-id], div.job-row, article, div[class*='job']",
                "alt_cards": ["div[class*='JobCard']", "div[class*='card']", "li[class*='job']"],
                "title": "a[data-job-id], a.job-title, h2 a, h3 a",
                "company": "span[class*='company'], div[class*='company']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "a[data-job-id], a.job-title, h2 a",
                "base_url": "https://www.careerbuilder.com",
            }

            jobs = _extract_jobs_from_page(page, "Careerbuilder", selectors, limit)
            logger.info(f"[Careerbuilder-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[Careerbuilder-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_simplyhired_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Simplyhired using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.simplyhired.com/search?q={query}&l={loc}"
            logger.info(f"[Simplyhired-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            selectors = {
                "card": "div[class*='card'], div.job, article, div[class*='SerpJob']",
                "alt_cards": ["div[class*='jobCard']", "div[class*='JobCard']", "div[data-jobid]"],
                "title": "a[class*='title'], h2 a, h3 a, a[class*='jobTitle']",
                "company": "span[class*='company'], div[class*='company']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "a[class*='title'], h2 a, a[class*='jobTitle']",
                "base_url": "https://www.simplyhired.com",
            }

            jobs = _extract_jobs_from_page(page, "Simplyhired", selectors, limit)
            logger.info(f"[Simplyhired-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[Simplyhired-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_linkedin_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape LinkedIn jobs using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc}"
            logger.info(f"[LinkedIn-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Try JSON-LD first (more reliable)
            scripts = page.query_selector_all("script[type='application/ld+json']")
            for script in scripts:
                try:
                    data = json.loads(script.inner_text())
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        for item in data.get("itemListElement", []):
                            job = item.get("item", {})
                            if job.get("title"):
                                jobs.append({
                                    "titre": job.get("title"),
                                    "entreprise": job.get("hiringOrganization", {}).get("name", "Non précisé"),
                                    "lien": job.get("url", "#"),
                                    "location": job.get("jobLocation", {}).get("address", {}).get("addressLocality", location),
                                    "date": "",
                                    "source": "LinkedIn",
                                })
                except:
                    pass

            # Fallback to card scraping
            if not jobs:
                selectors = {
                    "card": "li[data-occludable-job-id], .job-search-card, .base-card",
                    "alt_cards": ["div[class*='job-card']", "a[href*='/jobs/view']"],
                    "title": "a.base-card__full-link, h3.base-search-card__title, a[href*='/jobs/view']",
                    "company": "h4.base-search-card__subtitle, a[data-tracking-control-name*='company']",
                    "location": "span.job-search-card__location, span[class*='location']",
                    "link": "a.base-card__full-link",
                    "base_url": "https://www.linkedin.com",
                }
                jobs = _extract_jobs_from_page(page, "LinkedIn", selectors, limit)

            logger.info(f"[LinkedIn-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[LinkedIn-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_welcometothejungle(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Welcome to the Jungle using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            # Try French site first, then English
            urls = [
                f"https://www.welcometothejungle.com/fr/jobs?query={query}&location={loc}",
                f"https://www.welcometothejungle.com/jobs?query={query}&location={loc}",
            ]
            for url in urls:
                logger.info(f"[WTTJ-PW] Navigating to: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                # Try API endpoint first
                try:
                    api_url = f"https://www.welcometothejungle.com/api/v1/jobs?search%5Bquery%5D={query}&search%5Blocation%5D={loc}&per_page={limit * 2}"
                    response = page.request.get(api_url, timeout=15000)
                    if response.status == 200:
                        data = response.json()
                        for item in data.get("jobs", [])[:limit * 2]:
                            title = item.get("title", "")
                            if title:
                                jobs.append({
                                    "titre": title,
                                    "entreprise": item.get("company", {}).get("name", "Non précisé"),
                                    "lien": f"https://www.welcometothejungle.com/fr/jobs/{item.get('id', '')}",
                                    "location": item.get("location", {}).get("city", location),
                                    "date": "",
                                    "source": "Welcome to the Jungle",
                                })
                        if jobs:
                            logger.info(f"[WTTJ-PW] Extracted {len(jobs)} jobs via API")
                            break
                except Exception as e:
                    logger.debug(f"[WTTJ-PW] API attempt failed: {e}")

                # Fallback to scraping
                selectors = {
                    "card": "div[class*='card'], article, div[class*='job-card'], div[class*='mission-card']",
                    "alt_cards": ["a[href*='/jobs/']", "div[data-testid='card']"],
                    "title": "h2 a, h3 a, a[class*='title'], a[href*='/jobs/']",
                    "company": "span[class*='company'], div[class*='company'], p[class*='company']",
                    "location": "span[class*='location'], div[class*='location'], p[class*='location']",
                    "link": "a[href*='/jobs/'], h2 a, h3 a",
                    "base_url": "https://www.welcometothejungle.com",
                }
                jobs = _extract_jobs_from_page(page, "Welcome to the Jungle", selectors, limit)
                if jobs:
                    logger.info(f"[WTTJ-PW] Extracted {len(jobs)} jobs via scraping")
                    break

        except Exception as e:
            logger.error(f"[WTTJ-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_hellowork(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape HelloWork using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={query}&l={loc}"
            logger.info(f"[HelloWork-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Try API endpoint
            try:
                api_url = f"https://api.hellowork.com/v1/jobs?search={query}&location={loc}&limit={limit * 2}"
                response = page.request.get(api_url, timeout=15000)
                if response.status == 200:
                    data = response.json()
                    for item in data.get("jobs", [])[:limit * 2]:
                        title = item.get("title", "")
                        if title:
                            jobs.append({
                                "titre": title,
                                "entreprise": item.get("companyName", "Non précisé"),
                                "lien": f"https://www.hellowork.com/fr-fr/emploi/{item.get('id', '')}.htm",
                                "location": item.get("location", location),
                                "date": "",
                                "source": "HelloWork",
                            })
                    if jobs:
                        logger.info(f"[HelloWork-PW] Extracted {len(jobs)} jobs via API")
            except Exception as e:
                logger.debug(f"[HelloWork-PW] API attempt failed: {e}")

            # Fallback to scraping
            if not jobs:
                selectors = {
                    "card": "div[class*='card'], article, div[class*='job-card'], li[class*='job']",
                    "alt_cards": ["a[href*='/emploi/']", "div[data-testid='card']", "div[class*='result']"],
                    "title": "h2 a, h3 a, a[class*='title'], a[href*='/emploi/']",
                    "company": "span[class*='company'], div[class*='company'], p[class*='company']",
                    "location": "span[class*='location'], div[class*='location'], p[class*='location']",
                    "link": "a[href*='/emploi/'], h2 a, h3 a",
                    "base_url": "https://www.hellowork.com",
                }
                jobs = _extract_jobs_from_page(page, "HelloWork", selectors, limit)
                logger.info(f"[HelloWork-PW] Extracted {len(jobs)} jobs via scraping")

        except Exception as e:
            logger.error(f"[HelloWork-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_apec(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape APEC (executive jobs) using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.apec.fr/offres-d-emploi-cadre/recherche.html?motsCles={query}&lieux={location}"
            logger.info(f"[APEC-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            selectors = {
                "card": "div[class*='card'], article, div[class*='job-card'], li[class*='job']",
                "alt_cards": ["a[href*='/offre/']", "div[data-testid='card']"],
                "title": "h2 a, h3 a, a[class*='title'], a[href*='/offre/']",
                "company": "span[class*='company'], div[class*='company'], p[class*='company']",
                "location": "span[class*='location'], div[class*='location'], p[class*='location']",
                "link": "a[href*='/offre/'], h2 a, h3 a",
                "base_url": "https://www.apec.fr",
            }
            jobs = _extract_jobs_from_page(page, "APEC", selectors, limit)
            logger.info(f"[APEC-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[APEC-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_jobteaser(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape JobTeaser using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.jobteaser.com/fr/jobs?query={query}"
            logger.info(f"[JobTeaser-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            selectors = {
                "card": "div[class*='card'], article, div[class*='job-card'], li[class*='job']",
                "alt_cards": ["a[href*='/jobs/']", "div[data-testid='card']"],
                "title": "h2 a, h3 a, a[class*='title'], a[href*='/jobs/']",
                "company": "span[class*='company'], div[class*='company'], p[class*='company']",
                "location": "span[class*='location'], div[class*='location'], p[class*='location']",
                "link": "a[href*='/jobs/'], h2 a, h3 a",
                "base_url": "https://www.jobteaser.com",
            }
            jobs = _extract_jobs_from_page(page, "JobTeaser", selectors, limit)
            logger.info(f"[JobTeaser-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[JobTeaser-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


# ─── Convenience: Run all Playwright scrapers for a given query ────────────────

def scrape_all_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """
    Run all Playwright-based scrapers and return combined, deduplicated results.
    This is used as a comprehensive fallback when requests-based scrapers fail.
    """
    all_jobs = []

    scrapers = [
        ("Indeed", scrape_indeed_playwright),
        ("Monster", scrape_monster_playwright),
        ("Careerbuilder", scrape_careerbuilder_playwright),
        ("Simplyhired", scrape_simplyhired_playwright),
        ("LinkedIn", scrape_linkedin_playwright),
        ("Welcome to the Jungle", scrape_welcometothejungle),
        ("HelloWork", scrape_hellowork),
        ("APEC", scrape_apec),
        ("JobTeaser", scrape_jobteaser),
    ]

    for name, scraper_fn in scrapers:
        try:
            jobs = scraper_fn(job_title, location, limit)
            if jobs:
                logger.info(f"[Playwright] {name}: {len(jobs)} jobs")
                all_jobs.extend(jobs)
        except Exception as e:
            logger.warning(f"[Playwright] {name} failed: {e}")

    # Deduplicate by link
    seen_links = set()
    unique_jobs = []
    for job in all_jobs:
        link = job.get("lien", "") or job.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            unique_jobs.append(job)

    logger.info(f"[Playwright] Total unique jobs: {len(unique_jobs)}")
    return unique_jobs[:limit * 3]  # Return up to 3x the limit

