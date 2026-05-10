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

# --- CONFIGURATION INITIALE ---
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
ft_client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
ft_client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")

if not api_key:
    st.error("⚠️ Clé API GROQ non trouvée. Veuillez vérifier votre fichier .env")

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
    # Suppression des mentions inutiles pour les moteurs de recherche
    for word in ['h/f', 'f/h', 'hf', 'fh', 'métier:']:
        clean = clean.replace(word, ' ')
    # On ne garde que la partie principale avant les séparateurs
    for sep in [',', '(', '-', ':', '&', '/', '|']:
        clean = clean.split(sep)[0]
    return " ".join(clean.split()).capitalize()

def analyze_cv(text):
    """Envoie le texte à Groq et parse la réponse JSON."""
    if not client:
        return None
    
    prompt = f"""
    Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON avec les clés suivantes :
    "nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier), "recommandations_metiers" (liste de 5 métiers suggérés), "metiers_alternatifs" (liste de 3 métiers radicalement différents utilisant les mêmes compétences transférables).

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
        st.error(f"Détails de l'erreur API : {str(e)}")
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
        st.error(f"Erreur lors de la génération de la lettre : {e}")
        return None

def generate_job_search_links(job_title, keywords):
    """Génère des URLs de recherche pour différentes plateformes."""
    query = f"{job_title} {' '.join(keywords[:3])}"  # On prend le métier + les 3 premiers mots-clés
    encoded_query = urllib.parse.quote(query)
    
    return {
        "Indeed": f"https://fr.indeed.com/jobs?q={encoded_query}",
        "France Travail": f"https://candidat.pole-emploi.fr/offres/recherche?motsCles={encoded_query}",
        "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}",
        "Welcome to the Jungle": f"https://www.welcometothejungle.com/fr/jobs?query={encoded_query}"
    }

def scrape_france_travail_jobs(job_title, limit=10):
    """Alternative par Scraping si l'API n'est pas disponible."""
    # Nettoyage du titre pour la recherche (on retire les parenthèses et détails superflus)
    clean_title = job_title.lower().replace('h/f', '').replace('métier:', '').strip()
    clean_title = clean_title.split(',')[0].split('(')[0].split('-')[0].strip()
    
    query = urllib.parse.quote(clean_title)
    url = f"https://candidat.pole-emploi.fr/offres/recherche?motsCles={query}&offresPartenaires=true"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Recherche plus large de balises de résultats
        items = soup.find_all(['li', 'div'], class_=['result', 'offre'])
        
        for item in items[:limit]:
            title_elem = item.find(['h2', 'h3', 'a'])
            company_elem = item.find(['p', 'span'], class_=['sub-text', 'media-heading-text', 'nom-entreprise'])
            link_elem = item.find('a', href=True)
            
            if title_elem and link_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": company_elem.get_text(strip=True) if company_elem else "Entreprise non précisée",
                    "lien": "https://candidat.pole-emploi.fr" + link_elem['href']
                })
        return jobs
    except Exception as e:
        st.error(f"Erreur lors du scraping France Travail : {e}")
        return []

def chercher_offres_jobspy(metier, contrat_label, remote_only, location="France", num_results=5, experience=None):
    """Recherche des offres via JobSpy sur plusieurs plateformes."""
    # Mapping des types de contrat pour JobSpy
    job_type_map = {"CDI": "fulltime", "CDD": "contract", "Interim": "temporary"}
    
    search_term = f"{metier} {experience} ans d'expérience" if experience else metier
    clean_metier = clean_job_title(metier)
    if not clean_metier:
        clean_metier = metier

    # Essai sur plusieurs sites un par un pour éviter les blocages globaux
    sites_to_try = ["indeed", "linkedin"]
    all_jobs = pd.DataFrame()

    try:
        # Tentative 1 : Avec filtres
        for site in sites_to_try:
            res = scrape_jobs(
                site_name=[site],
                search_term=f"{clean_metier} {experience} ans" if experience else clean_metier,
                location=location,
                results_wanted=num_results,
                hours_old=720,
                job_type=job_type_map.get(contrat_label),
                is_remote=remote_only
            )
            if not res.empty:
                all_jobs = pd.concat([all_jobs, res], ignore_index=True)
        
        # Tentative 2 : Sans filtres (si toujours rien)
        if all_jobs.empty:
            all_jobs = scrape_jobs(
                site_name=["indeed"],
                search_term=clean_metier,
                location=location,
                results_wanted=num_results,
                hours_old=720
            )
        return all_jobs
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=1400)  # Le token dure environ 25 minutes
def get_france_travail_token():
    """Récupère le token OAuth2 pour l'API France Travail."""
    auth_url = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire"
    data = {
        "grant_type": "client_credentials",
        "client_id": ft_client_id,
        "client_secret": ft_client_secret,
        "scope": "api_offresdemploiv2 o2dso"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(auth_url, data=data, headers=headers)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        st.error(f"Erreur d'authentification France Travail : {e}")
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
        st.error(f"Erreur API France Travail : {e}")
        return []

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

    st.divider()
    with st.expander("Voir les données brutes"):
        st.json(data)

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

col_input, col_btn = st.columns([2, 1])
with col_input:
    if search_options:
        manual_query = st.selectbox("Métier cible :", 
                                    options=search_options, 
                                    index=search_options.index(st.session_state['search_query']) if st.session_state['search_query'] in search_options else 0,
                                    label_visibility="collapsed")
    else:
        manual_query = st.text_input("Métier recherché :", value=st.session_state['search_query'], label_visibility="collapsed")

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
    with st.spinner(f"Recherche en cours pour '{manual_query}'..."):
        # On récupère l'expérience extraite si elle existe
        exp_val = st.session_state.get('user_cv_data', {}).get('annees_experience')
        
        offres = chercher_offres_jobspy(manual_query, contrat, remote, location=ville, num_results=num_ads, experience=exp_val)
        st.session_state['offres'] = offres
        if offres.empty:
            st.session_state['job_ads_ft'] = scrape_france_travail_jobs(manual_query, limit=num_ads)
        else:
            st.session_state['job_ads_ft'] = None

# Affichage des résultats (en dehors du bloc 'if launch_search')
if st.session_state['offres'] is not None and not st.session_state['offres'].empty:
    offres = st.session_state['offres']
    st.success(f"{len(offres)} offres trouvées sur Indeed/LinkedIn/Glassdoor")
    
    for _, row in offres.iterrows():
        job_id = f"job_{row.get('id', row.get('job_url'))}"
        with st.container(border=True):
            st.markdown(f"### {row.get('title', 'Poste sans titre')}")
            st.markdown(f"🏢 **{row.get('company', 'Entreprise inconnue')}**")
            st.markdown(f"📍 {row.get('location', 'Lieu non précisé')}")

            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                st.link_button("🌐 Voir l'offre", row.get('job_url', '#'), use_container_width=True)
            with btn_c2:
                expander_letter = st.expander("📝 Lettre")
            with expander_letter:
                if 'user_cv_data' not in st.session_state:
                    st.warning("Veuillez d'abord uploader votre CV.")
                else:
                    # On stocke la lettre dans le state pour qu'elle reste affichée après génération
                    letter_key = f"letter_{job_id}"
                    if st.button(f"Générer la lettre (IA)", key=f"btn_{job_id}"):
                        with st.spinner("Rédaction en cours..."):
                            desc = row.get('description', "")
                            letter = generate_cover_letter(st.session_state['user_cv_data'], row['title'], row['company'], desc)
                            if letter:
                                st.session_state[letter_key] = letter
                    
                    if letter_key in st.session_state:
                        st.text_area("Votre lettre personnalisée :", value=st.session_state[letter_key], height=400, key=f"area_{job_id}")
                        st.download_button("Télécharger la lettre (.txt)", st.session_state[letter_key], file_name=f"lettre_{row.get('company', 'entreprise')}.txt", key=f"dl_{job_id}")

elif st.session_state['job_ads_ft'] is not None:
    for ad in st.session_state['job_ads_ft']:
        with st.container(border=True):
            st.markdown(f"**{ad['titre']}** @ {ad['entreprise']}")
            st.link_button("Voir l'offre", ad['lien'])

st.caption("Propulsé par Streamlit, Groq & Llama 3")
