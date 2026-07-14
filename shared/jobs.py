"""Fonctions de recherche d'emploi partagées (scraping + API)."""

import urllib.parse
import logging
from typing import Optional, List

import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs

from .utils import clean_job_title

logger = logging.getLogger(__name__)


def clean_html(text: str) -> str:
    """Nettoie le HTML d'un texte."""
    try:
        return BeautifulSoup(text, "html.parser").get_text()
    except Exception:
        return text


def scrape_france_travail_jobs(job_title: str, limit: int = 10) -> List[dict]:
    """Scraping France Travail (fallback si l'API officielle ne marche pas)."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    jobs = []
    page = 1
    try:
        while len(jobs) < limit and page <= 5:
            url = f"https://candidat.pole-emploi.fr/offres/recherche?motsCles={query}&offresPartenaires=true&page={page}&sort=1"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li.result-resumes-item, article.offre, li[data-id-offre]')
            if not items:
                items = soup.select('div[class*="offre"], article.result, .media-body')
            if not items:
                break

            for item in items:
                title_elem = item.select_one('h2.media-heading, .t4, .t5, a.titre, .media-heading')
                company_elem = item.select_one('p.sub-text, .nom-entreprise, span.entreprise')
                if title_elem:
                    jobs.append({
                        "title": title_elem.get_text(strip=True),
                        "company": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "link": "https://candidat.pole-emploi.fr" + title_elem.get('href', '#'),
                        "source": "France Travail"
                    })
            page += 1
        return jobs
    except Exception as e:
        logger.error(f"Erreur lors du scraping France Travail : {e}")
        return jobs


def get_france_travail_token(ft_client_id: str, ft_client_secret: str) -> Optional[str]:
    """Récupère le token OAuth2 pour l'API France Travail."""
    if not ft_client_id or not ft_client_secret:
        return None

    auth_url = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token"
    params = {"realm": "/partenaire"}
    data = {
        "grant_type": "client_credentials",
        "client_id": ft_client_id,
        "client_secret": ft_client_secret,
        "scope": "api_offresdemploiv2"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(auth_url, params=params, data=data, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Détails erreur France Travail : {response.text}")
            return None
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"Erreur France Travail Auth: {e}")
        return None


def get_france_travail_jobs_api(job_title: str, limit: int = 10,
                                ft_client_id: str = "", ft_client_secret: str = "") -> List[dict]:
    """Récupère les offres via l'API officielle France Travail."""
    token = get_france_travail_token(ft_client_id, ft_client_secret)
    if not token:
        return []

    search_url = "https://api.pole-emploi.io/partenaire/offresdemploi/v2/offres/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"motsCles": job_title, "range": f"0-{limit-1}"}
    try:
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 204:
            return []
        response.raise_for_status()
        results = response.json().get("resultats", [])
        return [{
            "titre": res.get("intitule"),
            "entreprise": res.get("entreprise", {}).get("nom", "Confidentiel"),
            "lien": f"https://candidat.pole-emploi.fr/offres/recherche/detail/{res.get('id')}",
            "source": "France Travail"
        } for res in results]
    except Exception as e:
        logger.error(f"Erreur API France Travail : {e}")
        return []


def chercher_offres_jobspy(job_title: str, location: str = "Paris, France",
                           limit: int = 10, selected_sites: Optional[List[str]] = None) -> List[dict]:
    """Recherche d'offres via la bibliothèque jobspy."""
    try:
        clean_title = clean_job_title(job_title)
        sites = [s.lower().replace(" ", "_") for s in selected_sites] if selected_sites else ["indeed", "linkedin", "glassdoor", "zip_recruiter"]

        valid_sites = []
        for s in sites:
            if s == "linkedin": valid_sites.append("linkedin")
            elif s == "indeed": valid_sites.append("indeed")
            elif s == "ziprecruiter": valid_sites.append("zip_recruiter")
            elif s == "glassdoor": valid_sites.append("glassdoor")

        if not valid_sites:
            valid_sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter"]

        jobs_df = scrape_jobs(
            site_name=valid_sites,
            search_term=clean_title,
            location=location,
            results_per_site=limit,
            hours_old=72
        )
        results = []
        if not jobs_df.empty:
            for _, row in jobs_df.iterrows():
                results.append({
                    "title": row.get("title", "Sans titre"),
                    "company": row.get("company", "Entreprise anonyme"),
                    "job_url": row.get("job_url", "#"),
                    "site": row.get("site", "Jobspy"),
                    "date_posted": str(row.get("date_posted", "")),
                    "location": row.get("location", ""),
                    "description": row.get("description", "")
                })
        return results
    except Exception as e:
        logger.error(f"Erreur Jobspy: {e}")
        return []


def get_adzuna_jobs(job_title: str, location: str = "France", limit: int = 10,
                    adzuna_app_id: str = "", adzuna_app_key: str = "") -> List[dict]:
    """Récupère des offres via l'API Adzuna."""
    if not adzuna_app_id or not adzuna_app_key:
        return []

    url = "https://api.adzuna.com/v1/api/jobs/fr/search/1"
    params = {
        "app_id": adzuna_app_id,
        "app_key": adzuna_app_key,
        "results_per_page": limit,
        "what": job_title,
        "where": location,
        "content-type": "application/json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        return [{
            "titre": res.get("title"),
            "entreprise": res.get("company", {}).get("display_name", "N/C"),
            "lien": res.get("redirect_url"),
            "date": res.get("created", ""),
            "location": res.get("location", {}).get("display_name", ""),
            "source": "Adzuna"
        } for res in results]
    except Exception as e:
        logger.error(f"❌ Adzuna API Error: {e}")
        return []


def get_serpapi_jobs(job_title: str, location: str = "France", limit: int = 10,
                     serpapi_key: str = "") -> List[dict]:
    """Récupère des offres via SerpApi (Google Jobs)."""
    if not serpapi_key:
        return []

    url = "https://serpapi.com/search"
    params = {
        "engine": "google_jobs",
        "q": job_title,
        "location": location,
        "hl": "fr",
        "api_key": serpapi_key
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("jobs_results", [])
        return [{
            "titre": res.get("title"),
            "entreprise": res.get("company_name", "N/C"),
            "lien": res.get("related_links", [{}])[0].get("link") if res.get("related_links") else "#",
            "date": res.get("detected_extensions", {}).get("posted_at", ""),
            "location": res.get("location", ""),
            "source": "Google Jobs"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"❌ SerpApi Error: {e}")
        return []


def get_jooble_jobs(job_title: str, location: str = "France", limit: int = 10,
                    jooble_api_key: str = "") -> List[dict]:
    """Récupère des offres via l'API Jooble."""
    if not jooble_api_key:
        return []

    url = f"https://jooble.org/api/{jooble_api_key}"
    try:
        response = requests.post(url, json={"keywords": job_title, "location": location}, timeout=10)
        response.raise_for_status()
        results = response.json().get("jobs", [])
        return [{
            "titre": clean_html(res.get("title", "")),
            "entreprise": res.get("company", "N/C"),
            "lien": res.get("link"),
            "date": res.get("updated", ""),
            "location": res.get("type", ""),
            "source": "Jooble"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"❌ Jooble API Error: {e}")
        return []


def get_apify_jobs(job_title: str, location: str = "France", limit: int = 10,
                   apify_api_key: str = "") -> List[dict]:
    """Récupère des offres via Apify (LinkedIn Scraper)."""
    if not apify_api_key:
        return []

    url = "https://api.apify.com/v2/acts/apify~linkedin-jobs-scraper/run-sync-get-dataset-items"
    params = {"token": apify_api_key}
    payload = {"searchKeywords": job_title, "location": location, "maxItems": limit}
    try:
        response = requests.post(url, params=params, json=payload, timeout=30)
        if response.status_code != 200:
            return []
        results = response.json()
        return [{
            "titre": res.get("title"),
            "entreprise": res.get("companyName", "N/C"),
            "lien": res.get("url"),
            "location": res.get("location", ""),
            "source": "LinkedIn (Apify)"
        } for res in results]
    except Exception as e:
        logger.error(f"❌ Apify API Error: {e}")
        return []