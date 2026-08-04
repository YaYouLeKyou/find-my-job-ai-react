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
    """
    import requests as req_lib
    
    jobs = []
    
    # Method 1: Direct HTML scraping of Free-Work job board
    try:
        encoded_query = urllib.parse.quote(query)
        base_url = "https://www.free-work.com/fr/tech-it/jobs"
        
        # Build URL with search parameters
        params = {
            "q": query,
            "location": location if location != "France" else "",
        }
        
        logger.info(f"[FREE-WORK] Scraping URL: {base_url} with params: {params}")
        
        response = req_lib.get(base_url, params=params, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Free-Work uses specific CSS classes for job listings
            # Try multiple selectors as the site structure may change
            job_cards = soup.find_all("div", class_=lambda c: c and ("job" in c.lower() or "mission" in c.lower() or "offer" in c.lower() or "card" in c.lower()))
            
            if not job_cards:
                # Try article tags
                job_cards = soup.find_all("article", class_=lambda c: c and "job" in (c.lower() if c else ""))
            
            if not job_cards:
                # Try links to job detail pages
                job_cards = soup.find_all("a", href=lambda h: h and "/fr/tech-it/jobs/" in h)
            
            logger.info(f"[FREE-WORK] Found {len(job_cards)} job cards")
            
            for card in job_cards[:limit]:
                try:
                    # Extract job data
                    title_elem = card.find(["h2", "h3", "h4", "a"], class_=lambda c: c and "title" in (c.lower() if c else ""))
                    title = title_elem.get_text(strip=True) if title_elem else card.get("title", "")
                    
                    # If card is an <a> tag, get title from text
                    if not title and card.name == "a":
                        title = card.get_text(strip=True)
                    
                    link = card.get("href", "")
                    if link and not link.startswith("http"):
                        link = f"https://www.free-work.com{link}"
                    
                    # Extract company
                    company_elem = card.find(class_=lambda c: c and "company" in (c.lower() if c else ""))
                    company = company_elem.get_text(strip=True) if company_elem else ""
                    
                    # Extract location
                    location_elem = card.find(class_=lambda c: c and "location" in (c.lower() if c else ""))
                    job_location = location_elem.get_text(strip=True) if location_elem else location
                    
                    # Extract description/snippet
                    desc_elem = card.find("p")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Extract TJM
                    card_text = card.get_text(separator=" ", strip=True)
                    tjm = _extract_tjm_from_text(card_text)
                    
                    # Build job object
                    job = {
                        "title": title,
                        "company": company or "Free-Work",
                        "link": link or "#",
                        "location": job_location,
                        "description": description,
                        "source": "Free-Work",
                        "contract_type": "Freelance",
                        "tjm": tjm,
                        "skills": _extract_skills_from_text(f"{title} {description}"),
                    }
                    
                    if title:
                        jobs.append(job)
                        
                except Exception as e:
                    logger.warning(f"[FREE-WORK] Error parsing card: {e}")
                    continue
        else:
            logger.warning(f"[FREE-WORK] HTTP {response.status_code}")
            
    except Exception as e:
        logger.error(f"[FREE-WORK] HTML scraping failed: {e}")
    
    # Method 2: Fallback - use SerpApi to find Free-Work missions via Google
    if not jobs:
        try:
            from app.config import get_settings
            settings = get_settings()
            
            if settings.SERPAPI_KEY:
                serp_query = f'site:free-work.com/fr/tech-it/jobs "{query}" freelance'
                logger.info(f"[FREE-WORK] SerpApi fallback query: {serp_query}")
                
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
        except Exception as e:
            logger.warning(f"[FREE-WORK] SerpApi fallback failed: {e}")
    
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