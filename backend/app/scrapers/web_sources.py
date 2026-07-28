"""
Lightweight web scrapers for job sources
LinkedIn, Indeed, and other sites - Timeout 6s
"""

import json
import logging
import re
import asyncio
import urllib.parse
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebScraperSource:
    """
    Lightweight web scraper for job sites.
    Uses requests with 6s timeout.
    """
    
    # Browser-like headers
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
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
    
    TIMEOUT = 6  # seconds
    
    @staticmethod
    def clean_title(title: str) -> str:
        """Clean job title."""
        if not title:
            return ""
        clean = title.lower()
        clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
        clean = re.split(r'[,(\-:&/|]', clean)[0]
        return " ".join(clean.split()).capitalize()
    
    @staticmethod
    def clean_html(text: str) -> str:
        """Remove HTML tags from text."""
        try:
            return BeautifulSoup(text, "html.parser").get_text()
        except:
            return text
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page with timeout.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None
        """
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            logger.debug(f"Fetch error for {url[:60]}: {e}")
            return None


class LinkedInScraper(WebScraperSource):
    """Scraper for LinkedIn jobs."""
    
    def search(self, job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
        """
        Search LinkedIn for jobs.
        
        Args:
            job_title: Job title to search
            location: Location
            limit: Max results
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        clean_title = self.clean_title(job_title)
        query = urllib.parse.quote(clean_title)
        loc = urllib.parse.quote(location)
        logger.info(f"[WEB:LinkedIn] start query={job_title!r} location={location!r} limit={limit}")
        
        try:
            url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc}"
            html = self._fetch_page(url)
            if not html:
                logger.warning(f"[WEB:LinkedIn] empty page for {url[:120]}")
                return jobs
            
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('li[data-occludable-job-id], .job-search-card, .base-card')
            if not cards:
                cards = soup.select('div[class*="job-card"]')
            
            if not cards:
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'ItemList':
                            for item in data.get('itemListElement', []):
                                job = item.get('item', {})
                                if job.get('title'):
                                    jobs.append({
                                        "titre": job.get('title'),
                                        "entreprise": job.get('hiringOrganization', {}).get('name', 'Non précisé'),
                                        "lien": job.get('url', '#'),
                                        "location": job.get('jobLocation', {}).get('address', {}).get('addressLocality', location),
                                        "date": "",
                                        "source": "LinkedIn"
                                    })
                    except:
                        pass
            
            for card in cards[:limit]:
                title_elem = card.select_one('a.base-card__full-link, h3.base-search-card__title, a[href*="/jobs/view"]')
                company_elem = card.select_one('h4.base-search-card__subtitle, a[data-tracking-control-name*="company"]')
                location_elem = card.select_one('span.job-search-card__location, span[class*="location"]')
                link_elem = card.select_one('a.base-card__full-link')
                
                link = link_elem.get('href', '#') if link_elem else '#'
                
                if title_elem:
                    jobs.append({
                        "titre": title_elem.get_text(strip=True),
                        "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "lien": link,
                        "location": location_elem.get_text(strip=True) if location_elem else location,
                        "date": "",
                        "source": "LinkedIn"
                    })
            
            logger.info(f"[WEB:LinkedIn] done jobs={len(jobs)}")
            return jobs[:limit]
            
        except Exception as e:
            logger.error(f"[WEB:LinkedIn] error: {e}")
            return jobs


class MonsterScraper(WebScraperSource):
    """Scraper for Monster jobs."""
    
    def search(self, job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
        """
        Search Monster for jobs.
        
        Args:
            job_title: Job title to search
            location: Location
            limit: Max results
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        clean_title = self.clean_title(job_title)
        query = urllib.parse.quote(clean_title)
        logger.info(f"[WEB:Monster] start query={job_title!r} location={location!r} limit={limit}")
        
        try:
            urls = [
                f"https://www.monster.fr/emploi/recherche?q={query}&where={urllib.parse.quote(location)}",
                f"https://www.monster.com/jobs/search?q={query}&where={urllib.parse.quote(location)}"
            ]
            
            for url in urls:
                html = self._fetch_page(url)
                if not html:
                    logger.warning(f"[WEB:Monster] empty page for {url[:120]}")
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                cards = soup.select('div[class*="card"], section[class*="card"], .job-row, article')
                if not cards:
                    logger.warning(f"[WEB:Monster] no cards matched for {url[:120]}")
                    continue
                
                for card in cards[:limit]:
                    title_elem = card.select_one('h2 a, h3 a, a[data-testid="jobTitle"], a[class*="title"]')
                    company_elem = card.select_one('span[class*="company"], div[class*="company"], span[data-testid="company"]')
                    location_elem = card.select_one('span[class*="location"], div[class*="location"]')
                    link_elem = card.select_one('h2 a, h3 a, a[data-testid="jobTitle"]')
                    
                    link = link_elem.get('href', '#') if link_elem else '#'
                    if link and not link.startswith('http'):
                        link = "https://www.monster.fr" + link
                    
                    if title_elem:
                        jobs.append({
                            "titre": title_elem.get_text(strip=True),
                            "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                            "lien": link,
                            "location": location_elem.get_text(strip=True) if location_elem else location,
                            "date": "",
                            "source": "Monster"
                        })
                
                if jobs:
                    break
                    
        except Exception as e:
            logger.error(f"[WEB:Monster] error: {e}")
        
        logger.info(f"[WEB:Monster] done jobs={len(jobs)}")
        return jobs[:limit]


class HelloWorkScraper(WebScraperSource):
    """Scraper for HelloWork jobs."""
    
    def search(self, job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
        """
        Search HelloWork for jobs.
        
        Args:
            job_title: Job title to search
            location: Location
            limit: Max results
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        clean_title = self.clean_title(job_title)
        query = urllib.parse.quote(clean_title)
        logger.info(f"[WEB:HelloWork] start query={job_title!r} location={location!r} limit={limit}")
        
        try:
            url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?q={query}&l={urllib.parse.quote(location)}"
            html = self._fetch_page(url)
            if not html:
                logger.warning(f"[WEB:HelloWork] empty page for {url[:120]}")
                return jobs
            
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('div[class*="offer"], article[class*="job"], div[class*="result"]')
            
            for card in cards[:limit]:
                title_elem = card.select_one('h2 a, h3 a, a[class*="title"]')
                company_elem = card.select_one('span[class*="company"], div[class*="company"]')
                location_elem = card.select_one('span[class*="location"], div[class*="location"]')
                link_elem = card.select_one('h2 a, h3 a, a[class*="title"]')
                
                link = link_elem.get('href', '#') if link_elem else '#'
                if link and not link.startswith('http'):
                    link = "https://www.hellowork.com" + link
                
                if title_elem:
                    jobs.append({
                        "titre": title_elem.get_text(strip=True),
                        "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "lien": link,
                        "location": location_elem.get_text(strip=True) if location_elem else location,
                        "date": "",
                        "source": "HelloWork"
                    })
            
            logger.info(f"[WEB:HelloWork] done jobs={len(jobs)}")
            return jobs[:limit]
            
        except Exception as e:
            logger.error(f"[WEB:HelloWork] error: {e}")
            return jobs


# Convenience functions
def scrape_indeed(job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
    """Scrape Indeed jobs."""
    scraper = IndeedScraper()
    return scraper.search(job_title, location, limit)


def scrape_linkedin(job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
    """Scrape LinkedIn jobs."""
    scraper = LinkedInScraper()
    return scraper.search(job_title, location, limit)


def scrape_monster(job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
    """Scrape Monster jobs."""
    scraper = MonsterScraper()
    return scraper.search(job_title, location, limit)


def scrape_hellowork(job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
    """Scrape HelloWork jobs."""
    scraper = HelloWorkScraper()
    return scraper.search(job_title, location, limit)


def scrape_google_jobs(job_title: str, location: str = "France", limit: int = 50, serpapi_key: str = "") -> List[dict]:
    """Scrape Google Jobs via SerpApi."""
    if not serpapi_key:
        logger.warning("[WEB:GoogleJobs] skipped: no serpapi key")
        return []
    try:
        from app.scrapers.api_sources import get_google_jobs_source
        source = get_google_jobs_source(serpapi_key)
    except Exception as e:
        logger.error(f"[WEB:GoogleJobs] import/source error: {e}")
        return []
    if not source:
        logger.warning("[WEB:GoogleJobs] skipped: source unavailable")
        return []
    try:
        logger.info(f"[WEB:GoogleJobs] start query={job_title!r} location={location!r} limit={limit}")
        results = asyncio.run(source.search_jobs(job_title, location, limit=limit))
        logger.info(f"[WEB:GoogleJobs] done jobs={len(results)}")
        return results
    except Exception as e:
        logger.error(f"[WEB:GoogleJobs] error: {e}")
        return []


def scrape_jobspy(job_title: str, location: str = "France", limit: int = 50, selected_sites: Optional[List[str]] = None) -> List[dict]:
    """Scrape jobs via JobSpy library."""
    try:
        from jobspy import scrape_jobs
    except Exception as e:
        logger.error(f"[WEB:JobSpy] import error: {e}")
        return []
    try:
        logger.info(f"[WEB:JobSpy] start query={job_title!r} location={location!r} limit={limit} sites={selected_sites}")
        sites = [s.lower().replace(" ", "_") for s in selected_sites] if selected_sites else ["indeed", "linkedin", "glassdoor", "zip_recruiter"]
        valid_sites = []
        for s in sites:
            if s == "linkedin":
                valid_sites.append("linkedin")
            elif s == "indeed":
                valid_sites.append("indeed")
            elif s == "ziprecruiter":
                valid_sites.append("zip_recruiter")
            elif s == "glassdoor":
                valid_sites.append("glassdoor")
        if not valid_sites:
            valid_sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter"]
        jobs_df = scrape_jobs(
            site_name=valid_sites,
            search_term=job_title,
            location=location,
            results_per_site=limit,
            hours_old=72,
        )
        results = []
        if jobs_df is not None and not jobs_df.empty:
            for _, row in jobs_df.iterrows():
                results.append({
                    "titre": row.get("title", "Sans titre"),
                    "entreprise": row.get("company", "Entreprise anonyme"),
                    "lien": row.get("job_url", "#"),
                    "location": row.get("location", location),
                    "date": str(row.get("date_posted", ""))[:10],
                    "source": str(row.get("site", "JobSpy")).title(),
                    "description": row.get("description", ""),
                })
        logger.info(f"[WEB:JobSpy] done jobs={len(results)}")
        return results[:limit]
    except Exception as e:
        logger.error(f"[WEB:JobSpy] error: {e}")
        return []


def scrape_enhanced(job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
    """Enhanced multi-source aggregator using lightweight scrapers."""
    logger.info(f"[WEB:Enhanced] start query={job_title!r} location={location!r} limit={limit}")
    results = []
    try:
        results.extend(scrape_indeed(job_title, location, limit=limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] indeed error: {e}")
    try:
        results.extend(scrape_linkedin(job_title, location, limit=limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] linkedin error: {e}")
    try:
        results.extend(scrape_monster(job_title, location, limit=limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] monster error: {e}")
    try:
        results.extend(scrape_hellowork(job_title, location, limit=limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] hellowork error: {e}")
    seen = set()
    deduped = []
    for job in results:
        key = (job.get("titre"), job.get("entreprise"), job.get("location"))
        if key not in seen:
            seen.add(key)
            deduped.append(job)
    logger.info(f"[WEB:Enhanced] done jobs={len(deduped)}")
    return deduped[:limit]