"""Utilitaires partagés entre l'application Streamlit et l'API FastAPI."""

import io
import re
import urllib.parse
import logging
from typing import Optional

import PyPDF2
import requests

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_file) -> Optional[str]:
    """Extrait le texte d'un fichier PDF de manière sécurisée."""
    try:
        if pdf_file is None:
            return None
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text() or ""
            if content:
                text += content + "\n"
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du PDF : {e}")
        return None


def reverse_geocoding(lat, lon) -> Optional[str]:
    """Transforme des coordonnées GPS en Ville, Pays via OpenStreetMap."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "FindMyJobAI/1.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            addr = data.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village")
            country = addr.get("country")
            if city and country:
                res = f"{city}, {country}"
                logger.info(f"📍 GPS Géocodage réussi : {res}")
                return res
        logger.warning(f"📍 GPS Géocodage échoué (Code {response.status_code})")
    except Exception:
        return None
    return None


def clean_job_title(title) -> str:
    """Nettoie le titre du poste pour optimiser la recherche."""
    if not title:
        return ""
    if isinstance(title, list):
        title = " ".join(map(str, title))
    clean = title.lower()
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\s*', '', clean, flags=re.IGNORECASE)
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()


def get_geolocation() -> Optional[str]:
    """Tente de récupérer la localisation de l'utilisateur via son adresse IP."""
    headers = {"User-Agent": "Mozilla/5.0"}
    client_ip = ""
    try:
        import streamlit as st
        if hasattr(st, "context") and "X-Forwarded-For" in st.context.headers:
            client_ip = st.context.headers.get("X-Forwarded-For").split(",")[0].strip()
    except Exception:
        pass

    for service in [
        (f"https://ipapi.co/{client_ip}/json/" if client_ip else "https://ipapi.co/json/",
         lambda d: d.get("city") and d.get("country_name")),
        (f"http://ip-api.com/json/{client_ip}" if client_ip else "http://ip-api.com/json/",
         lambda d: d.get("city") and d.get("country")),
        (f"https://ipinfo.io/{client_ip}/json" if client_ip else "https://ipinfo.io/json",
         lambda d: d.get("city") and d.get("country")),
    ]:
        try:
            response = requests.get(service[0], headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                city = data.get("city") or data.get("city")
                country = data.get("country_name") or data.get("country")
                if city and country:
                    return f"{city}, {country}"
        except Exception:
            continue
    return None


def generate_job_search_links(job_title, lang_code="fr") -> dict:
    """Génère des URLs de recherche pour différentes plateformes."""
    q = urllib.parse.quote(job_title)
    links = {
        "fr": {
            "Welcome to the Jungle": f"https://www.welcometothejungle.com/fr/jobs?query={q}",
            "HelloWork": f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={q}",
            "Service Public": f"https://www.choisirleservicepublic.gouv.fr/nos-offres/filtres/mots-cles/{q}/"
        },
        "en": {
            "LinkedIn US": f"https://www.linkedin.com/jobs/search/?keywords={q}",
            "Reed.co.uk": f"https://www.reed.co.uk/jobs/{q.replace('%20', '-')}-jobs",
            "Dice (Tech US)": f"https://www.dice.com/jobs?q={q}"
        },
        "es": {
            "InfoJobs ES": f"https://www.infojobs.net/jobsearch/search-results.xhtml?keywords={q}",
            "Tecnoempleo": f"https://www.tecnoempleo.com/busqueda-empleo.php?te={q}",
            "Turijobs": f"https://www.turijobs.com/ofertas-trabajo/{q.replace('%20', '-')}"
        },
        "de": {
            "Xing DE": f"https://www.xing.com/jobs/search?keywords={q}",
            "StepStone DE": f"https://www.stepstone.de/jobs/{q.replace('%20', '-')}",
            "Honeypot.io": f"https://app.honeypot.io/vacancies?q={q}"
        },
        "ar": {
            "Bayt (Middle East)": f"https://www.bayt.com/en/international/jobs/?keyword={q}",
            "GulfTalent": f"https://www.gulftalent.com/jobs/search?q={q}",
            "Naukrigulf": f"https://www.naukrigulf.com/{q}-jobs"
        },
        "ja": {
            "Indeed Japan": f"https://jp.indeed.com/jobs?q={q}",
            "Mynavi Tenshoku": f"https://tenshoku.mynavi.jp/list/kw{q}/",
            "Rikunabi Next": f"https://next.rikunabi.com/rnc/docs/cp_s0070.jsp?sayonara_word={q}"
        },
        "zh": {
            "51job": f"https://search.51job.com/list/000000,000000,0000,00,9,99,{q},2,1.html",
            "Liepin": f"https://www.liepin.com/zhaopin/?key={q}",
            "Zhaopin": f"https://sou.zhaopin.com/?jl=489&kw={q}&kt=3"
        }
    }
    global_links = {
        "Remote OK": f"https://remoteok.com/remote-{q.replace('%20', '-')}-jobs",
        "Indeed Global": f"https://www.indeed.com/jobs?q={q}"
    }
    return {**links.get(lang_code, {}), **global_links}