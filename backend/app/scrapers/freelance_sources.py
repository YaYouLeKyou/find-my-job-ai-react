"""
Scrapers for freelance-specific platforms.
These scrapers target platforms that publish 100% freelance missions.
"""

import re
import logging
import asyncio
import urllib.parse
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Common headers for scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _extract_skills_from_text(text: str) -> list:
    """Extract technical skills from text."""
    if not text:
        return []
    common_skills = [
        "React", "Vue", "Angular", "TypeScript", "JavaScript", "Python", "Java",
        "Node.js", "Node", "Django", "Flask", "FastAPI", "Spring", "Laravel",
        "Ruby", "Go", "Rust", "PHP", "C#", ".NET", "React Native", "Flutter",
        "Swift", "Kotlin", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "GraphQL", "REST API",
        "Git", "CI/CD", "Agile", "Scrum", "Microservices", "DevOps",
        "UI/UX", "Design", "Figma", "Marketing", "Data", "Machine Learning", "AI",
        "SEO", "Content", "Rédaction", "Communication", "Management",
    ]
    text_lower = text.lower()
    skills = []
    for skill in common_skills:
        if skill.lower() in text_lower:
            skills.append(skill)
    return skills[:10]


def _extract_tjm_from_text(text: str) -> Optional[str]:
    """Extract TJM (daily rate) from text."""
    if not text:
        return None
    # Patterns: "500€/j", "TJM: 450€", "400-600€/jour", "TJM à négocier"
    tjm_patterns = [
        r'(\d{3,4})\s*€\s*/\s*j(?:our)?',  # 500€/j, 500€/jour
        r'tjm\s*:?\s*(\d{3,4})\s*€?',      # TJM: 500€, TJM 500
        r'(\d{3,4})\s*-\s*\d{3,4}\s*€\s*/\s*j',  # 400-600€/j
        r'tarif\s*:?\s*(\d{3,4})\s*€',     # tarif: 500€
    ]
    for pattern in tjm_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


async def scrape_free_work(query: str, location: str, limit: int = 50) -> List[Dict]:
    """
    Scrape Free-Work (formerly JavaIte) for freelance IT missions.
    URL: https://www.free-work.com/fr/tech-it/jobs
    
    This is the #1 source for IT freelance missions in France.
    Almost all offers indicate TJM, location (or remote) and duration.
    
    Uses SerpApi for fast and reliable results.
    """
    import requests as req_lib
    import asyncio
    
    jobs = []
    
    # Use SerpApi to find Free-Work missions via Google (fast and reliable)
    try:
        from app.config import get_settings
        settings = get_settings()
        
        if settings.SERPAPI_KEY:
            serp_query = f'site:free-work.com/fr/tech-it/jobs "{query}" freelance'
            logger.info(f"[FREE-WORK] SerpApi query: {serp_query}")
            
            serp_params = {
                "q": serp_query,
                "num": min(limit, 10),
                "hl": "fr",
                "gl": "fr",
                "api_key": settings.SERPAPI_KEY,
            }
            
            def _sync_serpapi():
                return req_lib.get("https://serpapi.com/search", params=serp_params, timeout=(5, 10))
            
            response = await asyncio.to_thread(_sync_serpapi)
            
            if response.status_code == 200:
                data = response.json()
                organic_results = data.get("organic_results", [])
                
                for result in organic_results[:limit]:
                    link = result.get("link", "")
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    
                    job = {
                        "title": title,
                        "company": "Free-Work",
                        "link": link,
                        "location": location,
                        "description": snippet,
                        "source": "Free-Work",
                        "contract_type": "Freelance",
                        "tjm": _extract_tjm_from_text(snippet),
                        "skills": _extract_skills_from_text(f"{title} {snippet}"),
                    }
                    jobs.append(job)
                
                logger.info(f"[FREE-WORK] SerpApi found {len(jobs)} results")
            else:
                logger.warning(f"[FREE-WORK] SerpApi HTTP {response.status_code}")
        else:
            logger.warning("[FREE-WORK] SERPAPI_KEY not configured")
    except Exception as e:
        logger.error(f"[FREE-WORK] SerpApi failed: {e}")
    
    logger.info(f"[FREE-WORK] Returning {len(jobs)} freelance jobs")
    return jobs


async def scrape_codeur_com(query: str, location: str, limit: int = 50) -> List[Dict]:
    """
    Scrape Codeur.com for freelance projects and missions.
    URL: https://www.codeur.com/missions
    
    Codeur.com is a French platform for freelance projects (web, mobile, design).
    """
    import requests as req_lib
    
    jobs = []
    
    try:
        encoded_query = urllib.parse.quote(query)
        base_url = f"https://www.codeur.com/missions?q={encoded_query}"
        
        logger.info(f"[CODEUR] Scraping URL: {base_url}")
        
        response = req_lib.get(base_url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Codeur.com uses specific classes for mission listings
            mission_cards = soup.find_all("div", class_=lambda c: c and ("mission" in c.lower() or "project" in c.lower() or "card" in c.lower()))
            
            if not mission_cards:
                # Try article tags
                mission_cards = soup.find_all("article")
            
            if not mission_cards:
                # Try links to mission detail pages
                mission_cards = soup.find_all("a", href=lambda h: h and "/missions/" in h)
            
            logger.info(f"[CODEUR] Found {len(mission_cards)} mission cards")
            
            for card in mission_cards[:limit]:
                try:
                    # Extract title
                    title_elem = card.find(["h2", "h3", "h4", "a"], class_=lambda c: c and "title" in (c.lower() if c else ""))
                    title = title_elem.get_text(strip=True) if title_elem else card.get_text(strip=True)
                    
                    if not title and card.name == "a":
                        title = card.get_text(strip=True)
                    
                    link = card.get("href", "")
                    if link and not link.startswith("http"):
                        link = f"https://www.codeur.com{link}"
                    
                    # Extract description
                    desc_elem = card.find("p")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Extract budget/TJM
                    budget_elem = card.find(class_=lambda c: c and ("budget" in c.lower() if c else "" or "price" in c.lower() if c else ""))
                    budget = budget_elem.get_text(strip=True) if budget_elem else ""
                    
                    card_text = card.get_text(separator=" ", strip=True)
                    tjm = _extract_tjm_from_text(card_text) or budget
                    
                    # Extract skills
                    skills_elem = card.find(class_=lambda c: c and "skill" in (c.lower() if c else ""))
                    skills_text = skills_elem.get_text(strip=True) if skills_elem else ""
                    
                    job = {
                        "title": title,
                        "company": "Codeur.com",
                        "link": link or "#",
                        "location": location,
                        "description": f"{description} {budget}".strip(),
                        "source": "Codeur.com",
                        "contract_type": "Freelance",
                        "tjm": tjm,
                        "skills": _extract_skills_from_text(f"{title} {description} {skills_text}"),
                    }
                    
                    if title:
                        jobs.append(job)
                        
                except Exception as e:
                    logger.warning(f"[CODEUR] Error parsing card: {e}")
                    continue
        else:
            logger.warning(f"[CODEUR] HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"[CODEUR] Scraping failed: {e}")
    
    # Fallback: SerpApi
    if not jobs:
        try:
            from app.config import get_settings
            settings = get_settings()
            
            if settings.SERPAPI_KEY:
                serp_query = f'site:codeur.com/missions "{query}"'
                logger.info(f"[CODEUR] SerpApi fallback query: {serp_query}")
                
                serp_params = {
                    "q": serp_query,
                    "num": min(limit, 10),
                    "hl": "fr",
                    "gl": "fr",
                    "api_key": settings.SERPAPI_KEY,
                }
                
                response = req_lib.get("https://serpapi.com/search", params=serp_params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    organic_results = data.get("organic_results", [])
                    
                    for result in organic_results[:limit]:
                        link = result.get("link", "")
                        title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        
                        job = {
                            "title": title,
                            "company": "Codeur.com",
                            "link": link,
                            "location": location,
                            "description": snippet,
                            "source": "Codeur.com",
                            "contract_type": "Freelance",
                            "tjm": _extract_tjm_from_text(snippet),
                            "skills": _extract_skills_from_text(f"{title} {snippet}"),
                        }
                        jobs.append(job)
                    
                    logger.info(f"[CODEUR] SerpApi found {len(jobs)} results")
        except Exception as e:
            logger.warning(f"[CODEUR] SerpApi fallback failed: {e}")
    
    logger.info(f"[CODEUR] Returning {len(jobs)} freelance jobs")
    return jobs


async def scrape_freelance_republik(query: str, location: str, limit: int = 50) -> List[Dict]:
    """
    Scrape FreelanceRepublik for IT freelance missions.
    URL: https://www.freelancerepublik.com/missions
    
    Dedicated to long-term IT/Tech missions (3-18 months) with large enterprise clients.
    """
    import requests as req_lib
    
    jobs = []
    
    try:
        encoded_query = urllib.parse.quote(query)
        base_url = f"https://www.freelancerepublik.com/missions?search={encoded_query}"
        
        logger.info(f"[FREELANCE-REPUBLIK] Scraping URL: {base_url}")
        
        response = req_lib.get(base_url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            mission_cards = soup.find_all("div", class_=lambda c: c and ("mission" in c.lower() or "offer" in c.lower() or "card" in c.lower()))
            
            if not mission_cards:
                mission_cards = soup.find_all("article")
            
            logger.info(f"[FREELANCE-REPUBLIK] Found {len(mission_cards)} mission cards")
            
            for card in mission_cards[:limit]:
                try:
                    title_elem = card.find(["h2", "h3", "h4"])
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    link_elem = card.find("a", href=True)
                    link = link_elem["href"] if link_elem else "#"
                    if link and not link.startswith("http"):
                        link = f"https://www.freelancerepublik.com{link}"
                    
                    desc_elem = card.find("p")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    card_text = card.get_text(separator=" ", strip=True)
                    tjm = _extract_tjm_from_text(card_text)
                    
                    job = {
                        "title": title,
                        "company": "FreelanceRepublik",
                        "link": link,
                        "location": location,
                        "description": description,
                        "source": "FreelanceRepublik",
                        "contract_type": "Freelance",
                        "tjm": tjm,
                        "skills": _extract_skills_from_text(f"{title} {description}"),
                    }
                    
                    if title:
                        jobs.append(job)
                        
                except Exception as e:
                    logger.warning(f"[FREELANCE-REPUBLIK] Error parsing card: {e}")
                    continue
        else:
            logger.warning(f"[FREELANCE-REPUBLIK] HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"[FREELANCE-REPUBLIK] Scraping failed: {e}")
    
    logger.info(f"[FREELANCE-REPUBLIK] Returning {len(jobs)} freelance jobs")
    return jobs


async def scrape_upwork_rss(query: str, location: str = "", limit: int = 50) -> List[Dict]:
    """
    Scrape Upwork RSS feed for freelance missions.
    URL: https://www.upwork.com/ab/feed/jobs/rss?q=query
    
    Upwork provides official RSS feeds that are reliable and don't require HTML scraping.
    """
    import feedparser
    import requests as req_lib
    
    jobs = []
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://www.upwork.com/ab/feed/jobs/rss?q={encoded_query}"
    
    logger.info(f"[UPWORK-RSS] Scraping RSS: {rss_url[:100]}")
    
    try:
        response = req_lib.get(rss_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:limit]:
                try:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    description = entry.get('summary', '')
                    author = entry.get('author', '')
                    
                    published = entry.get('published', '')
                    if 'published_parsed' in entry:
                        published = str(entry.published_parsed).split(' ')[0] if entry.published_parsed else ''
                    
                    card_text = f"{title} {description} {author}"
                    tjm = _extract_tjm_from_text(card_text)
                    
                    job = {
                        "title": title,
                        "company": author or "Upwork",
                        "link": link,
                        "location": location or "Remote",
                        "description": description,
                        "source": "UpworkRSS",
                        "contract_type": "Freelance",
                        "tjm": tjm,
                        "skills": _extract_skills_from_text(card_text),
                        "date": published,
                    }
                    jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"[UPWORK-RSS] Error parsing entry: {e}")
                    continue
        
        logger.info(f"[UPWORK-RSS] Returned {len(jobs)} jobs")
        return jobs[:limit]
        
    except Exception as e:
        logger.error(f"[UPWORK-RSS] Error: {e}")
        return []


async def scrape_wwr_rss(category: str = "", query: str = "", limit: int = 50) -> List[Dict]:
    """
    Scrape We Work Remotely RSS feed for freelance missions.
    URL: https://weworkremotely.com/categories/remote-<category>-jobs.rss
    
    Categories: backend, development, design, management, sales
    """
    import feedparser
    import requests as req_lib
    
    jobs = []
    
    categories = [
        'remote-back-end-programming-jobs',
        'remote-front-end-programming-jobs',
        'remote-full-stack-programming-jobs',
        'remote-devops-engineering-jobs',
        'remote-mobile-programming-jobs',
        'remote-data-jobs',
        'remote-design-jobs',
        'remote-management-jobs',
    ]
    
    search_term = (query or category).lower().strip() if (query or category) else None
    
    for cat in categories[:3]:
        rss_url = f"https://weworkremotely.com/categories/{cat}.rss"
        logger.info(f"[WWR-RSS] Scraping: {rss_url[:80]}")
        
        try:
            response = req_lib.get(rss_url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:limit]:
                    try:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        description = entry.get('summary', '')
                        
                        # Filter by search term if provided
                        if search_term:
                            card_text = f"{title} {description}".lower()
                            if search_term not in card_text:
                                continue
                        
                        card_text = f"{title} {description}"
                        tjm = _extract_tjm_from_text(card_text)
                        
                        job = {
                            "title": title,
                            "company": "We Work Remotely",
                            "link": link,
                            "location": "Remote",
                            "description": description,
                            "source": "WeWorkRemotelyRSS",
                            "contract_type": "Freelance",
                            "tjm": tjm,
                            "skills": _extract_skills_from_text(card_text),
                            "date": entry.get('published', ''),
                        }
                        jobs.append(job)
                        
                        if len(jobs) >= limit:
                            break
                    except Exception as e:
                        logger.warning(f"[WWR-RSS] Error parsing entry: {e}")
                        continue
                
                if len(jobs) >= limit:
                    break
                    
        except Exception as e:
            logger.warning(f"[WWR-RSS] Error for {cat}: {e}")
            continue
    
    logger.info(f"[WWR-RSS] Returned {len(jobs)} jobs")
    return jobs[:limit]


async def scrape_remoteok_api(query: str = "", location: str = "", limit: int = 50) -> List[Dict]:
    """
    Scrape RemoteOK API for remote freelance jobs.
    URL: https://remoteok.com/api
    
    Free public JSON API, no authentication required.
    """
    import requests as req_lib
    
    jobs = []
    api_url = "https://remoteok.com/api"
    
    logger.info(f"[REMOTEOK] Scraping API: {api_url}")
    
    try:
        response = req_lib.get(
            api_url, 
            headers={'User-Agent': HEADERS.get('User-Agent', 'Chrome/120.0')},
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if isinstance(data, list):
                    for item in data[:limit]:
                        try:
                            # Filter by search term if provided
                            title = item.get('title', '')
                            description = item.get('description', '')
                            
                            if query and query.lower() not in f"{title} {description}".lower():
                                continue
                            
                            # Estimate TJM from salary info
                            salary_text = f"{item.get('salary', '')} {item.get('pay', '')}"
                            salary = item.get('salary', '')
                            
                            # Convert salary/hourly info to TJM estimate
                            tjm = None
                            if salary:
                                try:
                                    amt = int(salary)
                                    if 'hourly' in str(item.get('duration', '')).lower():
                                        # Hourly -> Daily (assuming 7h/day)
                                        tjm = f"{min(amt * 7, 1000)}€/jour"
                                    else:
                                        # Already a daily rate or contract amount
                                        tjm = f"{amt}€/jour"
                                except:
                                    pass
                            
                            job = {
                                "title": title,
                                "company": item.get('company', 'RemoteOK'),
                                "link": f"https://remoteok.com{item.get('url', '/')}",
                                "location": location or item.get('location', 'Remote'),
                                "description": description[:500] if description else '',
                                "source": "RemoteOK",
                                "contract_type": "Freelance",
                                "tjm": tjm,
                                "skills": _extract_skills_from_text(f"{title} {description}"),
                                "date": item.get('published_at', ''),
                                "tags": item.get('tags', []),
                            }
                            jobs.append(job)
                            
                        except Exception as e:
                            logger.warning(f"[REMOTEOK] Error parsing item: {e}")
                            continue
                
                logger.info(f"[REMOTEOK] Returned {len(jobs)} jobs")
                return jobs[:limit]
                
            except Exception as e:
                logger.error(f"[REMOTEOK] JSON parse error: {e}")
                return []
        else:
            logger.warning(f"[REMOTEOK] HTTP {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"[REMOTEOK] Error: {e}")
        return []


async def scrape_upwork_rss(query: str = "", location: str = "", limit: int = 50) -> List[Dict]:
    """
    Scrape Upwork RSS feed for freelance missions.
    URL: https://www.upwork.com/fr/rss/feeds/missions
    
    Upwork provides public RSS feeds for freelance missions.
    """
    import feedparser
    import requests as req_lib
    from urllib.parse import quote
    
    jobs = []
    
    rss_urls = [
        "https://www.upwork.com/fr/rss/feeds/missions?category=all&term=" + quote(query.lower().split()[0] if query else "development"),
        "https://www.upwork.com/fr/rss/feeds/missions?category=it-technology",
        "https://www.upwork.com/fr/rss/feeds/missions?category=design-creative",
    ]
    
    search_term = query.lower().strip() if query else None
    
    for rss_url in rss_urls:
        try:
            logger.info(f"[UPWORK-RSS] Scraping: {rss_url[:80]}")
            response = req_lib.get(rss_url, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:limit]:
                    try:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        description = entry.get('summary', '')
                        
                        if search_term:
                            card_text = f"{title} {description}".lower()
                            if search_term not in card_text:
                                continue
                        
                        card_text = f"{title} {description}"
                        author = entry.get('author', '')
                        published = entry.get('published', '')
                        
                        tjm = _extract_tjm_from_text(card_text)
                        
                        job = {
                            "title": title,
                            "company": author or "Upwork",
                            "link": link,
                            "location": location or "Remote",
                            "description": description,
                            "source": "UpworkRSS",
                            "contract_type": "Freelance",
                            "tjm": tjm,
                            "skills": _extract_skills_from_text(card_text),
                            "date": published,
                        }
                        jobs.append(job)
                        
                        if len(jobs) >= limit:
                            break
                            
                    except Exception as e:
                        logger.warning(f"[UPWORK-RSS] Error parsing entry: {e}")
                        continue
                
                if len(jobs) >= limit:
                    break
                    
            elif response.status_code == 403:
                logger.warning(f"[UPWORK-RSS] HTTP 403 - trying alternative endpoint")
                alt_url = "https://www.upwork.com/freelance-missions.rss"
                response = req_lib.get(alt_url, headers=HEADERS, timeout=10)
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    for entry in feed.entries[:limit]:
                        try:
                            title = entry.get('title', '')
                            link = entry.get('link', '')
                            description = entry.get('summary', '')
                            
                            if search_term:
                                card_text = f"{title} {description}".lower()
                                if search_term not in card_text:
                                    continue
                            
                            job = {
                                "title": title,
                                "company": "Upwork",
                                "link": link,
                                "location": "Remote",
                                "description": description,
                                "source": "UpworkRSS",
                                "contract_type": "Freelance",
                                "tjm": _extract_tjm_from_text(f"{title} {description}"),
                                "skills": _extract_skills_from_text(f"{title} {description}"),
                                "date": entry.get('published', ''),
                            }
                            jobs.append(job)
                            
                            if len(jobs) >= limit:
                                break
                        except Exception as e:
                            logger.warning(f"[UPWORK-RSS] Alt parse error: {e}")
                            continue
                            
        except Exception as e:
            logger.warning(f"[UPWORK-RSS] Error for {rss_url}: {e}")
            continue
    
    logger.info(f"[UPWORK-RSS] Returned {len(jobs)} jobs")
    return jobs[:limit]


async def scrape_malt(query: str = "", location: str = "", limit: int = 50) -> List[Dict]:
    """
    Scrape Malt.fr for freelance candidates/missions.
    URL: https://www.malt.fr/search/results
    
    First tries RSS, falls back to X-Ray Google SerpApi if RSS unavailable.
    """
    import requests as req_lib
    from urllib.parse import quote
    
    jobs = []
    
    malt_rss_url = "https://www.malt.fr/rss/search?q=" + quote(query.lower().replace(" ", "+") if query else "d%C3%A9veloppeur")
    
    try:
        logger.info(f"[MALT] Trying RSS: {malt_rss_url[:80]}")
        response = req_lib.get(
            malt_rss_url,
            headers={
                **HEADERS,
                "Accept": "application/rss+xml, application/xml, text/xml;q=0.9,*/*;q=0.8",
            },
            timeout=10
        )
        
        if response.status_code == 200 and 'item' in response.text:
            import feedparser
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:limit]:
                try:
                    title = entry.get('title', '') or entry.get('title', '')
                    link = entry.get('link', '')
                    description = entry.get('summary', entry.get('summary', ''))
                    
                    if query:
                        search_text = f"{title} {description}".lower()
                        if query.lower() not in search_text:
                            continue
                    
                    job = {
                        "title": title,
                        "company": "Malt",
                        "link": link,
                        "location": location or "France",
                        "description": description[:500] if description else '',
                        "source": "Malt",
                        "contract_type": "Freelance",
                        "skills": _extract_skills_from_text(f"{title} {description}"),
                        "date": entry.get('published', ''),
                    }
                    jobs.append(job)
                    
                    if len(jobs) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"[MALT] RSS entry parse error: {e}")
                    continue
                    
            if jobs:
                logger.info(f"[MALT] Returned {len(jobs)} jobs from RSS")
                return jobs[:limit]
    
    except Exception as e:
        logger.warning(f"[MALT] RSS failed: {e}")
    
    from app.config import get_settings
    settings = get_settings()
    
    if settings.SERPAPI_KEY:
        try:
            logger.info(f"[MALT] Falling back to SerpApi X-Ray")
            serp_query = f'site:malt.fr "{query}" freelancer' if query else 'site:malt.fr freelancer'
            serp_params = {
                "q": serp_query,
                "num": min(limit, 20),
                "hl": "fr",
                "gl": "fr",
                "api_key": settings.SERPAPI_KEY,
            }
            
            response = req_lib.get(
                "https://serpapi.com/search",
                params=serp_params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                organic_results = data.get("organic_results", [])
                
                for item in organic_results[:limit]:
                    try:
                        title = item.get('title', '')
                        link = item.get('link', '')
                        snippet = item.get('snippet', '')
                        
                        job = {
                            "title": title,
                            "company": "Malt (via SerpApi)",
                            "link": link,
                            "location": location or "France",
                            "description": snippet[:500] if snippet else '',
                            "source": "Malt",
                            "contract_type": "Freelance",
                            "skills": _extract_skills_from_text(f"{title} {snippet}"),
                            "date": '',
                        }
                        jobs.append(job)
                        
                        if len(jobs) >= limit:
                            break
                            
                    except Exception as e:
                        logger.warning(f"[MALT] SerpApi parse error: {e}")
                        continue
                        
            if jobs:
                logger.info(f"[MALT] Returned {len(jobs)} jobs from SerpApi")
                return jobs[:limit]
                
        except Exception as e:
            logger.warning(f"[MALT] SerpApi fallback failed: {e}")
    
    logger.info(f"[MALT] Returned {len(jobs)} jobs")
    return jobs[:limit]


async def scrape_freelancer_com(query: str = "", location: str = "", limit: int = 50) -> List[Dict]:
    """
    Scrape Freelancer.com for freelance jobs.
    URL: https://www.freelancer.com/jobs
    
    Uses RSS feed for public job listings.
    """
    import feedparser
    import requests as req_lib
    from urllib.parse import quote
    
    jobs = []
    search_term = query.lower().strip() if query else None
    
    rss_urls = [
        f"https://www.freelancer.com/rss/jobs?keywords={quote(query or 'development')}",
        "https://www.freelancer.com/rss/jobs",
    ]
    
    for rss_url in rss_urls:
        try:
            logger.info(f"[FREELANCER-COM] Scraping: {rss_url[:80]}")
            response = req_lib.get(
                rss_url,
                headers={**HEADERS, "Accept": "application/rss+xml"},
                timeout=10
            )
            
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:limit]:
                    try:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        description = entry.get('summary', '')
                        
                        if search_term:
                            card_text = f"{title} {description}".lower()
                            if search_term not in card_text:
                                continue
                        
                        job = {
                            "title": title,
                            "company": "Freelancer.com",
                            "link": link.split('?')[0] if link else '',
                            "location": "Global",
                            "description": description[:500] if description else '',
                            "source": "Freelancer.com",
                            "contract_type": "Freelance",
                            "tjm": _extract_tjm_from_text(f"{title} {description}"),
                            "skills": _extract_skills_from_text(f"{title} {description}"),
                            "date": entry.get('published', ''),
                        }
                        jobs.append(job)
                        
                        if len(jobs) >= limit:
                            break
                            
                    except Exception as e:
                        logger.warning(f"[FREELANCER-COM] Entry parse error: {e}")
                        continue
                        
                if len(jobs) >= limit:
                    break
                    
        except Exception as e:
            logger.warning(f"[FREELANCER-COM] Error for {rss_url}: {e}")
            continue
    
    logger.info(f"[FREELANCER-COM] Returned {len(jobs)} jobs")
    return jobs[:limit]