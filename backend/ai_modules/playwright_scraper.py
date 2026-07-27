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
import os
import random
import sys
import re
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

sys_path_added = False
if not sys_path_added:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys_path_added = True


def clean_job_title(title: str) -> str:
    if not title:
        return ""
    if isinstance(title, list):
        title = " ".join(map(str, title))
    clean = title.lower()
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()


try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
    logger.info("✅ Playwright available for JS-rendered scraping")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
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


def _extract_jobs_with_scroll(page, source_name: str, selectors: dict, limit: int, seen_links: set) -> List[dict]:
    """
    Extract jobs with auto-scroll to load more content.
    Used for LinkedIn infinite scroll pages.
    """
    jobs = []
    scroll_pause = 2.0
    max_scrolls = 10
    no_new_jobs_count = 0
    max_no_new = 3

    for scroll in range(max_scrolls):
        # Extract jobs from current view
        new_jobs = _extract_jobs_from_page(page, source_name, selectors, limit * 2)
        
        # Add only new jobs
        added = 0
        for job in new_jobs:
            link = job.get("lien", "")
            if link and link not in seen_links:
                seen_links.add(link)
                jobs.append(job)
                added += 1
        
        logger.info(f"[{source_name}] Scroll {scroll + 1}: extracted {len(new_jobs)} jobs, {added} new, total: {len(jobs)}")
        
        if len(jobs) >= limit:
            logger.info(f"[{source_name}] Reached limit of {limit} jobs")
            break
        
        if added == 0:
            no_new_jobs_count += 1
            if no_new_jobs_count >= max_no_new:
                logger.info(f"[{source_name}] No new jobs after {max_no_new} scrolls, stopping")
                break
        else:
            no_new_jobs_count = 0

        # Scroll down
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        time.sleep(scroll_pause)

        # Try to click "Voir plus" / "Load more" / "Show more" buttons
        load_more_selectors = [
            "button:has-text('Voir plus')",
            "button:has-text('Show more')",
            "button:has-text('Load more')",
            "button[aria-label='Voir plus']",
            "button[aria-label='Show more']",
            "button[data-control-name='infinite_scroll_show_more']",
            ".infinite-scroller__show-more-button",
            "button.artdeco-button--primary",
        ]
        
        clicked = False
        for btn_selector in load_more_selectors:
            try:
                btn = page.query_selector(btn_selector)
                if btn and btn.is_visible():
                    btn.click()
                    logger.info(f"[{source_name}] Clicked load more button: {btn_selector}")
                    time.sleep(2)
                    clicked = True
                    break
            except:
                continue
        
        if not clicked and scroll == 0:
            # If no button found and first scroll, try pagination
            try:
                next_btn = page.query_selector("button[aria-label='Suivant'], button[aria-label='Next']")
                if next_btn and next_btn.is_visible():
                    next_btn.click()
                    logger.info(f"[{source_name}] Clicked next page button")
                    time.sleep(3)
            except:
                pass

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


def scrape_linkedin_playwright(job_title: str, location: str = "France", limit: int = 10, auto_scroll: bool = True) -> List[dict]:
    """Scrape LinkedIn jobs using Playwright with auto-scroll to load more jobs."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = job_title.replace("h/f", "").replace("H/F", "").strip()
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []
    seen_links = set()

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
                                link = job.get("url", "#")
                                if link not in seen_links:
                                    seen_links.add(link)
                                    jobs.append({
                                        "titre": job.get("title"),
                                        "entreprise": job.get("hiringOrganization", {}).get("name", "Non précisé"),
                                        "lien": link,
                                        "location": job.get("jobLocation", {}).get("address", {}).get("addressLocality", location),
                                        "date": "",
                                        "source": "LinkedIn",
                                    })
                except:
                    pass

            # Fallback to card scraping with auto-scroll
            if not jobs or auto_scroll:
                selectors = {
                    "card": "li[data-occludable-job-id], .job-search-card, .base-card",
                    "alt_cards": ["div[class*='job-card']", "a[href*='/jobs/view']"],
                    "title": "a.base-card__full-link, h3.base-search-card__title, a[href*='/jobs/view']",
                    "company": "h4.base-search-card__subtitle, a[data-tracking-control-name*='company']",
                    "location": "span.job-search-card__location, span[class*='location']",
                    "link": "a.base-card__full-link",
                    "base_url": "https://www.linkedin.com",
                }
                
                if auto_scroll:
                    jobs = _extract_jobs_with_scroll(page, "LinkedIn", selectors, limit, seen_links)
                else:
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


def scrape_emploi_public(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Emploi Public (fonction publique) using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.choisirleservicepublic.gouv.fr/nos-offres/filtres/mots-cles/{query}/"
            logger.info(f"[EmploiPublic-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            selectors = {
                "card": "article[class*='offer'], div[class*='offer-card'], li[class*='result']",
                "alt_cards": ["a[href*='/offre/']", "div[class*='card']"],
                "title": "h2 a, h3 a, a[class*='title'], a[href*='/offre/']",
                "company": "span[class*='employer'], div[class*='employer'], p[class*='organization']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "a[href*='/offre/'], h2 a, h3 a",
                "base_url": "https://www.choisirleservicepublic.gouv.fr",
            }
            jobs = _extract_jobs_from_page(page, "Emploi Public", selectors, limit)
            logger.info(f"[EmploiPublic-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[EmploiPublic-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_regionsjob(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape RegionsJob using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.regionsjob.com/offres/emploi?motsCles={query}&lieu={loc}"
            logger.info(f"[RegionsJob-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            selectors = {
                "card": "div[class*='job'], article, div[class*='offer-card'], li[class*='result']",
                "alt_cards": ["a[href*='/offre/']", "div[class*='card']"],
                "title": "h2 a, h3 a, a[class*='title'], a[href*='/offre/']",
                "company": "span[class*='company'], div[class*='company']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "a[href*='/offre/'], h2 a, h3 a",
                "base_url": "https://www.regionsjob.com",
            }
            jobs = _extract_jobs_from_page(page, "RégionsJob", selectors, limit)
            logger.info(f"[RegionsJob-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[RegionsJob-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_chooseyourboss(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape ChooseYourBoss using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.chooseyourboss.com/jobs?q={query}&l={loc}"
            logger.info(f"[ChooseYourBoss-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            selectors = {
                "card": "div[class*='job'], article, div[class*='offer-card'], li[class*='result']",
                "alt_cards": ["a[href*='/jobs/']", "div[class*='card']"],
                "title": "h2 a, h3 a, a[class*='title'], a[href*='/jobs/']",
                "company": "span[class*='company'], div[class*='company']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "a[href*='/jobs/'], h2 a, h3 a",
                "base_url": "https://www.chooseyourboss.com",
            }
            jobs = _extract_jobs_from_page(page, "ChooseYourBoss", selectors, limit)
            logger.info(f"[ChooseYourBoss-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[ChooseYourBoss-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_lesjeudis(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape LesJeudis using Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []

    with sync_playwright() as p:
        browser, context = _get_browser_context(p)
        try:
            page = context.new_page()
            url = f"https://www.lesjeudis.com/jobs?search={query}&location={loc}"
            logger.info(f"[LesJeudis-PW] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            selectors = {
                "card": "div[class*='job'], article, div[class*='offer-card'], li[class*='result']",
                "alt_cards": ["a[href*='/jobs/']", "div[class*='card']"],
                "title": "h2 a, h3 a, a[class*='title'], a[href*='/jobs/']",
                "company": "span[class*='company'], div[class*='company']",
                "location": "span[class*='location'], div[class*='location']",
                "link": "a[href*='/jobs/'], h2 a, h3 a",
                "base_url": "https://www.lesjeudis.com",
            }
            jobs = _extract_jobs_from_page(page, "LesJeudis", selectors, limit)
            logger.info(f"[LesJeudis-PW] Extracted {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"[LesJeudis-PW] Error: {e}")
        finally:
            context.close()
            browser.close()

    return jobs[:limit]


def scrape_jooble_playwright(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Scrape Jooble using Playwright to bypass Cloudflare protection with proxy rotation."""
    if not PLAYWRIGHT_AVAILABLE:
        return []
    
    jobs = []
    
    # Get proxy configuration from environment
    proxy_url = os.getenv("PROXY_URL", "").strip()
    proxy_list_str = os.getenv("PROXY_LIST", "").strip()
    proxy_list = [p.strip() for p in proxy_list_str.split(",") if p.strip()] if proxy_list_str else []
    
    # Use PROXY_URL if set, otherwise pick random from PROXY_LIST
    selected_proxy = None
    if proxy_url:
        selected_proxy = proxy_url
        logger.info(f"[Playwright] Jooble: using proxy from PROXY_URL")
    elif proxy_list:
        selected_proxy = random.choice(proxy_list)
        logger.info(f"[Playwright] Jooble: using rotated proxy from PROXY_LIST ({len(proxy_list)} available)")
    
    try:
        with sync_playwright() as p:
            # Launch browser with stealth settings
            launch_args = [
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080",
            ]
            
            # Add proxy if configured
            if selected_proxy:
                launch_args.append(f"--proxy-server={selected_proxy}")
            
            browser = p.chromium.launch(
                headless=True, 
                args=launch_args
            )
            
            # Create context with realistic settings
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080},
                "locale": "fr-FR",
                "timezone_id": "Europe/Paris",
                "java_script_enabled": True,
                "accept_downloads": False,
                "bypass_csp": True,
            }
            
            # Add proxy to context if using authenticated proxy
            if selected_proxy and "@" in selected_proxy:
                # Format: http://user:pass@host:port
                context_args["proxy"] = {"server": selected_proxy.split("@")[1]}
                auth = selected_proxy.split("@")[0].split("://")[1]
                if ":" in auth:
                    context_args["proxy"]["username"] = auth.split(":")[0]
                    context_args["proxy"]["password"] = auth.split(":")[1]
            
            context = browser.new_context(**context_args)
            
            # Inject stealth scripts
            context.add_init_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['fr-FR', 'fr', 'en-US', 'en'],
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            page = context.new_page()
            
            # Try multiple Jooble URLs
            urls_to_try = [
                f"https://fr.jooble.org/jobs?keywords={urllib.parse.quote(job_title)}&location={urllib.parse.quote(location)}",
                f"https://jooble.org/jobs?keywords={urllib.parse.quote(job_title)}&location={urllib.parse.quote(location)}",
                f"https://fr.jooble.org/offres?keywords={urllib.parse.quote(job_title)}&location={urllib.parse.quote(location)}",
            ]
            
            for url in urls_to_try:
                try:
                    logger.info(f"[Playwright] Jooble: trying {url}")
                    
                    # Navigate with human-like behavior
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(2000)  # Wait for initial load
                    
                    # Simulate human scrolling
                    page.evaluate("window.scrollBy(0, 300)")
                    page.wait_for_timeout(1000)
                    page.evaluate("window.scrollBy(0, 300)")
                    page.wait_for_timeout(1000)
                    
                    # Try multiple selectors for job cards
                    selectors = [
                        'div[data-test="job-card"]',
                        '.job-card',
                        'article[class*="job"]',
                        'div[class*="JobCard"]',
                        'div[class*="job-listing"]',
                        'a[href*="/job/"]',
                        'a[href*="/offre/"]',
                    ]
                    
                    job_cards = []
                    for selector in selectors:
                        try:
                            cards = page.query_selector_all(selector)
                            if cards and len(cards) > len(job_cards):
                                job_cards = cards
                                logger.info(f"[Playwright] Jooble: found {len(cards)} cards with selector '{selector}'")
                                if len(job_cards) >= limit:
                                    break
                        except Exception:
                            continue
                    
                    if not job_cards:
                        # Try to extract from page content
                        logger.warning("[Playwright] Jooble: no job cards found, trying alternative extraction")
                        continue
                    
                    logger.info(f"[Playwright] Jooble: found {len(job_cards)} job cards")
                    
                    for card in job_cards[:limit]:
                        try:
                            # Try multiple selectors for each field
                            title_elem = card.query_selector('h2, h3, h4, [class*="title"], [class*="Title"]')
                            company_elem = card.query_selector('[class*="company"], [class*="employer"], [class*="Company"]')
                            link_elem = card.query_selector('a[href*="/job/"], a[href*="/offre/"], a[href*="/emploi/"]')
                            location_elem = card.query_selector('[class*="location"], [class*="region"], [class*="Location"]')
                            
                            title = title_elem.inner_text().strip() if title_elem else ""
                            company = company_elem.inner_text().strip() if company_elem else "N/C"
                            link = link_elem.get_attribute("href") if link_elem else ""
                            if link and not link.startswith("http"):
                                link = "https://fr.jooble.org" + link
                            location_text = location_elem.inner_text().strip() if location_elem else location
                            
                            if title:
                                jobs.append({
                                    "titre": title,
                                    "entreprise": company,
                                    "lien": link,
                                    "location": location_text,
                                    "date": "",
                                    "source": "Jooble"
                                })
                        except Exception as e:
                            logger.debug(f"[Playwright] Jooble: error parsing card: {e}")
                            continue
                    
                    if jobs:
                        logger.info(f"[Playwright] Jooble: successfully extracted {len(jobs)} jobs from {url}")
                        break
                        
                except Exception as e:
                    logger.warning(f"[Playwright] Jooble: failed with {url}: {e}")
                    continue
            
            browser.close()
            logger.info(f"[Playwright] Jooble: {len(jobs)} jobs extracted total")
            return jobs
            
    except Exception as e:
        logger.error(f"[Playwright] Jooble error: {e}")
        return jobs


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
        ("Jooble", scrape_jooble_playwright),
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

