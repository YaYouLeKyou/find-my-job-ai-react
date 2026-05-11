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

# --- INTERNATIONALIZATION (i18n) ---
LANGS = {
    "Français": {"code": "fr", "label": "français", "default_loc": "Paris, France"},
    "English": {"code": "en", "label": "English", "default_loc": "USA"},
    "Español": {"code": "es", "label": "español", "default_loc": "España"},
    "Deutsch": {"code": "de", "label": "Deutsch", "default_loc": "Deutschland"},
    "العربية": {"code": "ar", "label": "العربية", "default_loc": "Dubai, UAE"},
    "日本語": {"code": "ja", "label": "日本語", "default_loc": "Tokyo, Japan"},
    "中文": {"code": "zh", "label": "中文", "default_loc": "Beijing, China"}
}

STRINGS = {
    "fr": {
        "title": "🚀 Find me a job AI", "subtitle": "Trouvez votre prochain emploi avec l'aide de l'IA", "analyze": "Analyse du document...", "search": "Rechercher", "profile": "📋 Mon Profil",
        "settings": "⚙️ Paramètres", "num_ads": "Nombre d'annonces", "contract": "Type de contrat", "location": "📍 Ville / Pays", "remote": "Télétravail uniquement", "upload": "📂 Déposez votre CV (PDF)",
        "analyze_success": "Analyse réussie !", "analyze_fail": "Impossible d'extraire du texte de ce PDF.", "metier": "Métier", "exp": "Expérience", "advice": "✨ Conseils d'amélioration",
        "pistes": "💡 Pistes d'évolution", "alt": "🔀 Métiers Alternatifs", "search_section": "🔍 Recherche d'opportunités", "search_info": "Modifiez l'intitulé ci-dessous pour lancer une recherche personnalisée.",
        "search_placeholder": "Ex: Développeur Python, Serveur...", "scan_state": "📊 État du Scan Global", "direct_access": "🚀 Accès Direct", "no_results": "⚠️ Aucune offre trouvée.", "footer": "Propulsé par Streamlit, Groq & Llama 3",
        "global_search": "🌍 Recherche mondiale", "sort_by": "Trier par", "sort_relevant": "Pertinence (IA)", "sort_recent": "Plus récentes", "sort_closest": "Plus proches"
    },
    "en": {
        "title": "🚀 Find me a job AI", "subtitle": "Find your next job with AI assistance", "analyze": "Analyzing document...", "search": "Search", "profile": "📋 My Profile",
        "settings": "⚙️ Settings", "num_ads": "Number of ads", "contract": "Contract type", "location": "📍 City / Country", "remote": "Remote only", "upload": "📂 Drop your CV (PDF)",
        "analyze_success": "Analysis successful!", "analyze_fail": "Could not extract text from this PDF.", "metier": "Job", "exp": "Experience", "advice": "✨ Improvement Tips",
        "pistes": "💡 Career Paths", "alt": "🔀 Alternative Careers", "search_section": "🔍 Opportunity Search", "search_info": "Modify the title below to start a personalized search.",
        "search_placeholder": "E.g.: Python Developer, Waiter...", "scan_state": "📊 Global Scan Status", "direct_access": "🚀 Direct Access", "no_results": "⚠️ No offers found.", "footer": "Powered by Streamlit, Groq & Llama 3",
        "global_search": "🌍 Worldwide search", "sort_by": "Sort by", "sort_relevant": "Relevance (AI)", "sort_recent": "Most recent", "sort_closest": "Closest"
    },
    "es": {
        "title": "🚀 Find me a job AI", "subtitle": "Encuentra tu próximo empleo con IA", "analyze": "Analizando documento...", "search": "Buscar", "profile": "📋 Mi Perfil",
        "settings": "⚙️ Ajustes", "num_ads": "Número de anuncios", "contract": "Tipo de contrato", "location": "📍 Ciudad / País", "remote": "Solo teletrabajo", "upload": "📂 Sube tu CV (PDF)",
        "analyze_success": "¡Análisis exitoso!", "analyze_fail": "No se pudo extraer texto de este PDF.", "metier": "Oficio", "exp": "Experiencia", "advice": "✨ Consejos de mejora",
        "pistes": "💡 Trayectorias profesionales", "alt": "🔀 Carreras alternativas", "search_section": "🔍 Búsqueda de oportunidades", "search_info": "Modifica el título a continuación para iniciar una búsqueda personalizada.",
        "search_placeholder": "Ej: Desarrollador Python, Camarero...", "scan_state": "📊 Estado del escaneo global", "direct_access": "🚀 Acceso directo", "no_results": "⚠️ No se encontraron ofertas.", "footer": "Desarrollado par Streamlit, Groq & Llama 3",
        "global_search": "🌍 Búsqueda mundial", "sort_by": "Ordenar por", "sort_relevant": "Relevancia (IA)", "sort_recent": "Más recientes", "sort_closest": "Más cercanos"
    },
    "de": {
        "title": "🚀 Find me a job AI", "subtitle": "Finden Sie Ihren nächsten Job mit KI", "analyze": "Analysiere Dokument...", "search": "Suchen", "profile": "📋 Mein Profil",
        "settings": "⚙️ Einstellungen", "num_ads": "Anzahl der Anzeigen", "contract": "Vertragstyp", "location": "📍 Stadt / Land", "remote": "Nur Homeoffice", "upload": "📂 CV hochladen (PDF)",
        "analyze_success": "Analyse erfolgreich!", "analyze_fail": "Text konnte nicht aus dieser PDF extrahiert werden.", "metier": "Beruf", "exp": "Erfahrung", "advice": "✨ Verbesserungstipps",
        "pistes": "💡 Karrierewege", "alt": "🔀 Alternative Karrieren", "search_section": "🔍 Chancensuche", "search_info": "Ändern Sie den Titel unten, um eine personalisierte Suche zu starten.",
        "search_placeholder": "Z.B.: Python-Entwickler, Kellner...", "scan_state": "📊 Globaler Scan-Status", "direct_access": "🚀 Direktzugriff", "no_results": "⚠️ Keine Angebote gefunden.", "footer": "Präsentiert von Streamlit, Groq & Llama 3",
        "global_search": "🌍 Weltweite Suche", "sort_by": "Sortieren nach", "sort_relevant": "Relevanz (KI)", "sort_recent": "Neueste", "sort_closest": "Am nächsten"
    },
    "ar": {
        "title": "🚀 Find me a job AI", "subtitle": "ابحث عن وظيفتك القادمة بمساعدة الذكاء الاصطناعي", "analyze": "تحليل المستند...", "search": "بحث", "profile": "📋 ملفي الشخصي",
        "settings": "⚙️ الإعدادات", "num_ads": "عدد الإعلانات", "contract": "نوع العقد", "location": "📍 المدينة / الدولة", "remote": "عمل عن بعد فقط", "upload": "📂 ارفع سيرتك الذاتية (PDF)",
        "analyze_success": "نجح التحليل!", "analyze_fail": "تعذر استخراج النص من ملف PDF هذا.", "metier": "الوظيفة", "exp": "الخبرة", "advice": "✨ نصائح للتحسين",
        "pistes": "💡 المسارات الوظيفية", "alt": "🔀 وظائف بديلة", "search_section": "🔍 البحث عن فرص", "search_info": "قم بتعديل المسمى الوظيفي أدناه لبدء بحث مخصص.",
        "search_placeholder": "مثال: مطور بايثون، نادل...", "scan_state": "📊 حالة الفحص الشامل", "direct_access": "🚀 وصول مباشر", "no_results": "⚠️ لم يتم العثور على عروض.", "footer": "مدعوم بواسطة Streamlit و Groq و Llama 3",
        "global_search": "🌍 بحث عالمي", "sort_by": "ترتيب حسب", "sort_relevant": "الأكثر ملاءمة (ذكاء اصطناعي)", "sort_recent": "الأحدث", "sort_closest": "الأقرب"
    },
    "ja": {
        "title": "🚀 Find me a job AI", "subtitle": "AIの力で次の仕事を見つける", "analyze": "分析中...", "search": "検索", "profile": "📋 プロフィール",
        "settings": "⚙️ 設定", "num_ads": "表示件数", "contract": "雇用形態", "location": "📍 市区町村 / 国", "remote": "リモートのみ", "upload": "📂 CVをアップロード (PDF)",
        "analyze_success": "分析に成功しました！", "analyze_fail": "PDFからテキストを抽出できませんでした。", "metier": "職種", "exp": "経験", "advice": "✨ 改善のヒント",
        "pistes": "💡 キャリアパス", "alt": "🔀 代替の職業", "search_section": "🔍 求人検索", "search_info": "以下のタイトルを変更して、パーソナライズされた検索を開始します。",
        "search_placeholder": "例：Pythonエンジニア、ウェイター...", "scan_state": "📊 全体スキャンステータス", "direct_access": "🚀 ダイレクトアクセス", "no_results": "⚠️ 求人が見つかりませんでした。", "footer": "Powered by Streamlit, Groq & Llama 3",
        "global_search": "🌍 世界的な検索", "sort_by": "並べ替え", "sort_relevant": "関連性 (AI)", "sort_recent": "最新順", "sort_closest": "近い順"
    },
    "zh": {
        "title": "🚀 Find me a job AI", "subtitle": "利用 AI 找到你的下一份工作", "analyze": "分析中...", "search": "搜索", "profile": "📋 我的档案",
        "settings": "⚙️ 设置", "num_ads": "显示数量", "contract": "合同类型", "location": "📍 城市 / 国家", "remote": "仅远程", "upload": "📂 上传简历 (PDF)",
        "analyze_success": "分析成功！", "analyze_fail": "无法从此 PDF 中提取文本。", "metier": "职业", "exp": "经验", "advice": "✨ 改进建议",
        "pistes": "💡 职业路径", "alt": "🔀 替代职业", "search_section": "🔍 机会搜索", "search_info": "修改下方标题以启动个性化搜索。",
        "search_placeholder": "例如：Python 开发人员、服务员...", "scan_state": "📊 全球扫描状态", "direct_access": "🚀 直接访问", "no_results": "⚠️ 未找到职位。", "footer": "由 Streamlit、Groq 和 Llama 3 提供支持",
        "global_search": "🌍 全球搜索"
    }
}

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
        if file is None:
            return None
            
        pdf_reader = PyPDF2.PdfReader(file)
        if not pdf_reader.pages:
            return None

        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            content = page.extract_text() or ""
            if content:
                text += content
        return text
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF : {e}")
        return None

def rank_jobs_with_ai(cv_data, jobs, filters, target_lang="français"):
    """Utilise l'IA pour classer les offres par pertinence par rapport au CV et aux filtres."""
    if not client or not jobs or not cv_data:
        return jobs
    
    # On limite le tri aux 20 premières offres pour la rapidité
    limit_tri = 20
    jobs_to_rank = jobs[:limit_tri]
    
    job_list_text = "\n".join([f"ID: {i} | {j['title']} @ {j['company']}" for i, j in enumerate(jobs_to_rank)])
    
    prompt = f"""
    En tant qu'expert en recrutement, classe ces offres par pertinence décroissante pour ce candidat.
    TIENS COMPTE DU MÉTIER, DE L'EXPÉRIENCE ET DES FILTRES (Contrat: {filters.get('contrat')}, Remote: {filters.get('remote')}).

    PROFIL : {cv_data.get('metier')} ({cv_data.get('annees_experience')} ans d'exp). Compétences: {', '.join(cv_data.get('mots_cles', []))}
    OFFRES :
    {job_list_text}

    Réponds uniquement avec un objet JSON contenant une clé "ranking" qui est la liste d'objets : [{{ "id": index, "score": score_0_a_100 }}].
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        ranking_data = json.loads(response.choices[0].message.content).get("ranking", [])
        
        ranked_list = []
        ranked_indices = []
        for item in ranking_data:
            idx = item.get("id")
            if idx is not None and idx < len(jobs_to_rank):
                job = jobs_to_rank[idx].copy()
                job["match_score"] = item.get("score", 0)
                ranked_list.append(job)
                ranked_indices.append(idx)

        # Ajouter les jobs du top 20 qui n'auraient pas été classés par l'IA
        for i in range(len(jobs_to_rank)):
            if i not in ranked_indices:
                ranked_list.append(jobs_to_rank[i])

        # Ajouter le reste des jobs au-delà du top 20
        if len(jobs) > limit_tri:
            ranked_list.extend(jobs[limit_tri:])
            
        return ranked_list
    except Exception as e:
        logger.error(f"Erreur tri IA: {e}")
        return jobs

def get_geolocation():
    """Tente de récupérer la localisation de l'utilisateur via son adresse IP."""
    try:
        # Utilisation d'un service gratuit de géolocalisation par IP
        response = requests.get("https://ipapi.co/json/", timeout=3)
        if response.status_code == 200:
            data = response.json()
            city = data.get("city")
            country = data.get("country_name")
            if city and country:
                return f"{city}, {country}"
    except Exception as e:
        logger.warning(f"Échec de la géolocalisation IP : {e}")
    return None

def clean_job_title(title):
    """Nettoie le titre du poste pour optimiser la recherche (le dénominateur optimisé)."""
    if not title: return ""
    clean = title.lower()
    # Suppression des mentions H/F, F/H, etc., de manière robuste avec regex
    # Ajout de flags pour ignorer la casse et gestion des espaces multiples
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
    # On ne garde que la partie principale avant les séparateurs courants
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()

def analyze_cv(text, target_lang="français"):
    """Envoie le texte à Groq et parse la réponse JSON."""
    if not client:
        return None
    
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

def generate_cover_letter(cv_data, job_title, company, job_description="", target_lang="français"):
    """Génère une lettre de motivation personnalisée via Groq."""
    if not client or not cv_data:
        return None

    prompt = f"""
    Tu es un expert en recrutement. Rédige une lettre de motivation percutante, professionnelle et personnalisée en {target_lang}.
    
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

def generate_job_search_links(job_title, lang_code="fr"):
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
    # Retourne les liens de la langue choisie + liens globaux
    global_links = {"Remote OK": f"https://remoteok.com/remote-{q.replace('%20', '-')}-jobs", "Indeed Global": f"https://www.indeed.com/jobs?q={q}"}
    return {**links.get(lang_code, {}), **global_links}

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
            "date": res.get("created", ""),
            "location": res.get("location", {}).get("display_name", ""),
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
            "date": res.get("detected_extensions", {}).get("posted_at", ""),
            "location": res.get("location", ""),
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
            "date": res.get("updated", ""),
            "location": res.get("type", ""), # Jooble met souvent la loc ici
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
            "location": res.get("location", ""),
            "source": "LinkedIn (Apify)"
        } for res in results]
    except Exception as e:
        logger.error(f"❌ Apify API Error: {e}")
        return []

def render_job_card(title, company, link, source, job_id, description="", match_score=None, date=None):
    """Rendu générique d'une carte d'offre d'emploi pour éviter la duplication de code."""
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"### {title}")
            st.markdown(f"🏢 **{company}**")
        with c2:
            if match_score is not None:
                color = "green" if match_score > 70 else "orange" if match_score > 40 else "red"
                st.markdown(f"**Score: <span style='color:{color}'>{match_score}%</span>**", unsafe_allow_html=True)
            if date:
                st.caption(f"📅 {date}")

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
                        letter = generate_cover_letter(st.session_state['user_cv_data'], title, company, description, target_lang=st.session_state.get('lang_label', 'français'))
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

# --- SIDEBAR CONFIGURATION (Language first) ---
with st.sidebar:
    lang_choice = st.selectbox("🌐 Langue / Language", list(LANGS.keys()), index=0)
    lang_data = LANGS[lang_choice]
    st.session_state['lang_code'] = lang_data['code']
    st.session_state['lang_label'] = lang_data['label']
    
    # Get current strings for UI
    S = STRINGS[st.session_state['lang_code']]

    st.header(S['settings'])
    num_ads = st.slider(S['num_ads'], min_value=1, max_value=50, value=10)
    contrat = st.selectbox(S['contract'], ["CDI", "CDD", "Interim"])
    
    # Initialisation de la localisation : Paris par défaut, puis tentative de géo-détection
    if 'user_location' not in st.session_state:
        st.session_state['user_location'] = lang_data['default_loc']
        detected_loc = get_geolocation()
        if detected_loc:
            st.session_state['user_location'] = detected_loc

    remote = st.checkbox(S['remote'])
    global_search = False
    if remote:
        global_search = st.checkbox(S['global_search'], value=False)

    if global_search:
        ville = ""
        st.caption(f"🌐 {S['global_search']}")
    else:
        ville = st.text_input(S['location'], value=st.session_state['user_location'])
        st.session_state['user_location'] = ville

    st.divider()
    sort_option = st.selectbox(S['sort_by'], [S['sort_relevant'], S['sort_recent'], S['sort_closest']])

# --- MAIN UI ---
st.title(S['title'])
st.markdown(f"#### {S['subtitle']}")

# --- INITIALISATION DE L'ÉTAT ---
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

uploaded_file = st.file_uploader(S['upload'], type="pdf")

if uploaded_file is not None:
    # On crée un identifiant unique pour le fichier pour éviter de re-analyser inutilement
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get('last_processed_file') != file_id:
        with st.spinner(S['analyze']):
            cv_text = extract_text_from_pdf(uploaded_file)
            if cv_text:
                data = analyze_cv(cv_text, target_lang=st.session_state['lang_label'])
                if data:
                    logger.info("--- Données brutes de l'analyse CV ---")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                    st.session_state['user_cv_data'] = data
                    st.session_state['search_query'] = clean_job_title(data.get("metier", ""))
                    st.session_state['last_processed_file'] = file_id
                    st.success(S['analyze_success'])
                    st.divider()
            else:
                st.warning(S['analyze_fail'])

# --- AFFICHAGE DU PROFIL ---
if 'user_cv_data' in st.session_state:
    data = st.session_state['user_cv_data']

    if data.get("nom_complet"):
        st.header(f"👤 {data['nom_complet']}")
    if data.get("contact"):
        st.caption(f"📩 {data['contact']}")

    col_profil, col_pistes = st.columns([1, 1])

    with col_profil:
        st.subheader(S['profile'])
        st.markdown(f"**{S['metier']} :** {data.get('metier', 'Non spécifié')}")
        st.markdown(f"**{S['exp']} :** {data.get('annees_experience', 0)} an(s)")
        st.info(data.get("resume", "Pas de résumé disponible."))
        keywords = data.get("mots_cles", [])
        st.write(" ".join([f"`{kw}`" for kw in keywords]))
        
        if data.get("suggestions_amelioration"):
            st.markdown("---")
            st.markdown(S['advice'])
            for suggestion in data["suggestions_amelioration"]:
                st.markdown(f"📍 {suggestion}")

    with col_pistes:
        st.subheader(S['pistes'])
        for i, r in enumerate(data.get("recommandations_metiers", [])):
            if st.button(f"🔍 {r}", key=f"reco_{i}", use_container_width=True):
                st.session_state['search_query'] = r
                st.session_state['trigger_search'] = True
                st.rerun()
        
        st.subheader(S['alt'])
        st.caption("Basés sur vos compétences transférables")
        for i, r in enumerate(data.get("metiers_alternatifs", [])):
            if st.button(f"🔄 {r}", key=f"alt_{i}", use_container_width=True):
                st.session_state['search_query'] = r
                st.session_state['trigger_search'] = True
                st.rerun()

# --- SECTION DE RECHERCHE D'OFFRES ---
st.divider()
st.subheader(S['search_section'])
st.info(S['search_info'])

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
    manual_query = st.text_input(S['metier'], value=st.session_state['search_query'], placeholder=S['search_placeholder'], label_visibility="collapsed")

with col_btn:
    launch_search = st.button(S['search'], use_container_width=True)

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
        ville_search = ville if (ville or global_search) else "France"

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
        
        # --- UNIFICATION ET TRI IA ---
        all_results = []
        # Collecter JobSpy
        if st.session_state['offres'] is not None and not st.session_state['offres'].empty:
            for i, row in st.session_state['offres'].iterrows():
                all_results.append({
                    "title": row.get('title', 'N/A'), "company": row.get('company', 'N/A'),
                    "link": row.get('job_url', '#'), "source": row.get('site', 'JobSpy').capitalize(),
                    "date": str(row.get('date_posted', '')),
                    "location": row.get('location', ''),
                    "desc": row.get('description', ""), "id": f"js_{i}_{hash(row.get('job_url'))}"
                })
        
        # Collecter APIs
        api_sources = [('job_ads_adzuna', 'Adzuna'), ('job_ads_serpapi', 'Google Jobs'), 
                       ('job_ads_jooble', 'Jooble'), ('job_ads_apify', 'LinkedIn')]
        for key, name in api_sources:
            for i, ad in enumerate(st.session_state.get(key, [])):
                all_results.append({
                    "title": ad.get('titre'), "company": ad.get('entreprise'),
                    "link": ad.get('lien'), "source": ad.get('source', name),
                    "date": ad.get('date', ''), "location": ad.get('location', ''),
                    "desc": "", "id": f"api_{name}_{i}_{hash(ad.get('lien'))}"
                })

        # --- LOGIQUE DE TRI ---
        if sort_option == S['sort_recent']:
            all_results.sort(key=lambda x: x.get('date', ''), reverse=True)
        elif sort_option == S['sort_closest'] and st.session_state.get('user_location'):
            user_loc = st.session_state['user_location'].lower()
            all_results.sort(key=lambda x: user_loc in x.get('location', '').lower(), reverse=True)
        elif sort_option == S['sort_relevant'] and 'user_cv_data' in st.session_state and all_results:
            filters = {"contrat": contrat, "remote": remote}
            all_results = rank_jobs_with_ai(st.session_state['user_cv_data'], all_results, filters)
        
        st.session_state['ranked_results'] = all_results

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
    st.subheader(S['scan_state'])
    
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
    st.subheader(S['direct_access'])
    st.caption("Ces plateformes protègent leurs données contre l'IA, mais nous avons optimisé vos liens de recherche pour un accès rapide :")
    
    links = generate_job_search_links(manual_query, lang_code=st.session_state['lang_code'])
    link_rows = [list(links.items())[i:i + 3] for i in range(0, len(links), 3)]
    for row in link_rows:
        cols = st.columns(len(row))
        for i, (name, url) in enumerate(row):
            cols[i].link_button(f"🔍 {name}", url, use_container_width=True)

# --- AFFICHAGE DES RÉSULTATS TRIÉS ---
if st.session_state.get('ranked_results'):
    st.divider()
    st.subheader(f"🔥 {S.get('top_matches', 'Meilleurs résultats triés par IA')}")
    for job in st.session_state['ranked_results']:
        render_job_card(job['title'], job['company'], job['link'], job['source'], job['id'], job.get('desc', ""), job.get('match_score'), job.get('date'))

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
        st.warning(S['no_results'])

st.caption(S['footer'])
