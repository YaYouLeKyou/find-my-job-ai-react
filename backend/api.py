import os
import re
import json
import urllib.parse
import logging
import concurrent.futures
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import PyPDF2
from groq import Groq
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
import pandas as pd
from dotenv import load_dotenv

# Config logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

app = FastAPI(title="FindMyJobAI API", description="Backend API for React Prototype")

# CORS middleware to allow connection from React (usually on port 5173 or 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For prototype, allow all origins
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

def call_local_llama(prompt: str, model_name: str, is_json: bool = False) -> Optional[str]:
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json" if is_json else ""
        }
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=90)
        if response.status_code == 200:
            return response.json().get("response")
        else:
            logger.error(f"Ollama error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Ollama local error: {e}")
        return None

def call_ai_provider(prompt: str, selected_model: str, is_json: bool = False, custom_gemini_key: Optional[str] = None) -> Optional[str]:
    active_gemini_key = (custom_gemini_key or gemini_api_key or "").strip()
    try:
        if "Gemini" in selected_model:
            if not active_gemini_key:
                raise Exception("Clé API Gemini manquante.")
            genai.configure(api_key=active_gemini_key)
            model_id = "models/gemini-2.0-flash" if "3.5" in selected_model else "models/gemini-1.5-flash"
            logger.info(f"Calling Gemini AI: {model_id}")
            model = genai.GenerativeModel(model_id)
            generation_config = {"response_mime_type": "application/json", "temperature": 0.1} if is_json else {"temperature": 0.7}
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
            
            if response.candidates and response.candidates[0].finish_reason != 1:
                reason = response.candidates[0].finish_reason
                if reason == 3:
                    raise Exception("L'analyse a été bloquée par les filtres de sécurité de Google.")
            
            text = response.text
            if is_json:
                json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
                if json_match:
                    text = json_match.group(1)
            return text
            
        elif "(Local/dev)" in selected_model:
            model_map = {
                "Llama 3.2 Vision (Local/dev)": "llama3.2-vision",
                "Llama 3.2 (Local/dev)": "llama3.2",
                "Qwen 3 4B (Local/dev)": "qwen3:4b"
            }
            ollama_model = model_map.get(selected_model, "llama3.2")
            return call_local_llama(prompt, ollama_model, is_json=is_json)
            
        elif "Grok" in selected_model:
            if not xai_api_key:
                raise Exception("Clé API xAI (Grok) non configurée.")
            headers = {
                "Authorization": f"Bearer {xai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        else:
            # Groq / Llama 3.3
            if not api_key:
                raise Exception("Clé Groq non configurée")
            client = Groq(api_key=api_key)
            params = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "llama-3.3-70b-versatile",
            }
            if is_json:
                params["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"Error calling AI Provider ({selected_model}): {e}")
        raise e

def clean_job_title(title: str) -> str:
    if not title: return ""
    if isinstance(title, list):
        title = " ".join(map(str, title))
    clean = title.lower()
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()

def analyze_cv(text: str, target_lang: str = "français", selected_model: str = "Groq / Llama 3.3", custom_gemini_key: Optional[str] = None) -> Optional[dict]:
    prompt = f"""
    Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON en {target_lang} avec les clés suivantes :
    "nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier), "recommandations_metiers" (liste de 5 métiers suggérés), "metiers_alternatifs" (liste de 3 métiers radicalement différents utilisant les mêmes compétences transférables), "suggestions_amelioration" (liste de 3 à 5 conseils concrets pour améliorer l'impact de ce CV).

    LOGIQUE D'IDENTIFICATION DU MÉTIER :
    - Si le profil contient des métiers multiples (ex: "Consultant & Développeur"), NE les regroupe PAS.
    - Sélectionne le métier le plus porteur/pertinent pour une recherche d'emploi actuelle comme "metier" principal.
    - Place le second métier (ou les métiers connexes identifiés) en priorité absolue au début de la liste "recommandations_metiers".

    Texte du CV :
    {text}
    """
    try:
        response_text = call_ai_provider(prompt, selected_model, is_json=True, custom_gemini_key=custom_gemini_key)
        if not response_text:
            return None
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Error in CV analysis: {e}")
        return None

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
    if not jobs or not cv_data:
        return jobs
    limit_tri = 20
    jobs_to_rank = jobs[:limit_tri]
    job_list_text = "\n".join([f"{i} | {j['title']} @ {j['company']}" for i, j in enumerate(jobs_to_rank)])
    
    prompt = f"""
    Tu es un expert en recrutement. Évalue la compatibilité (0 à 100%) entre le profil du candidat et les offres d'emploi suivantes.
    
    FILTRES CRITIQUES :
    - Type de contrat recherché : {filters.get('contrat')}
    - Télétravail : {'Oui' if filters.get('remote') else 'Non spécifié'}

    PROFIL CANDIDAT : {cv_data.get('metier')} ({cv_data.get('annees_experience')} ans d'exp). Compétences clés: {', '.join(cv_data.get('mots_cles', []))}
    
    LISTE DES OFFRES (format "index | titre @ entreprise") :
    {job_list_text}

    INSTRUCTIONS :
    Retourne UNIQUEMENT un objet JSON avec une clé "ranking" contenant une liste d'objets : 
    {{"ranking": [{{"id": index_numérique, "score": score_entier_0_a_100}}]}}
    L'ID doit être uniquement le numéro d'index fourni.
    """
    try:
        response_text = call_ai_provider(prompt, ranking_engine, is_json=True, custom_gemini_key=custom_gemini_key)
        if not response_text:
            return jobs
        ranking_data = json.loads(response_text).get("ranking", [])
        ranked_list = []
        ranked_indices = []
        for item in ranking_data:
            try:
                idx_raw = item.get("id")
                score_raw = item.get("score")
                if isinstance(idx_raw, str):
                    idx_match = re.search(r'\d+', idx_raw)
                    if idx_match:
                        idx_raw = idx_match.group()
                if idx_raw is not None:
                    idx = int(idx_raw)
                    score = int(score_raw) if score_raw is not None else 0
                    if idx < len(jobs_to_rank):
                        job = {**jobs_to_rank[idx], "match_score": score}
                        ranked_list.append(job)
                        ranked_indices.append(idx)
            except:
                continue
        for i in range(len(jobs_to_rank)):
            if i not in ranked_indices:
                ranked_list.append(jobs_to_rank[i])
        if len(jobs) > limit_tri:
            ranked_list.extend(jobs[limit_tri:])
        return ranked_list
    except Exception as e:
        logger.error(f"Error ranking jobs: {e}")
        return jobs

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

# Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ollama_online": is_ollama_online()
    }

@app.post("/api/analyze-cv")
async def api_analyze_cv(
    file: UploadFile = File(...),
    selected_model: str = Form("Groq / Llama 3.3"),
    custom_gemini_key: Optional[str] = Form(None),
    lang_label: str = Form("français")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Read PDF text
    try:
        contents = await file.read()
        import io
        pdf_file = io.BytesIO(contents)
        text = extract_text_from_pdf(pdf_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF file: {str(e)}")

    if not text or len(text) <= 50:
        raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF.")

    # Call AI CV analysis
    data = analyze_cv(text, target_lang=lang_label, selected_model=selected_model, custom_gemini_key=custom_gemini_key)
    if not data:
        raise HTTPException(status_code=500, detail="CV Analysis failed. Please check AI key or model availability.")
        
    return data

@app.post("/api/search-jobs")
def api_search_jobs(req: JobSearchRequest):
    all_results = []
    
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

    return {
        "results": all_results,
        "source_counts": source_counts
    }

@app.post("/api/generate-letter")
def api_generate_letter(req: CoverLetterRequest):
    prompt = f"""
    Tu es un expert en recrutement. Rédige une lettre de motivation percutante, professionnelle et personnalisée en {req.lang_label}.
    
    INFORMATIONS DU CANDIDAT :
    - Nom : {req.cv_data.get('nom_complet')}
    - Contact : {req.cv_data.get('contact')}
    - Métier : {req.cv_data.get('metier')}
    - Compétences : {', '.join(req.cv_data.get('mots_cles', []))}
    - Expérience : {req.cv_data.get('annees_experience')} ans
    - Résumé : {req.cv_data.get('resume')}

    INFORMATIONS DU POSTE :
    - Titre : {req.job_title}
    - Entreprise : {req.company}
    - Description (si dispo) : {req.job_description}

    La lettre doit être structurée (Vous/Moi/Nous), montrer une réelle adéquation entre le profil et le poste, et rester concise.
    Utilise les informations de contact pour l'en-tête et signe la lettre avec le nom du candidat. Réponds uniquement par le texte de la lettre, sans commentaires additionnels.
    """
    try:
        letter = call_ai_provider(prompt, req.ranking_engine, is_json=False, custom_gemini_key=req.custom_gemini_key)
        if not letter:
            raise HTTPException(status_code=500, detail="Cover letter generation failed.")
        return {"letter": letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
