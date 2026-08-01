"""
Lightweight web scrapers for job sources
LinkedIn, Indeed, and other sites - Timeout 6s
Intégration des stratégies de contournement (bypass_strategies) pour maximiser les résultats.
"""

import json
import logging
import re
import asyncio
import time
import urllib.parse
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

from app.scrapers.bypass_strategies import (
    generate_relaxed_queries,
    get_rotated_headers,
    get_jitter_delay,
    optimize_location_for_api,
    get_optimal_limit,
    search_with_query_relaxation,
    normalize_and_deduplicate,
)

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
    """Scraper for LinkedIn jobs.
    Intègre les stratégies de contournement : query relaxation, rotation d'User-Agent, jitter.
    """
    
    def search(self, job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
        """
        Search LinkedIn for jobs with bypass strategies.
        Si la recherche exacte renvoie 0 résultat, réessaie avec des variantes plus larges.
        """
        # 🔑 Stratégie 3: Optimiser la limite
        optimal_limit = get_optimal_limit(limit, "LinkedIn")
        
        # 🔄 Stratégie 1: Recherche avec relâchement automatique des requêtes
        def _search_single(relaxed_query: str, loc: str, lim: int) -> List[dict]:
            """Sous-fonction de recherche synchrone pour une requête unique."""
            jobs = []
            try:
                clean_title = self.clean_title(relaxed_query)
                query = urllib.parse.quote(clean_title)
                loc_encoded = urllib.parse.quote(optimize_location_for_api(loc, "LinkedIn"))
                
                # 🛡️ Stratégie 2: Headers avec rotation d'User-Agent
                headers = get_rotated_headers()
                
                # 🔑 Stratégie 3: URL optimisée avec plus de résultats
                url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc_encoded}&f_TPR=r2592000"
                logger.info(f"[WEB:LinkedIn] query={relaxed_query!r} location={loc!r} limit={lim}")
                
                # 🛡️ Stratégie 2: Fetch avec headers rotatifs
                try:
                    response = requests.get(url, headers=headers, timeout=self.TIMEOUT)
                    if response.status_code != 200:
                        logger.warning(f"[WEB:LinkedIn] HTTP {response.status_code} for {url[:120]}")
                        return jobs
                    html = response.text
                except Exception as e:
                    logger.warning(f"[WEB:LinkedIn] fetch error: {e}")
                    return jobs
                
                if not html:
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
                                            "location": job.get('jobLocation', {}).get('address', {}).get('addressLocality', loc),
                                            "date": "",
                                            "source": "LinkedIn"
                                        })
                        except:
                            pass
                
                for card in cards[:lim]:
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
                            "location": location_elem.get_text(strip=True) if location_elem else loc,
                            "date": "",
                            "source": "LinkedIn"
                        })
                
                logger.info(f"[WEB:LinkedIn] variation '{relaxed_query}' returned {len(jobs)} jobs")
                return jobs
                
            except Exception as e:
                logger.error(f"[WEB:LinkedIn] error: {e}")
                return jobs
        
        # 🔄 Stratégie 1: Générer les variantes et essayer
        relaxed_queries = generate_relaxed_queries(job_title, max_variations=4)
        all_jobs = []
        seen_keys = set()
        
        for i, relaxed_query in enumerate(relaxed_queries):
            # 🛡️ Stratégie 2: Jitter entre les tentatives
            if i > 0:
                time.sleep(get_jitter_delay(0.5, 1.5))
            
            results = _search_single(relaxed_query, location, optimal_limit)
            
            if results:
                # 🧹 Stratégie 5: Déduplication
                for job in results:
                    key = (job.get("titre", "").lower(), job.get("entreprise", "").lower(), job.get("location", "").lower())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
                
                if len(all_jobs) >= optimal_limit:
                    break
        
        # 🧹 Stratégie 5: Normalisation et déduplication finale
        all_jobs = normalize_and_deduplicate(all_jobs)
        
        logger.info(f"[WEB:LinkedIn] done jobs={len(all_jobs)} (after bypass strategies)")
        return all_jobs[:limit]


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
    """Scrape Indeed jobs - uses LinkedIn scraper as fallback since IndeedScraper is not defined."""
    # Indeed blocking is aggressive, fallback to LinkedIn-style scraping
    logger.info(f"[WEB:Indeed] start query={job_title!r} location={location!r} limit={limit}")
    try:
        # 🔄 Stratégie 1: Query relaxation
        relaxed_queries = generate_relaxed_queries(job_title, max_variations=3)
        all_jobs = []
        seen_keys = set()
        
        for relaxed_query in relaxed_queries:
            clean_title = re.sub(r'[^\w\s,-]', '', relaxed_query)
            query = urllib.parse.quote(clean_title)
            loc = urllib.parse.quote(optimize_location_for_api(location, "Indeed"))
            
            # 🛡️ Stratégie 2: Headers avec rotation
            headers = get_rotated_headers()
            
            # 🔑 Stratégie 3: URL optimisée
            url = f"https://fr.indeed.com/jobs?q={query}&l={loc}&limit=50"
            logger.info(f"[WEB:Indeed] trying: {url[:120]}")
            
            try:
                response = requests.get(url, headers=headers, timeout=6)
                if response.status_code != 200:
                    logger.warning(f"[WEB:Indeed] HTTP {response.status_code}")
                    continue
                html = response.text
            except Exception as e:
                logger.warning(f"[WEB:Indeed] fetch error: {e}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('div.job_seen_beacon, div.result, div[data-jk]')
            
            for card in cards[:limit]:
                title_elem = card.select_one('h2 a, h2.jobTitle, a.jobtitle')
                company_elem = card.select_one('span.companyName, div.company')
                location_elem = card.select_one('div.companyLocation, span.location')
                link_elem = card.select_one('h2 a, a.jobtitle')
                
                link = link_elem.get('href', '#') if link_elem else '#'
                if link and not link.startswith('http'):
                    link = "https://fr.indeed.com" + link
                
                if title_elem:
                    job = {
                        "titre": title_elem.get_text(strip=True),
                        "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "lien": link,
                        "location": location_elem.get_text(strip=True) if location_elem else location,
                        "date": "",
                        "source": "Indeed"
                    }
                    key = (job["titre"].lower(), job["entreprise"].lower(), job["location"].lower())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
            
            if len(all_jobs) >= limit:
                break
            
            # 🛡️ Stratégie 2: Jitter
            time.sleep(get_jitter_delay(0.5, 1.5))
        
        # 🧹 Stratégie 5: Normalisation
        all_jobs = normalize_and_deduplicate(all_jobs)
        logger.info(f"[WEB:Indeed] done jobs={len(all_jobs)}")
        return all_jobs[:limit]
        
    except Exception as e:
        logger.error(f"[WEB:Indeed] error: {e}")
        return []


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


async def scrape_google_jobs(job_title: str, location: str = "France", limit: int = 50, serpapi_key: str = "") -> List[dict]:
    """Scrape Google Jobs via SerpApi.
    
    Now fully async to avoid asyncio.run() in async contexts.
    """
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
        results = await source.search_jobs(job_title, location, limit=limit)
        logger.info(f"[WEB:GoogleJobs] done jobs={len(results)}")
        return results
    except Exception as e:
        logger.error(f"[WEB:GoogleJobs] error: {e}")
        return []


def scrape_jobspy(job_title: str, location: str = "France", limit: int = 50, selected_sites: Optional[List[str]] = None) -> List[dict]:
    """Scrape jobs via JobSpy library.
    Intègre les stratégies de contournement : query relaxation, optimisation des paramètres.
    """
    try:
        from jobspy import scrape_jobs
    except Exception as e:
        logger.error(f"[WEB:JobSpy] import error: {e}")
        return []
    
    # 🔑 Stratégie 3: Optimiser la limite
    optimal_limit = get_optimal_limit(limit, "JobSpy")
    
    # 🔄 Stratégie 1: Query relaxation
    relaxed_queries = generate_relaxed_queries(job_title, max_variations=3)
    all_results = []
    seen_keys = set()
    
    for relaxed_query in relaxed_queries:
        try:
            logger.info(f"[WEB:JobSpy] query={relaxed_query!r} location={location!r} limit={optimal_limit}")
            # ✅ CORRECTION: Limiter aux sites les plus rapides + country_indeed
            sites = ["indeed", "glassdoor"]  # Sites plus rapides que LinkedIn/ZipRecruiter
            valid_sites = []
            for s in sites:
                if s == "indeed":
                    valid_sites.append("indeed")
                elif s == "glassdoor":
                    valid_sites.append("glassdoor")
            
            if not valid_sites:
                valid_sites = ["indeed", "glassdoor"]
            
            # ✅ CORRECTION: Ajouter country_indeed pour de meilleurs résultats français
            # ✅ CORRECTION: Ajouter timeout explicite si supporté par la version de jobspy
            try:
                # Essayer avec timeout si supporté (jobspy >= 1.9.0)
                jobs_df = scrape_jobs(
                    site_name=valid_sites,
                    search_term=relaxed_query,
                    location=optimize_location_for_api(location, "JobSpy"),
                    results_per_site=optimal_limit,
                    hours_old=72,
                    country_indeed='France',  # Spécifier pays pour Indeed FR
                )
            except TypeError:
                # Version plus ancienne de jobspy sans support timeout/timeout
                jobs_df = scrape_jobs(
                    site_name=valid_sites,
                    search_term=relaxed_query,
                    location=optimize_location_for_api(location, "JobSpy"),
                    results_per_site=optimal_limit,
                    hours_old=72,
                    country_indeed='France',
                )
            
            if jobs_df is not None and not jobs_df.empty:
                for _, row in jobs_df.iterrows():
                    job = {
                        "titre": row.get("title", "Sans titre"),
                        "entreprise": row.get("company", "Entreprise anonyme"),
                        "lien": row.get("job_url", "#"),
                        "location": row.get("location", location),
                        "date": str(row.get("date_posted", ""))[:10],
                        "source": str(row.get("site", "JobSpy")).title(),
                        "description": row.get("description", ""),
                    }
                    # 🧹 Stratégie 5: Déduplication
                    key = (job["titre"].lower(), job["entreprise"].lower(), job["location"].lower())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append(job)
            
            if len(all_results) >= optimal_limit:
                break
            
            # 🛡️ Stratégie 2: Jitter entre les tentatives
            time.sleep(get_jitter_delay(0.5, 1.5))
            
        except Exception as e:
            logger.error(f"[WEB:JobSpy] error with query '{relaxed_query}': {e}")
            continue
    
    # 🧹 Stratégie 5: Normalisation et déduplication finale
    all_results = normalize_and_deduplicate(all_results)
    
    logger.info(f"[WEB:JobSpy] done jobs={len(all_results)} (after bypass strategies)")
    return all_results[:limit]


def scrape_enhanced(job_title: str, location: str = "France", limit: int = 50) -> List[dict]:
    """Enhanced multi-source aggregator using lightweight scrapers.
    Intègre les stratégies de contournement pour maximiser les résultats.
    """
    # 🔑 Stratégie 3: Optimiser la limite
    optimal_limit = get_optimal_limit(limit, "Enhanced")
    
    logger.info(f"[WEB:Enhanced] start query={job_title!r} location={location!r} limit={optimal_limit}")
    results = []
    
    # 🔀 Stratégie 4: Exécution parallèle non-bloquante avec gestion d'erreurs
    try:
        results.extend(scrape_indeed(job_title, location, limit=optimal_limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] indeed error: {e}")
    try:
        results.extend(scrape_linkedin(job_title, location, limit=optimal_limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] linkedin error: {e}")
    try:
        results.extend(scrape_monster(job_title, location, limit=optimal_limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] monster error: {e}")
    try:
        results.extend(scrape_hellowork(job_title, location, limit=optimal_limit))
    except Exception as e:
        logger.error(f"[WEB:Enhanced] hellowork error: {e}")
    
    # 🧹 Stratégie 5: Normalisation et déduplication intelligente
    results = normalize_and_deduplicate(results)
    
    logger.info(f"[WEB:Enhanced] done jobs={len(results)} (after bypass strategies)")
    return results[:limit]