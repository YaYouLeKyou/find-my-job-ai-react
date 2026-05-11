import streamlit as st
from groq import Groq
import PyPDF2
import json
import os
import urllib.parse
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
import pandas as pd
import time
import re
import concurrent.futures
import logging

# --- LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION INITIALE ---
load_dotenv(override=True)  # Force le rechargement si le fichier .env change
api_key = os.getenv("GROQ_API_KEY", "").strip()
ft_client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "").strip()
ft_client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "").strip()
adzuna_app_id = os.getenv("ADZUNA_APP_ID", "").strip()
adzuna_app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
serpapi_key = os.getenv("SERPAPI_KEY", "").strip()
jooble_api_key = os.getenv("JOOBLE_API_KEY", "").strip()
apify_api_key = os.getenv("APIFY_API_KEY", "").strip()

if not api_key:
    st.error("⚠️ Clé API GROQ non trouvée. Veuillez vérifier votre fichier .env")

# Diagnostic de la clé Groq (Console)
if api_key:
    logger.info("--- Diagnostic Groq ---")
    logger.info(f"Clé détectée : {api_key[:4]}...{api_key[-4:]}")
    if not api_key.startswith("gsk_"):
        logger.error("❌ Format invalide : Une clé Groq doit commencer par 'gsk_'")
else:
    logger.warning("--- Diagnostic Groq ---")
    logger.error("❌ Aucune clé Groq détectée dans .env")

client = Groq(api_key=api_key) if api_key else None

def extract_text_from_pdf(file):
    """Extrait le texte d'un fichier PDF de manière sécurisée."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        if len(pdf_reader.pages) == 0:
            return None
            
        for page_num, page in enumerate(pdf_reader.pages):
            content = page.extract_text() or ""
            if content:
                text += content
        return text
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF : {e}")
        return None

def clean_job_title(title):
    """Nettoie le titre du poste pour optimiser la recherche (le dénominateur optimisé)."""
    if not title: return ""
    clean = title.lower()
    # Suppression des mentions H/F, F/H, etc., de manière robuste avec regex
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:)\b', ' ', clean)
    # On ne garde que la partie principale avant les séparateurs courants
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return clean.strip().capitalize()

def analyze_cv(text):
    """Envoie le texte à Groq et parse la réponse JSON."""
    if not client:
        return None
    
    prompt = f"""
    Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON avec les clés suivantes :
    "nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier), "recommandations_metiers" (liste de 5 métiers suggérés), "metiers_alternatifs" (liste de 3 métiers radicalement différents utilisant les mêmes compétences transférables), "suggestions_amelioration" (liste de 3 à 5 conseils concrets pour améliorer l'impact de ce CV).

    LOGIQUE D'IDENTIFICATION DU MÉTIER :
    - Si le profil contient des métiers multiples (ex: "Consultant & Développeur"), NE les regroupe PAS.
    - Sélectionne le métier le plus porteur/pertinent pour une recherche d'emploi actuelle comme "metier" principal.
    - Place le second métier (ou les métiers connexes identifiés) en priorité absolue au début de la liste "recommandations_metiers".

    Texte du CV :
    {text}
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )
        return json.loads(chat_completion.choices[0].message.content)
    except json.JSONDecodeError as je:
        st.error(f"L'IA n'a pas renvoyé un JSON valide : {je}")
        return None
    except Exception as e:
        if "401" in str(e):
            st.error("🔑 **Erreur d'authentification** : Votre clé `GROQ_API_KEY` est invalide. Vérifiez qu'elle est correcte dans votre fichier `.env` et qu'il s'agit bien d'une clé Groq (et non Gemini).")
        else:
            st.error(f"❌ **Erreur API Groq** : {str(e)}")
        return None

def generate_cover_letter(cv_data, job_title, company, job_description=""):
    """Génère une lettre de motivation personnalisée via Groq."""
    if not client or not cv_data:
        return None

    prompt = f"""
    Tu es un expert en recrutement. Rédige une lettre de motivation percutante, professionnelle et personnalisée.
    
    INFORMATIONS DU CANDIDAT :
    - Nom : {cv_data.get('nom_complet')}
    - Contact : {cv_data.get('contact')}
    - Métier : {cv_data.get('metier')}
    - Compétences : {', '.join(cv_data.get('mots_cles', []))}
    - Expérience : {cv_data.get('annees_experience')} ans
    - Résumé : {cv_data.get('resume')}

    INFORMATIONS DU POSTE :
    - Titre : {job_title}
    - Entreprise : {company}
    - Description (si dispo) : {job_description}

    La lettre doit être structurée (Vous/Moi/Nous), montrer une réelle adéquation entre le profil et le poste, et rester concise.
    Utilise les informations de contact pour l'en-tête et signe la lettre avec le nom du candidat. Réponds uniquement par le texte de la lettre, sans commentaires additionnels.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        return completion.choices[0].message.content
    except Exception as e:
        if "401" in str(e):
            st.error("🔑 **Erreur d'authentification** : Clé API Groq invalide lors de la génération de la lettre.")
        else:
            st.error(f"❌ **Erreur lors de la génération de la lettre** : {e}")
        return None

def generate_job_search_links(job_title, keywords):
    """Génère des URLs de recherche pour différentes plateformes."""
    query = job_title
    encoded_query = urllib.parse.quote(query)
    
    return {
        "Welcome to the Jungle": f"https://www.welcometothejungle.com/fr/jobs?query={encoded_query}",
        "HelloWork": f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={encoded_query}",
        "Meteojob": f"https://www.meteojob.com/jobsearch/search?what={encoded_query}",
        "Jobijoba": f"https://www.jobijoba.com/fr/recherche?q={encoded_query}",
        "Service Public (FR)": f"https://www.choisirleservicepublic.gouv.fr/nos-offres/filtres/mots-cles/{encoded_query}/",
        "We Work Remotely (Global)": f"https://weworkremotely.com/remote-jobs/search?term={encoded_query}",
        "Remote OK (Global)": f"https://remoteok.com/remote-{encoded_query.replace('%20', '-')}-jobs",
        "Working Nomads (Global)": f"https://www.workingnomads.com/remote-jobs?search={encoded_query}",
        "Remotive (Global)": f"https://remotive.com/remote-jobs?search={encoded_query}",
        "EuroJobs (Europe)": f"https://www.eurojobs.com/index.php?job_title={encoded_query}&location=",
        "Indeed (USA)": f"https://www.indeed.com/jobs?q={encoded_query}",
        "Indeed (UK)": f"https://uk.indeed.com/jobs?q={encoded_query}",
        "Indeed (Canada)": f"https://ca.indeed.com/jobs?q={encoded_query}",
        "StepStone (Allemagne)": f"https://www.stepstone.de/jobs/{encoded_query.replace('%20', '-')}",
        "Seek (Australie)": f"https://www.seek.com.au/{encoded_query.replace('%20', '-')}-jobs",
        "Idealist (Impact)": f"https://www.idealist.org/en/jobs?q={encoded_query}"
    }

def scrape_france_travail_jobs(job_title, limit=10):
    """Alternative par Scraping si l'API n'est pas disponible."""
    # Nettoyage du titre pour la recherche (on retire les parenthèses et détails superflus)
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
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code != 200: break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li.result-resumes-item, article.offre, li[data-id-offre]')
            
            if not items:
                items = soup.select('div[class*="offre"], article.result, .media-body')
            
            if not items: break

            for item in items:
                if len(jobs) >= limit: break
                title_elem = item.select_one('h2.media-heading, .t4, .t5, a.titre, .media-heading')
                company_elem = item.select_one('p.sub-text, .nom-entreprise, span.entreprise')
                link_elem = item.select_one('a[href*="detail"], a.btn-detail-offre')
                
                if title_elem:
                    href = link_elem['href'] if link_elem else "#"
                    jobs.append({
                        "titre": title_elem.get_text(strip=True),
                        "entreprise": company_elem.get_text(strip=True) if company_elem else "Entreprise non précisée",
                        "lien": "https://candidat.pole-emploi.fr" + href if href.startswith('/') else href
                    })
            page += 1
            
        return jobs
    except Exception as e:
        logger.error(f"Erreur lors du scraping France Travail : {e}")
        return jobs

def chercher_offres_jobspy(metier, contrat_label, remote_only, location="France, FR", num_results=5, experience=None):
    """Recherche des offres via JobSpy sur plusieurs plateformes."""
    # Mapping des types de contrat pour JobSpy
    job_type_map = {"CDI": "fulltime", "CDD": "contract", "Interim": "temporary"}
    
    clean_metier = clean_job_title(metier)
    if not clean_metier:
        clean_metier = metier

    # Sites à scanner (Indeed et LinkedIn sont les plus fiables en France)
    sites_to_try = ["indeed", "linkedin", "google", "glassdoor", "zip_recruiter", "simplyhired", "careerbuilder", "monster"]
    all_results = pd.DataFrame()

    for site in sites_to_try:
        try:
            time.sleep(1)  # Délai pour réduire les risques de bannissement IP
            search_location = location if location else "France"
            
            # Configuration de base
            search_params = {
                "site_name": [site],
                "search_term": clean_metier,
                "location": search_location,
                "results_wanted": num_results,
                "hours_old": 720,
                "job_type": job_type_map.get(contrat_label),
                "is_remote": remote_only,
                "enforce_desktop": True
            }

            if site == "indeed":
                search_params["country_indeed"] = "france"
            elif site == "linkedin":
                search_params["linkedin_fetch_full_description"] = False
                if "," in search_location: search_params["location"] = search_location.split(",")[0]
            elif site in ["google", "glassdoor", "zip_recruiter", "simplyhired"]:
                # Ces sites préfèrent souvent "France" tout court plutôt que "France, FR"
                if "France" in search_location: search_params["location"] = "France"
            
            results = scrape_jobs(**search_params)
            
            # Fallback 1 : On retire le filtre de type de contrat
            if (results is None or results.empty) and "job_type" in search_params:
                search_params.pop("job_type")
                results = scrape_jobs(**search_params)
            
            # Fallback 2 : On retire la limite temporelle
            if (results is None or results.empty) and "hours_old" in search_params:
                search_params.pop("hours_old")
                results = scrape_jobs(**search_params)

            # Fallback 3 : Recherche ultra-simplifiée (Titre brut)
            if (results is None or results.empty):
                search_params["search_term"] = metier # On utilise le titre non nettoyé
                # On garde results_wanted tel quel pour avoir un maximum de retours
                results = scrape_jobs(**search_params)

            if results is not None and not results.empty:
                all_results = pd.concat([all_results, results], ignore_index=True)
                
            # On continue la boucle pour interroger toutes les sources et remplir le dashboard, 
            # sauf si on a vraiment un volume massif d'offres (ex: 3x le demandé)
            if len(all_results) >= num_results * 3:
                break

        except Exception:
            # On ignore l'erreur spécifique à un site pour ne pas bloquer les autres
            continue
            
    if all_results.empty:
        st.info("💡 Note : Les plateformes externes (LinkedIn, Indeed...) bloquent souvent les requêtes automatiques. Privilégiez France Travail ou les liens d'accès direct.")
        
    return all_results

def get_france_travail_token():
    """Récupère le token OAuth2 pour l'API France Travail."""
    if not ft_client_id or not ft_client_secret:
        return None

    auth_url = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token"
    params = {"realm": "/partenaire"}
    data = {
        "grant_type": "client_credentials",
        "client_id": ft_client_id,
        "client_secret": ft_client_secret,
        "scope": "api_offresdemploiv2" # Simplifié pour éviter les erreurs si o2dso n'est pas activé
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

def get_france_travail_jobs_api(job_title, limit=10):
    """Récupère les offres via l'API officielle."""
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
        if response.status_code == 204: # Pas de contenu
            return []
        response.raise_for_status()
        
        results = response.json().get("resultats", [])
        jobs = []
        for res in results:
            jobs.append({
                "titre": res.get("intitule"),
                "entreprise": res.get("entreprise", {}).get("nom", "Confidentiel"),
                "lien": f"https://candidat.pole-emploi.fr/offres/recherche/detail/{res.get('id')}"
            })
        return jobs
    except Exception as e:
        st.error(f"Erreur lors de l'appel API France Travail : {e}")
        return []

def get_adzuna_jobs(job_title, location="France", limit=10):
    """Récupère des offres via l'API Adzuna (Stable et structuré)."""
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
            "source": "Adzuna"
        } for res in results]
    except Exception as e:
        logger.error(f"❌ Adzuna API Error: {e}")
        return []

def get_serpapi_jobs(job_title, location="France", limit=10):
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
            "source": "Google Jobs"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"❌ SerpApi Error: {e}")
        return []

def get_jooble_jobs(job_title, location="France", limit=10):
    """Récupère des offres via l'API Jooble."""
    if not jooble_api_key:
        return []
    
    url = f"https://jooble.org/api/{jooble_api_key}"
    try:
        response = requests.post(url, json={"keywords": job_title, "location": location}, timeout=10)
        response.raise_for_status()
        results = response.json().get("jobs", [])
        
        def clean_html(text):
            try:
                return BeautifulSoup(text, "html.parser").get_text()
            except:
                return text

        return [{
            "titre": clean_html(res.get("title", "")),
            "entreprise": res.get("company", "N/C"),
            "lien": res.get("link"),
            "source": "Jooble"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"❌ Jooble API Error: {e}")
        return []

def get_apify_jobs(job_title, location="France", limit=10):
    """Récupère des offres via Apify (LinkedIn Scraper)."""
    if not apify_api_key:
        return []
    
    # Exemple utilisant l'acteur apify/linkedin-jobs-scraper
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
            "source": "LinkedIn (Apify)"
        } for res in results]
    except Exception as e:
        logger.error(f"❌ Apify API Error: {e}")
        return []

def render_job_card(title, company, link, source, job_id, description=""):
    """Rendu générique d'une carte d'offre d'emploi pour éviter la duplication de code."""
    with st.container(border=True):
        st.markdown(f"### {title}")
        st.markdown(f"🏢 **{company}**")
        if source:
            st.caption(f"🏷️ Source : **{source}**")
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            st.link_button("🌐 Voir l'offre", link, use_container_width=True)
        with btn_c2:
            expander = st.expander("📝 Lettre")
        
        with expander:
            if 'user_cv_data' not in st.session_state:
                st.warning("Veuillez d'abord uploader votre CV.")
            else:
                letter_key = f"letter_{job_id}"
                if st.button(f"Générer la lettre (IA)", key=f"btn_{job_id}"):
                    with st.spinner("Rédaction en cours..."):
                        letter = generate_cover_letter(st.session_state['user_cv_data'], title, company, description)
                        if letter:
                            st.session_state[letter_key] = letter
                
                if letter_key in st.session_state:
                    st.text_area("Votre lettre personnalisée :", value=st.session_state[letter_key], height=400, key=f"area_{job_id}")
                    st.download_button("Télécharger la lettre (.txt)", st.session_state[letter_key], file_name=f"lettre_{company}.txt", key=f"dl_{job_id}")

def display_api_jobs(job_list, source_name):
    """Affiche une liste d'offres via le composant render_job_card."""
    if not job_list:
        return
    
    st.subheader(f"✨ Offres {source_name}")
    source_tag = "".join(filter(str.isalnum, source_name)).lower()
    for i, ad in enumerate(job_list):
        job_id = f"{source_tag}_{i}_{hash(ad['lien'])}"
        render_job_card(ad['titre'], ad['entreprise'], ad['lien'], ad.get('source', source_name), job_id)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Find me a job AI", page_icon="🚀", layout="centered")

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    /* Amélioration globale */
    .main { background-color: #f9fafb; }
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    /* Style des cartes */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #edf2f7 !important;
        background-color: white !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }
    /* Optimisation Mobile */
    @media (max-width: 640px) {
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        h1 { font-size: 1.8rem !important; }
        .stMarkdown div p { font-size: 0.95rem; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Find me a job AI")
st.markdown("#### Trouvez votre prochain emploi avec l'aide de l'IA")

# --- INITIALISATION DE L'ÉTAT ---
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

with st.sidebar:
    st.header("⚙️ Paramètres")
    num_ads = st.slider("Nombre d'annonces à afficher", min_value=1, max_value=50, value=10)
    contrat = st.selectbox("Type de contrat", ["CDI", "CDD", "Interim"])
    ville = st.text_input("📍 Ville / Département", value="France")
    remote = st.checkbox("Télétravail uniquement")

uploaded_file = st.file_uploader("📂 Glissez-déposez votre CV ici (PDF uniquement)", type="pdf")

if uploaded_file is not None:
    # On crée un identifiant unique pour le fichier pour éviter de re-analyser inutilement
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get('last_processed_file') != file_id:
        with st.spinner("Analyse du document en cours..."):
            cv_text = extract_text_from_pdf(uploaded_file)
            if cv_text:
                data = analyze_cv(cv_text)
                if data:
                    logger.info("--- Données brutes de l'analyse CV ---")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                    st.session_state['user_cv_data'] = data
                    st.session_state['search_query'] = clean_job_title(data.get("metier", ""))
                    st.session_state['last_processed_file'] = file_id
                    st.success("Analyse réussie !")
                    st.divider()
            else:
                st.warning("Impossible d'extraire du texte de ce PDF.")

# --- AFFICHAGE DU PROFIL ---
if 'user_cv_data' in st.session_state:
    data = st.session_state['user_cv_data']

    if data.get("nom_complet"):
        st.header(f"👤 {data['nom_complet']}")
    if data.get("contact"):
        st.caption(f"📩 {data['contact']}")

    col_profil, col_pistes = st.columns([1, 1])

    with col_profil:
        st.subheader("📋 Mon Profil")
        st.markdown(f"**Métier :** {data.get('metier', 'Non spécifié')}")
        st.markdown(f"**Expérience :** {data.get('annees_experience', 0)} an(s)")
        st.info(data.get("resume", "Pas de résumé disponible."))
        keywords = data.get("mots_cles", [])
        st.write(" ".join([f"`{kw}`" for kw in keywords]))
        
        if data.get("suggestions_amelioration"):
            st.markdown("---")
            st.markdown("✨ **Conseils d'amélioration**")
            for suggestion in data["suggestions_amelioration"]:
                st.markdown(f"📍 {suggestion}")

    with col_pistes:
        st.subheader("💡 Pistes d'évolution")
        for i, r in enumerate(data.get("recommandations_metiers", [])):
            if st.button(f"🔍 {r}", key=f"reco_{i}", use_container_width=True):
                st.session_state['search_query'] = r
                st.session_state['trigger_search'] = True
                st.rerun()
        
        st.subheader("🔀 Métiers Alternatifs")
        st.caption("Basés sur vos compétences transférables")
        for i, r in enumerate(data.get("metiers_alternatifs", [])):
            if st.button(f"🔄 {r}", key=f"alt_{i}", use_container_width=True):
                st.session_state['search_query'] = r
                st.session_state['trigger_search'] = True
                st.rerun()

# --- SECTION DE RECHERCHE D'OFFRES ---
st.divider()
st.subheader("🔍 Recherche d'opportunités")
st.info("Modifiez l'intitulé ci-dessous pour lancer une recherche personnalisée.")

# Préparation des options de recherche (Métier principal + Recommandations)
search_options = []
if 'user_cv_data' in st.session_state:
    cv_data = st.session_state['user_cv_data']
    primary = clean_job_title(cv_data.get("metier", ""))
    recos = [clean_job_title(r) for r in cv_data.get("recommandations_metiers", [])]
    # On crée une liste unique en gardant l'ordre
    search_options = list(dict.fromkeys([primary] + recos))

if search_options:
    st.caption("✨ Suggestions basées sur votre profil (cliquez pour remplir) :")
    # Affichage des suggestions sous forme de boutons rapides (chips)
    sugg_cols = st.columns(min(len(search_options), 4))
    for i, opt in enumerate(search_options[:4]):
        if sugg_cols[i].button(opt, key=f"chip_{i}", use_container_width=True):
            st.session_state['search_query'] = opt
            st.rerun()

col_input, col_btn = st.columns([2, 1])
with col_input:
    # Utilisation systématique de text_input pour permettre la saisie manuelle libre
    manual_query = st.text_input("Métier recherché :", value=st.session_state['search_query'], placeholder="Ex: Développeur Python, Serveur...", label_visibility="collapsed")

with col_btn:
    launch_search = st.button("🚀 Rechercher", use_container_width=True)

# Déclenchement automatique si on a cliqué sur une suggestion
if st.session_state.get('trigger_search'):
    launch_search = True
    st.session_state['trigger_search'] = False

# Initialisation de l'état pour les résultats
if 'offres' not in st.session_state:
    st.session_state['offres'] = None
if 'job_ads_ft' not in st.session_state:
    st.session_state['job_ads_ft'] = None

if launch_search and manual_query:
    # On mémorise la requête manuelle dans le state pour qu'elle persiste au rechargement
    st.session_state['search_query'] = manual_query
    with st.spinner(f"Scan global des plateformes en cours..."):
        exp_val = st.session_state.get('user_cv_data', {}).get('annees_experience')
        ville_search = ville if ville else "France"

        # Utilisation du multi-threading pour accélérer la recherche
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # On prépare les appels
            future_jobspy = executor.submit(chercher_offres_jobspy, manual_query, contrat, remote, ville_search, num_ads, exp_val)
            future_adzuna = executor.submit(get_adzuna_jobs, manual_query, ville_search, num_ads)
            future_serpapi = executor.submit(get_serpapi_jobs, manual_query, ville_search, num_ads)
            future_jooble = executor.submit(get_jooble_jobs, manual_query, ville_search, num_ads)
            future_apify = executor.submit(get_apify_jobs, manual_query, ville_search, num_ads)
            
            # Récupération des résultats JobSpy
            st.session_state['offres'] = future_jobspy.result()
            
            # Récupération des APIs
            st.session_state['job_ads_adzuna'] = future_adzuna.result()
            st.session_state['job_ads_serpapi'] = future_serpapi.result()
            st.session_state['job_ads_jooble'] = future_jooble.result()
            st.session_state['job_ads_apify'] = future_apify.result()
        
        # Cas particulier France Travail (gestion Token)
        st.session_state['job_ads_ft'] = []
        if ft_client_id and ft_client_secret:
            st.session_state['job_ads_ft'] = get_france_travail_jobs_api(manual_query, limit=num_ads)
        
        if not st.session_state['job_ads_ft']:
            st.session_state['job_ads_ft'] = scrape_france_travail_jobs(manual_query, limit=num_ads)

# --- TABLEAU DE BORD DES SOURCES ---
if st.session_state['offres'] is not None or st.session_state['job_ads_ft'] is not None:
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📊 État du Scan Global (Résultats intégrés)")
    
    # Extraction des statistiques
    js_df = st.session_state['offres']
    js_counts = js_df['site'].value_counts().to_dict() if js_df is not None and not js_df.empty else {}
    ft_count = len(st.session_state['job_ads_ft']) if st.session_state['job_ads_ft'] else 0
    adzuna_count = len(st.session_state.get('job_ads_adzuna', []))
    serpapi_count = len(st.session_state.get('job_ads_serpapi', []))
    jooble_count = len(st.session_state.get('job_ads_jooble', []))
    apify_count = len(st.session_state.get('job_ads_apify', []))
    
    # Configuration des sources à afficher
    source_list = [
        ("linkedin", "LinkedIn"),
        ("indeed", "Indeed"),
        ("glassdoor", "Glassdoor"),
        ("google", "Google Jobs"),
        ("zip_recruiter", "ZipRecruiter"),
        ("simplyhired", "SimplyHired"),
        ("careerbuilder", "CareerBuilder"),
        ("monster", "Monster"),
        ("france_travail", "FT / Pôle Emploi"),
        ("adzuna", "Adzuna (Premium)"),
        ("serpapi", "Google Jobs (Serp)"),
        ("jooble", "Jooble API"),
        ("apify", "LinkedIn (Apify)")
    ]
    
    # Filtrage des sources avec résultats et log console pour les autres
    active_sources = []
    for key, label in source_list:
        if key == "france_travail":
            count = ft_count
        elif key == "adzuna":
            count = adzuna_count
        elif key == "serpapi":
            count = serpapi_count
        elif key == "jooble":
            count = jooble_count
        elif key == "apify":
            count = apify_count
        else:
            count = js_counts.get(key, 0)
        
        if count > 0:
            active_sources.append((label, count))
        else:
            logger.info(f"🔍 [Console Scan] Aucun résultat trouvé pour : {label}")

    # Affichage en grille des sources actives uniquement
    rows = [active_sources[i:i + 4] for i in range(0, len(active_sources), 4)]
    for row in rows:
        status_cols = st.columns(len(row))
        for idx, (label, count) in enumerate(row):
            status_cols[idx].markdown(f"""
                <div style="text-align:center; padding:8px; border-radius:8px; background-color:#d4edda; border:1px solid rgba(0,0,0,0.1); margin-bottom:5px;">
                    <small style="font-size:0.75rem;">{label}</small><br><b>✅ {count}</b>
                </div>
            """, unsafe_allow_html=True)

    # --- NOUVELLE SECTION : ACCÈS DIRECT ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🚀 Accès Direct (Autres plateformes)")
    st.caption("Ces plateformes protègent leurs données contre l'IA, mais nous avons optimisé vos liens de recherche pour un accès rapide :")
    
    links = generate_job_search_links(manual_query, [])
    link_rows = [list(links.items())[i:i + 3] for i in range(0, len(links), 3)]
    for row in link_rows:
        cols = st.columns(len(row))
        for i, (name, url) in enumerate(row):
            cols[i].link_button(f"🔍 {name}", url, use_container_width=True)

# Affichage des résultats (en dehors du bloc 'if launch_search')
if st.session_state['offres'] is not None and not st.session_state['offres'].empty:
    offres = st.session_state['offres']
    st.success(f"{len(offres)} offres trouvées via le scanner multi-plateformes")

    for i, (_, row) in enumerate(offres.iterrows()):
        # On ajoute un préfixe 'js' et l'index pour éviter les collisions avec les APIs
        job_id = f"js_{i}_{row.get('id', row.get('job_url'))}"
        render_job_card(
            row.get('title', 'Poste sans titre'),
            row.get('company', 'Entreprise inconnue'),
            row.get('job_url', '#'),
            row.get('site', 'Plateforme').capitalize(),
            job_id,
            row.get('description', "")
        )

# Affichage des offres via API (Plus stables)
display_api_jobs(st.session_state.get('job_ads_apify'), "LinkedIn (Apify)")
display_api_jobs(st.session_state.get('job_ads_serpapi'), "Google Jobs (SerpApi)")
display_api_jobs(st.session_state.get('job_ads_jooble'), "Jooble")
display_api_jobs(st.session_state.get('job_ads_adzuna'), "Adzuna")
display_api_jobs(st.session_state.get('job_ads_ft'), "France Travail")

# Message d'alerte si rien n'est trouvé après une recherche
if st.session_state['offres'] is not None:
    all_empty = (
        st.session_state['offres'].empty and 
        not st.session_state.get('job_ads_ft') and
        not st.session_state.get('job_ads_adzuna') and
        not st.session_state.get('job_ads_serpapi') and
        not st.session_state.get('job_ads_jooble') and
        not st.session_state.get('job_ads_apify')
    )
    if all_empty:
        st.warning("⚠️ Aucune offre trouvée. Essayez de simplifier l'intitulé du métier ou de changer la ville.")

st.caption("Propulsé par Streamlit, Groq & Llama 3")
