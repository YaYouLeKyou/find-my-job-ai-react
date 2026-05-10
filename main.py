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

def analyze_cv(text):
    """Envoie le texte à Groq et parse la réponse JSON."""
    if not client:
        return None
    
    prompt = f"""
    Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON avec les clés suivantes :
    "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes).

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
    except Exception:
        return []

def chercher_offres_jobspy(metier, contrat_label, remote_only, location="France", num_results=5):
    """Recherche des offres via JobSpy sur plusieurs plateformes."""
    # Mapping des types de contrat pour JobSpy
    job_type_map = {"CDI": "fulltime", "CDD": "contract", "Interim": "temporary"}
    
    # Nettoyage profond du métier : on ne garde que l'intitulé principal
    clean_metier = metier.lower().replace('h/f', '').replace('métier:', '').strip()
    clean_metier = clean_metier.split(',')[0].split('(')[0].split('-')[0].strip()
    
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
                search_term=clean_metier,
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
st.set_page_config(page_title="IA CV Scanner", page_icon="📄", layout="centered")

st.title("📄 Analyseur de CV Intelligent")
st.markdown("Extrayez instantanément les compétences clés grâce à **Groq & Llama 3**.")

# --- INITIALISATION DE L'ÉTAT ---
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

with st.sidebar:
    st.header("⚙️ Paramètres")
    num_ads = st.slider("Nombre d'annonces à afficher", min_value=1, max_value=20, value=10)
    contrat = st.selectbox("Type de contrat", ["CDI", "CDD", "Interim"])
    ville = st.text_input("Ville / Département", value="France")
    remote = st.checkbox("Télétravail uniquement")

uploaded_file = st.file_uploader("Déposez votre CV (PDF uniquement)", type="pdf")

if uploaded_file is not None:
    # Affichage d'un spinner pendant le traitement
    with st.spinner("Analyse du document en cours..."):
        # 1. Extraction du texte
        cv_text = extract_text_from_pdf(uploaded_file)
        
        if cv_text:
            # 2. Analyse par Gemini
            data = analyze_cv(cv_text)
            
            if data:
                # Mise à jour de l'intitulé pour la recherche
                st.session_state['search_query'] = data.get("metier", "")
                st.success("Analyse réussie !")
                st.divider()
                
                # Mise en page des résultats
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("👨‍💼 Métier identifié")
                    st.info(data.get("metier", "Non spécifié"))
                    
                    st.subheader("🛠️ Compétences techniques")
                    keywords = data.get("mots_cles", [])
                    # Affichage sous forme de tags
                    st.write(" ".join([f" `{kw}`" for kw in keywords]))
                
                with col2:
                    st.subheader("📝 Résumé professionnel")
                    st.write(data.get("resume", "Pas de résumé disponible."))
                
                st.divider()
                # Option pour voir le JSON brut
                with st.expander("Voir les données brutes"):
                    st.json(data)

        else:
            st.warning("Impossible d'extraire du texte de ce PDF.")

# --- SECTION DE RECHERCHE D'OFFRES ---
st.divider()
st.subheader("🔍 Recherche d'opportunités")
st.info("Modifiez l'intitulé ci-dessous pour lancer une recherche personnalisée.")

col_input, col_btn = st.columns([3, 1])
with col_input:
    manual_query = st.text_input("Métier recherché :", value=st.session_state['search_query'], label_visibility="collapsed")
with col_btn:
    launch_search = st.button("🚀 Rechercher", use_container_width=True)

if launch_search:
    if manual_query:
        with st.spinner(f"Recherche en cours pour '{manual_query}'..."):
            offres = chercher_offres_jobspy(manual_query, contrat, remote, location=ville, num_results=num_ads)
        
        if not offres.empty:
            st.success(f"{len(offres)} offres trouvées sur Indeed/LinkedIn/Glassdoor")
            
            # Nettoyage des colonnes
            cols_to_show = ['title', 'company', 'location', 'job_url']
            for col in cols_to_show:
                if col not in offres.columns:
                    offres[col] = "Non précisé"
            
            if 'job_url' in offres.columns:
                offres['job_url'] = offres['job_url'].apply(lambda x: x if str(x).startswith('http') else f"https://{x}")

            display_df = offres[cols_to_show].copy()
            display_df.columns = ['Poste', 'Entreprise', 'Lieu', 'Lien']
            
            st.dataframe(
                display_df,
                column_config={"Lien": st.column_config.LinkColumn("🔗 Ouvrir l'annonce")},
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Aucun résultat sur les plateformes majeures. Tentative sur France Travail...")
            job_ads = scrape_france_travail_jobs(manual_query, limit=num_ads)
            if job_ads:
                for ad in job_ads:
                    with st.container(border=True):
                        st.markdown(f"**{ad['titre']}** @ {ad['entreprise']}")
                        st.link_button("Voir l'offre", ad['lien'])
            else:
                st.error("Aucune offre trouvée. Essayez d'élargir vos filtres (contrat, ville) ou de simplifier l'intitulé.")
    else:
        st.warning("Veuillez saisir un intitulé de poste pour lancer la recherche.")

# Pied de page
st.caption("Propulsé par Streamlit, Groq & Llama 3")
