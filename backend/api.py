import os
import re
import json
import sys
import urllib.parse
import logging
import time
import hashlib
import concurrent.futures
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body, Request

# Ensure the parent directory is in sys.path so 'shared' module is found
# This is needed because Railway starts the app from /app/backend/ but shared/ is at /app/shared/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import PyPDF2
from groq import Groq
try:
    import google.genai as genai
except ImportError:
    import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
import pandas as pd
from dotenv import load_dotenv
from shared.ai import call_ai_provider, analyze_cv as shared_analyze_cv, rank_jobs_with_ai as shared_rank_jobs, generate_cover_letter as shared_generate_letter, estimate_workload as shared_estimate_workload

# Config logging (must be before Redis setup)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import AI modules for enhanced scraping
try:
    from ai_modules.data_extraction import extract_job_data
    from ai_modules.deduplication import deduplicate_jobs
    from ai_modules.enrichment import enrich_job_data, enrich_jobs_batch
    from ai_modules.ranking import rank_jobs_ml
    AI_MODULES_AVAILABLE = True
    logger.info("✅ AI modules loaded successfully")
except ImportError as e:
    AI_MODULES_AVAILABLE = False
    logger.warning(f"⚠️ AI modules not available: {e}")

# Redis cache setup
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("✅ Redis cache connected")
except Exception as e:
    REDIS_AVAILABLE = False
    logger.warning(f"⚠️ Redis not available: {e}. Caching disabled.")

# Rate limiting setup
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute", "10/second"])

# Load environment variables
load_dotenv(override=True)

# Read keys from .env
api_key = os.getenv("GROQ_API_KEY", "").strip()
ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
xai_api_key = os.getenv("XAI_API_KEY", "").strip()
ft_client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "").strip()
ft_client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "").strip()
adzuna_app_id = os.getenv("ADZUNA_APP_ID", "").strip()
adzuna_app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
serpapi_key = os.getenv("SERPAPI_KEY", "").strip()
jooble_api_key = os.getenv("JOOBLE_API_KEY", "").strip()
apify_api_key = os.getenv("APIFY_API_KEY", "").strip()

# --- STARTUP DIAGNOSTIC ---
logger.info("=" * 60)
logger.info("FindMyJobAI Backend Startup Diagnostic")
logger.info("=" * 60)
logger.info(f"GROQ_API_KEY configured: {bool(api_key)}")
if api_key:
    logger.info(f"GROQ_API_KEY format valid (gsk_...): {api_key.startswith('gsk_')}")
    logger.info(f"GROQ_API_KEY preview: {api_key[:4]}...{api_key[-4:]}")
logger.info(f"GEMINI_API_KEY configured: {bool(gemini_api_key)}")
logger.info(f"Default model for CV analysis: Groq / Llama 3.3")
logger.info(f"If GROQ_API_KEY is missing, users must switch to Gemini 3.5 in the UI")
logger.info("=" * 60)

app = FastAPI(title="FindMyJobAI API", description="Backend API for React Prototype")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware to allow connection from React (usually on port 5173 or 3000)
# In production, replace ["*"] with specific origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8501,https://find-my-job-ai.netlify.app,https://*.netlify.app").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def extract_text_from_pdf(pdf_file) -> Optional[str]:
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text() or ""
            if content:
                text += content + "\n"
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return None

def is_ollama_online() -> bool:
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def clean_job_title(title: str) -> str:
    if not title: return ""
    if isinstance(title, list):
        title = " ".join(map(str, title))
    clean = title.lower()
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()

# Scraping / Job Search functions
def clean_html(text: str) -> str:
    try:
        return BeautifulSoup(text, "html.parser").get_text()
    except:
        return text

def scrape_france_travail_jobs(job_title: str, limit: int = 10) -> List[dict]:
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    jobs = []
    page = 1
    try:
        session = requests.Session()
        while len(jobs) < limit and page <= 5:
            url = f"https://candidat.pole-emploi.fr/offres/recherche?motsCles={query}&offresPartenaires=true&page={page}&sort=1"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200: break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li.result-resumes-item, article.offre, li[data-id-offre]')
            if not items:
                items = soup.select('div[class*="offre"], article.result, .media-body')
            if not items: break

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
        logger.error(f"Error scraping France Travail: {e}")
        return jobs

def get_france_travail_token() -> Optional[str]:
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
            return None
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"Error France Travail Auth: {e}")
        return None

def get_france_travail_jobs_api(job_title: str, limit: int = 10) -> List[dict]:
    token = get_france_travail_token()
    if not token:
        return []
    search_url = "https://api.pole-emploi.io/partenaire/offresdemploi/v2/offres/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "motsCles": job_title,
        "range": f"0-{limit-1}"
    }
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
        logger.error(f"Error official France Travail API: {e}")
        return []

def chercher_offres_jobspy(job_title: str, location: str = "Paris, France", limit: int = 10, selected_sites: List[str] = None) -> List[dict]:
    try:
        clean_title = clean_job_title(job_title)
        sites = [s.lower().replace(" ", "_") for s in selected_sites] if selected_sites else ["indeed", "linkedin", "glassdoor", "zip_recruiter"]
        
        # jobspy expects specific names
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
        logger.error(f"Error Jobspy: {e}")
        return []

def get_adzuna_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    if not adzuna_app_id or not adzuna_app_key:
        return []
    url = f"https://api.adzuna.com/v1/api/jobs/fr/search/1"
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
        logger.error(f"Adzuna API error: {e}")
        return []

def get_serpapi_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
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
        logger.error(f"SerpApi error: {e}")
        return []

def get_jooble_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
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
        logger.error(f"Jooble API error: {e}")
        return []

def get_apify_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    if not apify_api_key:
        return []
    url = "https://api.apify.com/v2/acts/apify~linkedin-jobs-scraper/run-sync-get-dataset-items"
    params = {"token": apify_api_key}
    payload = {
        "searchKeywords": job_title,
        "location": location,
        "maxItems": limit,
    }
    try:
        response = requests.post(url, params=params, json=payload, timeout=30)
        results = response.json()
        return [{
            "titre": res.get("title"),
            "entreprise": res.get("companyName", "N/C"),
            "lien": res.get("url"),
            "location": res.get("location", ""),
            "source": "LinkedIn"
        } for res in results]
    except Exception as e:
        logger.error(f"Apify API error: {e}")
        return []

def rank_jobs_with_ai(cv_data: dict, jobs: List[dict], filters: dict, ranking_engine: str = "Groq / Llama 3.3", custom_gemini_key: Optional[str] = None) -> List[dict]:
    """Wrapper pour utiliser la fonction partagée."""
    return shared_rank_jobs(
        cv_data=cv_data,
        jobs=jobs,
        filters=filters,
        target_lang="français",
        selected_model=ranking_engine,
        gemini_api_key=gemini_api_key,
        xai_api_key=xai_api_key,
        groq_api_key=api_key,
        ollama_url=ollama_url,
        custom_gemini_key=custom_gemini_key
    )

def get_cache_key(params: Dict[str, Any]) -> str:
    """Generate cache key from request parameters."""
    param_str = json.dumps(params, sort_keys=True)
    return f"job_search:{hashlib.md5(param_str.encode()).hexdigest()}"

# FastAPI schemas
class CvAnalysisRequest(BaseModel):
    selected_model: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"

class JobSearchRequest(BaseModel):
    query: str
    location: str = "Paris, France"
    num_ads: int = 10
    contract: str = "CDI"
    remote: bool = False
    global_search: bool = False
    selected_sources: List[str] = []
    sort_option: str = "Pertinence (IA)"
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_code: str = "fr"
    lang_label: str = "français"
    cv_data: Optional[dict] = None

class CoverLetterRequest(BaseModel):
    cv_data: dict
    job_title: str
    company: str
    job_description: Optional[str] = ""
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"
    is_freelance: Optional[bool] = False

class WorkloadEstimationRequest(BaseModel):
    mission_title: str
    mission_description: str
    cv_data: Optional[dict] = None
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"

# Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ollama_online": is_ollama_online()
    }

@app.get("/api/diagnostic")
def diagnostic():
    """Diagnostic endpoint to check API key configuration."""
    return {
        "groq_key_configured": bool(api_key and api_key.startswith("gsk_")),
        "gemini_key_configured": bool(gemini_api_key),
        "xai_key_configured": bool(xai_api_key),
        "ollama_configured": bool(ollama_url),
        "france_travail_configured": bool(ft_client_id and ft_client_secret),
        "adzuna_configured": bool(adzuna_app_id and adzuna_app_key),
        "serpapi_configured": bool(serpapi_key),
        "jooble_configured": bool(jooble_api_key),
        "apify_configured": bool(apify_api_key),
        "default_model": "Groq / Llama 3.3",
        "recommendation": "Configure GROQ_API_KEY in Railway environment variables, or switch to Gemini with a custom key in the UI."
    }

@app.post("/api/analyze-cv")
@limiter.limit("10/minute")  # Max 10 CV analyses per minute per IP
async def api_analyze_cv(
    request: Request,
    file: UploadFile = File(...),
    selected_model: str = Form("Groq / Llama 3.3"),
    custom_gemini_key: Optional[str] = Form(None),
    lang_label: str = Form("français")
):
    try:
        logger.info(f"Received CV upload request: filename={file.filename}, content_type={file.content_type}, model={selected_model}")
        
        # Check file extension (more permissive)
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Rejected file: not a PDF (filename={file.filename})")
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
        # Read PDF text
        try:
            contents = await file.read()
            logger.info(f"Read {len(contents)} bytes from PDF")
            
            if len(contents) == 0:
                raise HTTPException(status_code=400, detail="Le fichier PDF est vide.")
            
            import io
            pdf_file = io.BytesIO(contents)
            text = extract_text_from_pdf(pdf_file)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading PDF: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to read PDF file: {str(e)}")

        if not text or len(text) <= 50:
            logger.warning(f"Insufficient text extracted from PDF (length={len(text) if text else 0})")
            raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF. Please ensure your PDF contains readable text.")

        logger.info(f"Extracted {len(text)} characters from PDF, calling AI analysis...")
        
        # Call AI CV analysis with automatic fallback using shared function
        active_gemini_key = (custom_gemini_key or gemini_api_key or "").strip()
        fallback_used = None
        
        # Try the selected model first, then fallback
        models_to_try = []
        
        if "(Local/dev)" in selected_model:
            models_to_try.append(("local", selected_model))
            # Fallback: try Gemini if user provided a key
            if active_gemini_key:
                models_to_try.append(("gemini", "Gemini 3.5"))
            # Final fallback: try Groq if key exists
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", "Groq / Llama 3.3"))
        elif "Grok" in selected_model:
            if xai_api_key:
                models_to_try.append(("grok", selected_model))
            if active_gemini_key:
                models_to_try.append(("gemini", "Gemini 3.5"))
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", "Groq / Llama 3.3"))
        elif "Gemini" in selected_model:
            if active_gemini_key:
                models_to_try.append(("gemini", selected_model))
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", "Groq / Llama 3.3"))
        else:  # Groq / Llama 3.3 (default)
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", selected_model))
            if active_gemini_key:
                models_to_try.append(("gemini", "Gemini 3.5"))

        if not models_to_try:
            missing_keys = []
            if not active_gemini_key:
                missing_keys.append("- Clé Gemini (ajoutez votre clé personnelle dans le panneau latéral)")
            if not api_key:
                missing_keys.append("- Clé Groq (GROQ_API_KEY manquante sur le serveur)")
            error_msg = "Aucune clé API disponible pour l'analyse.\n" + "\n".join(missing_keys)
            raise HTTPException(status_code=500, detail=error_msg)

        data = None
        last_error = ""
        for provider, model in models_to_try:
            try:
                logger.info(f"Trying CV analysis with {provider} ({model})")
                data = shared_analyze_cv(
                    text=text,
                    target_lang=lang_label,
                    selected_model=model,
                    gemini_api_key=gemini_api_key,
                    xai_api_key=xai_api_key,
                    groq_api_key=api_key,
                    ollama_url=ollama_url,
                    custom_gemini_key=custom_gemini_key
                )
                if data:
                    if model != selected_model:
                        fallback_used = model
                    break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Fallback {model} failed: {e}")
                continue

        if not data:
            logger.error("All CV analysis attempts failed")
            raise HTTPException(
                status_code=500,
                detail=f"L'analyse CV a échoué avec tous les modèles disponibles. Dernière erreur: {last_error}"
            )

        if fallback_used:
            data["_fallback"] = fallback_used
            logger.info(f"CV analysis succeeded with fallback model: {fallback_used}")
        else:
            logger.info(f"CV analysis successful: metier={data.get('metier')}")
            
        return data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in api_analyze_cv: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/search-jobs")
@limiter.limit("20/minute")  # Max 20 searches per minute per IP
def api_search_jobs(request: Request, req: JobSearchRequest):
    all_results = []
    
    # Check cache first
    cache_key = None
    if REDIS_AVAILABLE:
        cache_key = get_cache_key(req.dict())
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {req.query}")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    # Concurrency using ThreadPool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {}
        
        js_sites = ["Indeed", "LinkedIn", "Google Jobs", "Glassdoor", "ZipRecruiter", "Simplyhired", "Careerbuilder", "Monster"]
        # If any of the Jobspy sites are selected
        if any(s in req.selected_sources for s in js_sites):
            futures['jobspy'] = executor.submit(chercher_offres_jobspy, req.query, req.location, req.num_ads, req.selected_sources)
        
        if "Adzuna" in req.selected_sources:
            futures['adzuna'] = executor.submit(get_adzuna_jobs, req.query, req.location, req.num_ads)
            
        if "Google Jobs" in req.selected_sources:
            futures['serpapi'] = executor.submit(get_serpapi_jobs, req.query, req.location, req.num_ads)
            
        if "Jooble" in req.selected_sources:
            futures['jooble'] = executor.submit(get_jooble_jobs, req.query, req.location, req.num_ads)
            
        if "LinkedIn" in req.selected_sources and "LinkedIn" not in js_sites: # fallback if not using jobspy
            futures['apify'] = executor.submit(get_apify_jobs, req.query, req.location, req.num_ads)

        # Collect Jobspy results
        if 'jobspy' in futures:
            try:
                jobspy_res = futures['jobspy'].result()
                for i, row in enumerate(jobspy_res):
                    site = str(row.get('site', 'Jobspy')).lower()
                    source_label = "LinkedIn" if site == "linkedin" else ("Google Jobs" if site == "google" else site.capitalize())
                    all_results.append({
                        "title": row.get('title', 'N/A'),
                        "company": row.get('company', 'N/A'),
                        "link": row.get('job_url', '#'),
                        "source": source_label,
                        "date": str(row.get('date_posted', '')),
                        "location": row.get('location', ''),
                        "desc": row.get('description', ''),
                        "id": f"js_{i}_{hash(row.get('job_url'))}"
                    })
            except Exception as e:
                logger.error(f"Jobspy Thread failed: {e}")

        # Collect Adzuna results
        if 'adzuna' in futures:
            try:
                adzuna_res = futures['adzuna'].result()
                for i, ad in enumerate(adzuna_res):
                    all_results.append({
                        "title": ad.get('titre'),
                        "company": ad.get('entreprise'),
                        "link": ad.get('lien'),
                        "source": "Adzuna",
                        "date": ad.get('date', ''),
                        "location": ad.get('location', ''),
                        "desc": "",
                        "id": f"api_adzuna_{i}_{hash(ad.get('lien'))}"
                    })
            except Exception as e:
                logger.error(f"Adzuna Thread failed: {e}")

        # Collect SerpApi results
        if 'serpapi' in futures:
            try:
                serpapi_res = futures['serpapi'].result()
                for i, ad in enumerate(serpapi_res):
                    all_results.append({
                        "title": ad.get('titre'),
                        "company": ad.get('entreprise'),
                        "link": ad.get('lien'),
                        "source": "Google Jobs",
                        "date": ad.get('date', ''),
                        "location": ad.get('location', ''),
                        "desc": "",
                        "id": f"api_googlejobs_{i}_{hash(ad.get('lien'))}"
                    })
            except Exception as e:
                logger.error(f"SerpApi Thread failed: {e}")

        # Collect Jooble results
        if 'jooble' in futures:
            try:
                jooble_res = futures['jooble'].result()
                for i, ad in enumerate(jooble_res):
                    all_results.append({
                        "title": ad.get('titre'),
                        "company": ad.get('entreprise'),
                        "link": ad.get('lien'),
                        "source": "Jooble",
                        "date": ad.get('date', ''),
                        "location": ad.get('location', ''),
                        "desc": "",
                        "id": f"api_jooble_{i}_{hash(ad.get('lien'))}"
                    })
            except Exception as e:
                logger.error(f"Jooble Thread failed: {e}")

    # France Travail search
    if "France Travail" in req.selected_sources:
        ft_results = []
        if ft_client_id and ft_client_secret:
            ft_results = get_france_travail_jobs_api(req.query, limit=req.num_ads)
        if not ft_results:
            ft_results = scrape_france_travail_jobs(req.query, limit=req.num_ads)
        for i, ad in enumerate(ft_results):
            all_results.append({
                "title": ad.get('title') or ad.get('titre'),
                "company": ad.get('company') or ad.get('entreprise'),
                "link": ad.get('link') or ad.get('lien'),
                "source": "France Travail",
                "date": "",
                "location": "",
                "desc": "",
                "id": f"api_francetravail_{i}_{hash(ad.get('link') or ad.get('lien'))}"
            })

    # Sort results
    if req.sort_option in ["Plus récentes", "Most recent", "Más recientes", "Neueste", "الأحدث", "最新順", "最新发布"]:
        all_results.sort(key=lambda x: x.get('date', ''), reverse=True)
    elif req.sort_option in ["Plus proches", "Closest", "Más cercanos", "Am nächsten", "الأقرب", "近い順", "距离最近"] and req.location:
        user_loc = req.location.lower()
        all_results.sort(key=lambda x: user_loc in x.get('location', '').lower(), reverse=True)
    elif req.sort_option in ["Pertinence (IA)", "Relevance (AI)", "Relevancia (AI)", "Relevanz (KI)", "الأكثر ملاءمة (ذكاء اصطnaعي)", "関連性 (AI)", "相关性 (AI)"] and req.cv_data and all_results:
        filters = {"contrat": req.contract, "remote": req.remote}
        all_results = rank_jobs_with_ai(
            req.cv_data, 
            all_results, 
            filters, 
            ranking_engine=req.ranking_engine, 
            custom_gemini_key=req.custom_gemini_key
        )

    # Collect source statistics
    source_counts = {}
    for res in all_results:
        src = res.get('source', 'Inconnue')
        source_counts[src] = source_counts.get(src, 0) + 1

    result = {
        "results": all_results,
        "source_counts": source_counts
    }

    # Cache result for 1 hour
    if REDIS_AVAILABLE and all_results and cache_key:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(result))
            logger.info(f"Cached result for query: {req.query}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    return result

@app.post("/api/generate-letter")
@limiter.limit("30/minute")  # Max 30 letter generations per minute per IP
def api_generate_letter(request: Request, req: CoverLetterRequest):
    try:
        letter = shared_generate_letter(
            cv_data=req.cv_data,
            job_title=req.job_title,
            company=req.company,
            job_description=req.job_description or "",
            target_lang=req.lang_label,
            selected_model=req.ranking_engine,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=api_key,
            ollama_url=ollama_url,
            custom_gemini_key=req.custom_gemini_key
        )
        if not letter:
            raise HTTPException(status_code=500, detail="Cover letter generation failed.")
        return {"letter": letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/estimate-workload")
@limiter.limit("20/minute")  # Max 20 workload estimations per minute per IP
def api_estimate_workload(request: Request, req: WorkloadEstimationRequest):
    try:
        workload = shared_estimate_workload(
            mission_description=req.mission_description,
            mission_title=req.mission_title,
            cv_data=req.cv_data,
            target_lang=req.lang_label,
            selected_model=req.ranking_engine,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=api_key,
            ollama_url=ollama_url,
            custom_gemini_key=req.custom_gemini_key
        )
        if not workload:
            raise HTTPException(status_code=500, detail="Workload estimation failed.")
        return {"workload": workload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)