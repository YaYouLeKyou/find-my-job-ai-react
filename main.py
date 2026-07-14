import streamlit as st
from groq import Groq
import google.generativeai as genai
import PyPDF2
import json
import os
import urllib.parse
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
import pandas as pd
import re
import concurrent.futures
import logging

# Configuration de la page Streamlit (Doit être la TOUTE PREMIÈRE commande)
st.set_page_config(page_title="Find me a job AI", page_icon="🚀", layout="wide")

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
        "settings": "⚙️ Paramètres", "num_ads": "Nombre d'annonces", "contract": "Type de contrat", "location": "📍 Ville / Pays", "remote": "Télétravail uniquement", "upload": "📂 Glissez-déposez votre CV ici (PDF)",
        "analyze_success": "Analyse réussie !", "analyze_fail": "Impossible d'extraire du texte de ce PDF.", "metier": "Métier", "exp": "Expérience", "advice": "✨ Conseils d'amélioration",
        "pistes": "💡 Pistes d'évolution", "alt": "🔀 Métiers Alternatifs", "search_section": "🔍 Recherche d'opportunités", "search_info": "Modifiez l'intitulé ci-dessous pour lancer une recherche personnalisée.",
        "search_placeholder": "Ex: Développeur Python, Serveur...", "scan_state": "📊 État du Scan Global", "direct_access": "🚀 Accès Direct", "no_results": "⚠️ Aucune offre trouvée.", "footer": "Propulsé par Streamlit, Groq & Llama 3",
        "global_search": "🌍 Recherche mondiale", "sort_by": "Trier par", "sort_relevant": "Pertinence (IA)", "sort_recent": "Plus récentes", "sort_closest": "Plus proches", "footer": "",
        "filter_active": "Filtré par", "clear_filter": "❌ Effacer le filtre", "select_sources": "📡 Sources de recherche", "top_matches": "Meilleurs résultats triés par IA",
        "scan_help": "Cliquez sur une source pour l'inclure (vert) ou l'exclure (rouge) des résultats.",
        "relaunch": "🔄 Actualiser / Appliquer les changements"
    },
    "en": {
        "title": "🚀 Find me a job AI", "subtitle": "Find your next job with AI assistance", "analyze": "Analyzing document...", "search": "Search", "profile": "📋 My Profile",
        "settings": "⚙️ Settings", "num_ads": "Number of ads", "contract": "Contract type", "location": "📍 City / Country", "remote": "Remote only", "upload": "📂 Drag and drop your CV here (PDF)",
        "analyze_success": "Analysis successful!", "analyze_fail": "Could not extract text from this PDF.", "metier": "Job", "exp": "Experience", "advice": "✨ Improvement Tips",
        "pistes": "💡 Career Paths", "alt": "🔀 Alternative Careers", "search_section": "🔍 Opportunity Search", "search_info": "Modify the title below to start a personalized search.",
        "search_placeholder": "E.g.: Python Developer, Waiter...", "scan_state": "📊 Global Scan Status", "direct_access": "🚀 Direct Access", "no_results": "⚠️ No offers found.", "footer": "",
        "global_search": "🌍 Worldwide search", "sort_by": "Sort by", "sort_relevant": "Relevance (AI)", "sort_recent": "Most recent", "sort_closest": "Closest",
        "filter_active": "Filtered by", "clear_filter": "❌ Clear filter", "select_sources": "📡 Search Sources", "top_matches": "Best AI-sorted results",
        "scan_help": "Click a source to include (green) or exclude (red) it from results.",
        "relaunch": "🔄 Refresh / Apply changes"
    },
    "es": {
        "title": "🚀 Find me a job AI", "subtitle": "Encuentra tu próximo empleo con IA", "analyze": "Analizando documento...", "search": "Buscar", "profile": "📋 Mi Perfil",
        "settings": "⚙️ Ajustes", "num_ads": "Número de anuncios", "contract": "Tipo de contrato", "location": "📍 Ciudad / País", "remote": "Solo teletrabajo", "upload": "📂 Arrastra y suelta tu CV aquí (PDF)",
        "analyze_success": "¡Análisis exitoso!", "analyze_fail": "No se pudo extraer texto de este PDF.", "metier": "Oficio", "exp": "Experiencia", "advice": "✨ Consejos de mejora",
        "pistes": "💡 Trayectorias profesionales", "alt": "🔀 Carreras alternativas", "search_section": "🔍 Búsqueda de oportunidades", "search_info": "Modifica el título a continuación para iniciar una búsqueda personalizada.",
        "search_placeholder": "Ej: Desarrollador Python, Camarero...", "search_placeholder": "Ej: Desarrollador Python, Camarero...", "scan_state": "📊 Estado del escaneo global", "direct_access": "🚀 Acceso directo", "no_results": "⚠️ No se encontraron ofertas.", "footer": "",
        "global_search": "🌍 Búsqueda mundial", "sort_by": "Ordenar por", "sort_relevant": "Relevancia (IA)", "sort_recent": "Más recientes", "sort_closest": "Más cercanos",
        "top_matches": "Mejores resultados ordenados por IA", "filter_active": "Filtrado por", "clear_filter": "❌ Borrar filtro",
        "select_sources": "📡 Fuentes de búsqueda",
        "scan_help": "Haga clic en una fuente para incluirla (verde) o excluirla (rojo) de los resultados."
    },
    "de": {
        "title": "🚀 Find me a job AI", "subtitle": "Finden Sie Ihren nächsten Job mit KI", "analyze": "Analysiere Dokument...", "search": "Suchen", "profile": "📋 Mein Profil",
        "settings": "⚙️ Einstellungen", "num_ads": "Anzahl der Anzeigen", "contract": "Vertragstyp", "location": "📍 Stadt / Land", "remote": "Nur Homeoffice", "upload": "📂 Lebenslauf hierher ziehen (PDF)",
        "analyze_success": "Analyse erfolgreich!", "analyze_fail": "Text konnte nicht aus dieser PDF extrahiert werden.", "metier": "Beruf", "exp": "Erfahrung", "advice": "✨ Verbesserungstipps",
        "pistes": "💡 Karrierewege", "alt": "🔀 Alternative Karrieren", "search_section": "🔍 Chancensuche", "search_info": "Ändern Sie den Titel unten, um eine personalisierte Suche zu starten.",
        "search_placeholder": "Z.B.: Python-Entwickler, Kellner...", "scan_state": "📊 Globaler Scan-Status", "direct_access": "🚀 Direktzugriff", "no_results": "⚠️ Keine Angebote gefunden.", "footer": "",
        "global_search": "🌍 Weltweite Suche", "sort_by": "Sortieren nach", "sort_relevant": "Relevanz (KI)", "sort_recent": "Neueste", "sort_closest": "Am nächsten",
        "top_matches": "Beste KI-sortierte Ergebnisse", "filter_active": "Gefiltert nach", "clear_filter": "❌ Filter löschen",
        "select_sources": "📡 Suchquellen",
        "scan_help": "Klicken Sie auf eine Quelle, um sie in die Ergebnisse aufzunehmen (grün) oder auszuschließen (rot)."
    },
    "ar": {
        "title": "🚀 Find me a job AI", "subtitle": "ابحث عن وظيفتك القادمة بمساعدة الذكاء الاصطناعي", "analyze": "تحليل المستند...", "search": "بحث", "profile": "📋 ملفي الشخصي",
        "settings": "⚙️ الإعدادات", "num_ads": "عدد الإعلانات", "contract": "نوع العقد", "location": "📍 المدينة / الدولة", "remote": "عمل عن بعد فقط", "upload": "📂 قم بسحب وإفلات سيرتك الذاتية هنا (PDF)",
        "analyze_success": "نجح التحليل!", "analyze_fail": "تعذر استخراج النص من ملف PDF هذا.", "metier": "الوظيفة", "exp": "الخبرة", "advice": "✨ نصائح للتحسين",
        "pistes": "💡 المسارات الوظيفية", "alt": "🔀 وظائف بديلة", "search_section": "🔍 البحث عن فرص", "search_info": "قم بتعديل المسمى الوظيفي أدناه لبدء بحث مخصص.",
        "search_placeholder": "مثال: مطور بايثون، نادل...", "scan_state": "📊 حالة الفحص الشامل", "direct_access": "🚀 وصول مباشر", "no_results": "⚠️ لم يتم العثور على عروض.", "footer": "",
        "global_search": "🌍 بحث عالمي", "sort_by": "ترتيب حسب", "sort_relevant": "الأكثر ملاءمة (ذكاء اصطناعي)", "sort_recent": "الأحدث", "sort_closest": "الأقرب",
        "top_matches": "أفضل النتائج المصنفة بواسطة الذكاء الاصطناعي", "filter_active": "مصفى حسب", "clear_filter": "❌ مسح التصفية",
        "select_sources": "📡 مصادر البحث",
        "scan_help": "انقر فوق مصدر لتضمينه (أخضر) أو استبعاده (أحمر) من النتائج."
    },
    "ja": {
        "title": "🚀 Find me a job AI", "subtitle": "AIの力で次の仕事を見つける", "analyze": "分析中...", "search": "検索", "profile": "📋 プロフィール",
        "settings": "⚙️ 設定", "num_ads": "表示件数", "contract": "雇用形態", "location": "📍 市区町村 / 国", "remote": "リモートのみ", "upload": "📂 ここにCVをドラッグ＆ドロップ (PDF)",
        "analyze_success": "分析に成功しました！", "analyze_fail": "PDFからテキストを抽出できませんでした。", "metier": "職種", "exp": "経験", "advice": "✨ 改善のヒント",
        "pistes": "💡 キャリアパス", "alt": "🔀 代替の職業", "search_section": "🔍 求人検索", "search_info": "以下のタイトルを変更して、パーソナライズされた検索を開始します。",
        "search_placeholder": "例：Pythonエンジニア、ウェイター...", "scan_state": "📊 全体スキャンステータス", "direct_access": "🚀 ダイレクトアクセス", "no_results": "⚠️ 求人が見つかりませんでした。", "footer": "",
        "global_search": "🌍 世界的な検索", "sort_by": "並べ替え", "sort_relevant": "関連性 (AI)", "sort_recent": "最新順", "sort_closest": "近い順",
        "top_matches": "AIが選んだおすすめの結果", "filter_active": "フィルター中:", "clear_filter": "❌ 解除",
        "select_sources": "📡 検索ソース",
        "scan_help": "クリックしてソースを結果に含める（緑）か除外する（赤）かを選択します。"
    },
    "zh": {
        "title": "🚀 Find me a job AI", "subtitle": "利用 AI 找到你的下一份工作", "analyze": "分析中...", "search": "搜索", "profile": "📋 我的档案",
        "settings": "⚙️ 设置", "num_ads": "显示数量", "contract": "合同类型", "location": "📍 城市 / 国家", "remote": "仅远程", "upload": "📂 在此处拖放您的简历 (PDF)",
        "analyze_success": "分析成功！", "analyze_fail": "无法从此 PDF 中提取文本。", "metier": "职业", "exp": "经验", "advice": "✨ 改进建议",
        "pistes": "💡 职业路径", "alt": "🔀 替代职业", "search_section": "🔍 机会搜索", "search_info": "修改下方标题以启动个性化搜索。",
        "search_placeholder": "例如：Python 开发人员、服务员...", "scan_state": "📊 全球扫描状态", "direct_access": "🚀 直接访问", "no_results": "⚠️ 未找到职位。", "footer": "",
        "global_search": "🌍 全球搜索", "sort_by": "排序方式", "sort_relevant": "相关性 (AI)", "sort_recent": "最新发布", "sort_closest": "距离最近",
        "top_matches": "AI 排序的最佳结果", "filter_active": "筛选依据:", "clear_filter": "❌ 清除筛选",
        "select_sources": "📡 搜索来源",
        "scan_help": "点击来源以将其包含在结果中（绿色）或排除（红色）。"
    }
}

# --- CONFIGURATION INITIALE ---
load_dotenv(override=True)
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

# Diagnostic de la clé Groq (Console)
if api_key:
    logger.info("--- Diagnostic Groq ---")
    logger.info(f"Clé détectée : {api_key[:4]}...{api_key[-4:]}")
    if not api_key.startswith("gsk_"):
        logger.error("❌ Format invalide : Une clé Groq doit commencer par 'gsk_'")

if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
    except Exception as e:
        logger.error(f"❌ Erreur de configuration Gemini : {e}")
else:
    logger.warning("⚠️ Aucune clé Gemini API trouvée dans .env")

if api_key:
    client = Groq(api_key=api_key)
else:
    client = None
    st.error("⚠️ Clé API GROQ manquante dans le fichier .env")

def extract_text_from_pdf(file):
    """Extrait le texte d'un fichier PDF de manière sécurisée."""
    try:
        if file is None:
            return None
        
        # Important : Reset le pointeur de lecture pour les flux mobiles/cloud
        file.seek(0)
        
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text() or ""
            if content:
                text += content + "\n"
        
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du PDF : {e}")
        return None

def reverse_geocoding(lat, lon):
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
    except:
        return None

def is_ollama_online():
    """Vérifie si le serveur Ollama répond sur l'URL configurée."""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_ollama_version():
    """Récupère la version d'Ollama via l'API."""
    try:
        response = requests.get(f"{ollama_url}/api/version", timeout=2)
        if response.status_code == 200:
            return response.json().get("version")
    except:
        return None

def call_local_llama(prompt, model_name, is_json=False):
    """Appelle l'instance locale d'Ollama avec gestion d'erreur détaillée."""
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json" if is_json else ""
        }
        # Augmentation du timeout à 90s pour les gros modèles
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=90)
        
        if response.status_code == 200:
            return response.json().get("response")
        else:
            error_data = response.json()
            error_msg = error_data.get("error", response.text)
            if "unknown model architecture" in error_msg.lower() or "mllama" in error_msg.lower():
                logger.error("Erreur d'architecture Ollama")
            else:
                logger.error(f"Erreur Ollama : {error_msg}")
            return None
    except Exception as e:
        logger.error(f"Ollama Local Error: {e}")
        return None

def call_ai_provider(prompt, selected_model, is_json=False):
    """Fonction centralisée pour appeler Gemini ou Groq."""
    st.session_state['last_ai_error'] = ""
    # Priorité à la clé saisie par l'utilisateur dans la sidebar, sinon clé du .env
    active_gemini_key = st.session_state.get('custom_gemini_key') or gemini_api_key

    try:
        if "Gemini" in selected_model:
            if not active_gemini_key:
                raise Exception("Clé API Gemini manquante. Veuillez la configurer dans la barre latérale.")

            genai.configure(api_key=active_gemini_key)
            # Mapping : 3.5 -> 2.0 Flash (Stable), 2.5 -> 1.5 Flash
            model_id = "models/gemini-2.0-flash" if "3.5" in selected_model else "models/gemini-1.5-flash"
            
            logger.info(f"Appel Gemini AI : {model_id}")
            model = genai.GenerativeModel(model_id)
            
            generation_config = {"response_mime_type": "application/json", "temperature": 0.1} if is_json else {"temperature": 0.7}
            # On assouplit les filtres de sécurité pour éviter les faux positifs sur les contenus de CV
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
            
            try:
                # Vérification du motif de fin (Safety, etc.)
                if response.candidates and response.candidates[0].finish_reason != 1: # 1 = STOP (Success)
                    reason = response.candidates[0].finish_reason
                    logger.warning(f"Gemini finish_reason inhabituel : {reason}")
                    if reason == 3: # SAFETY
                        raise Exception("L'analyse a été bloquée par les filtres de sécurité de Google.")
                
                text = response.text
            except (ValueError, AttributeError):
                # Fallback si l'accès à .text est bloqué par la sécurité
                if response.candidates and len(response.candidates[0].content.parts) > 0:
                    text = response.candidates[0].content.parts[0].text
                else:
                    raise Exception("Gemini a refusé de générer du texte pour ce contenu (Filtre de sécurité).")

            if is_json:
                # Nettoyage JSON ultra-robuste
                # On cherche la première { et la dernière } au cas où l'IA ajoute du texte avant/après
                json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
                if json_match:
                    text = json_match.group(1)
                
            return text
        elif "(Local/dev)" in selected_model:
            # Mapping des noms d'affichage vers les tags Ollama
            # Simplification du mapping local
            model_map = {
                "Llama 3.2 Vision (Local/dev)": "llama3.2-vision",
                "Llama 3.2 (Local/dev)": "llama3.2",
                "Qwen 3 4B (Local/dev)": "qwen3:4b"
            }
            ollama_model = model_map.get(selected_model, "llama3.2")
            return call_local_llama(prompt, ollama_model, is_json=is_json)
        elif "Grok" in selected_model:
            if not xai_api_key:
                raise Exception("Clé API xAI (Grok) non configurée dans le fichier .env")
            
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
            if not client:
                raise Exception("Clé Groq non configurée")
                
            params = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "llama-3.3-70b-versatile",
            }
            if is_json:
                params["response_format"] = {"type": "json_object"}
                
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Erreur AI Provider ({selected_model}): {e}")
        st.session_state['last_ai_error'] = err_msg
        return None
        

def rank_jobs_with_ai(cv_data, jobs, filters, target_lang="français"):
    """Utilise l'IA pour classer les offres par pertinence par rapport au CV et aux filtres."""
    if not jobs or not cv_data:
        return jobs

    selected_model = st.session_state.get('ranking_engine', 'Groq / Llama 3.3')
    # On limite le tri aux 20 premières offres pour la rapidité
    limit_tri = 20
    jobs_to_rank = jobs[:limit_tri]
    
    # On simplifie le format pour ne laisser aucune place à l'ambiguïté pour l'IA
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
        response_text = call_ai_provider(prompt, selected_model, is_json=True)
        if not response_text:
            return jobs
            
        ranking_data = json.loads(response_text).get("ranking", [])
        
        ranked_list = []
        ranked_indices = []
        for item in ranking_data:
            try:
                # Conversion explicite en int car certains modèles (Gemini) renvoient souvent des strings "0", "1"...
                idx_raw = item.get("id")
                score_raw = item.get("score")
                
                # Nettoyage de l'ID au cas où Gemini renverrait "ID: 0" au lieu de 0
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
            except (ValueError, TypeError):
                continue

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
    """Tente de récupérer la localisation de l'utilisateur via son adresse IP (multi-sources)."""
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Détection de l'IP réelle du client (indispensable sur Streamlit Cloud)
    client_ip = ""
    try:
        # st.context.headers est disponible dans les versions récentes de Streamlit
        if hasattr(st, "context") and "X-Forwarded-For" in st.context.headers:
            # X-Forwarded-For contient souvent une liste d'IPs, on prend la première
            client_ip = st.context.headers.get("X-Forwarded-For").split(",")[0].strip()
    except:
        pass

    # Tentative 1: ipapi.co
    try:
        url = f"https://ipapi.co/{client_ip}/json/" if client_ip else "https://ipapi.co/json/"
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            city, country = data.get("city"), data.get("country_name")
            if city and country:
                return f"{city}, {country}"
    except:
        pass

    # Tentative 2: ip-api.com
    try:
        url = f"http://ip-api.com/json/{client_ip}" if client_ip else "http://ip-api.com/json/"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            city, country = data.get("city"), data.get("country")
            if city and country:
                return f"{city}, {country}"
    except:
        pass

    # Tentative 3: ipinfo.io
    try:
        url = f"https://ipinfo.io/{client_ip}/json" if client_ip else "https://ipinfo.io/json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            city, country = data.get("city"), data.get("country")
            if city and country:
                return f"{city}, {country}"
    except:
        pass

    return None

def clean_job_title(title):
    """Nettoie le titre du poste pour optimiser la recherche (le dénominateur optimisé)."""
    if not title: return ""
    
    # Gestion sécurisée si l'IA renvoie une liste au lieu d'une chaîne
    if isinstance(title, list):
        title = " ".join(map(str, title))
        
    clean = title.lower()
    # Suppression des mentions H/F, F/H, etc., de manière robuste avec regex
    # Ajout de flags pour ignorer la casse et gestion des espaces multiples
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
    # On ne garde que la partie principale avant les séparateurs courants
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()

def analyze_cv(text, target_lang="français"):
    """Envoie le texte à Groq et parse la réponse JSON."""
    selected_model = st.session_state.get('analysis_engine', 'Groq / Llama 3.3')
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
        response_text = call_ai_provider(prompt, selected_model, is_json=True)
        if not response_text:
            return None
            
        return json.loads(response_text)
    except json.JSONDecodeError as je:
        logger.error(f"JSONDecodeError: {je}")
        if response_text:
            logger.error(f"Réponse brute ayant échoué : {response_text}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du CV : {e}")
        return None

def generate_cover_letter(cv_data, job_title, company, job_description="", target_lang="français"):
    """Génère une lettre de motivation personnalisée via Groq."""
    if not cv_data:
        return None
    selected_model = st.session_state.get('ranking_engine', 'Groq / Llama 3.3')

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
        return call_ai_provider(prompt, selected_model, is_json=False)
    except Exception:
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
        logger.error(f"Erreur lors du scraping France Travail : {e}")
        return jobs

def chercher_offres_jobspy(job_title, location="Paris, France", limit=10):
    """Effectue une recherche via la bibliothèque jobspy."""
    try:
        clean_title = clean_job_title(job_title)
        jobs_df = scrape_jobs(
            site_name=["indeed", "linkedin", "zip_recruiter", "glassdoor"],
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
                    "date_posted": row.get("date_posted"),
                    "location": row.get("location"),
                    "description": row.get("description")
                })
        return results
    except Exception as e:
        logger.error(f"Erreur Jobspy: {e}")
        return []

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
        # On s'assure que le lien est une chaîne de caractères valide pour st.link_button
        safe_link = str(link) if link and not (isinstance(link, float) and pd.isna(link)) else "#"
        with btn_c1:
            st.link_button("🌐 Voir l'offre", safe_link, use_container_width=True)
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

# --- SIDEBAR CONFIGURATION (Language first) ---
with st.sidebar:

    lang_choice = st.selectbox("🌐 Langue / Language", list(LANGS.keys()), index=0)
    lang_data = LANGS[lang_choice]
    st.session_state['lang_code'] = lang_data['code']
    st.session_state['lang_label'] = lang_data['label']
    
    # Get current strings for UI
    S = STRINGS[st.session_state['lang_code']]

    # --- LOGIQUE DE GÉOLOCALISATION : DÉTECTION ET INITIALISATION ---
    # 1. Vérification des coordonnées GPS dans l'URL (Priorité haute)
    q_params = st.query_params
    if "lat" in q_params and "lon" in q_params:
        lat, lon = q_params["lat"], q_params["lon"]
        logger.info(f"📍 Coordonnées GPS détectées dans l'URL : {lat}, {lon}")
        precise_loc = reverse_geocoding(lat, lon)
        if precise_loc:
            st.session_state['user_location'] = precise_loc
        # Nettoyage immédiat pour éviter les boucles infinies sur Nominatim
        st.query_params.clear()
        st.rerun()

    # 2. Initialisation par défaut ou IP (si premier lancement)
    if 'user_location' not in st.session_state:
        detected_loc = get_geolocation()
        st.session_state['user_location'] = detected_loc if detected_loc else lang_data['default_loc']
        logger.info(f"📍 Localisation initiale définie : {st.session_state['user_location']}")

    st.header(S['settings'])

    # --- LOGIQUE DE STATUT IA (CONSOLE) ---
    if is_ollama_online():
        ver = get_ollama_version()
        logger.info(f"Ollama est en ligne (v{ver if ver else 'inconnue'})")
    else:
        logger.warning("Ollama est hors ligne. Lancez Ollama sur votre machine pour utiliser les modèles (Local/dev).")

    # --- SÉLECTION DES MOTEURS IA ---
    st.subheader("🔬 Configuration IA")
    st.selectbox("🔬 Analyse du CV", 
                 ["Gemini 3.5", "Gemini 2.5", "Groq / Llama 3.3", "Llama 3.2 (Local/dev)", "Llama 3.2 Vision (Local/dev)"], 
                 index=2, key='analysis_engine',
                 help="Llama 3.3 via Groq est ultra-rapide et gratuit.")
    
    st.selectbox("⚖️ Tri & Rédaction", 
                 ["Gemini 3.5", "Gemini 2.5", "Groq / Llama 3.3", "Llama 3.2 (Local/dev)", "Qwen 3 4B (Local/dev)"], 
                 index=2, key='ranking_engine',
                 help="Choisissez le moteur pour le classement des offres et les lettres.")

    st.text_input("🔑 Clé API Gemini personnelle", 
                  type="password", 
                  key="custom_gemini_key",
                  help="Utilisez votre propre clé de Google AI Studio pour éviter les limites de quota partagées.")
    
    st.caption("ℹ️ [Obtenir une clé API gratuite ici](https://aistudio.google.com/app/apikey)")

# --- MAIN UI ---
st.title(S['title'])
st.markdown(f"#### {S['subtitle']}")

# --- INITIALISATION DE L'ÉTAT ---
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""
if 'excluded_sources' not in st.session_state:
    st.session_state['excluded_sources'] = set()

uploaded_file = st.file_uploader(S['upload'], type=["pdf"], help="Glissez votre fichier PDF directement dans cette zone.")

if uploaded_file is not None:
    # On crée un identifiant unique pour le fichier pour éviter de re-analyser inutilement
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get('last_processed_file') != file_id:
        with st.spinner(S['analyze']):
            cv_text = extract_text_from_pdf(uploaded_file)
            # On vérifie qu'on a assez de texte (au moins 50 caractères) pour une analyse pertinente
            if cv_text and len(cv_text) > 50:
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
                    last_err = st.session_state.get('last_ai_error', "")
                    engine = st.session_state.get('analysis_engine')
                    if "429" in last_err or "quota" in last_err.lower():
                        st.error("🛑 **Quota Gemini épuisé** (limite de l'offre gratuite). Veuillez patienter 60 secondes ou passez sur 'Groq / Llama 3.3'.")
                    elif "sécurité" in last_err or "safety" in last_err.lower():
                        st.error("🛡️ **Filtre de sécurité** : Google a refusé d'analyser ce contenu. Essayez avec Groq.")
                    elif engine and "Groq" in engine:
                        st.error("❌ **Problème Groq / Llama 3.3** : Le moteur est indisponible. Veuillez sélectionner **Gemini 3.5** dans la barre latérale pour analyser votre CV.")
                    else:
                        st.error(f"❌ L'analyse avec {engine} a échoué. Vérifiez vos logs ou essayez avec Groq.")
            else:
                st.error("⚠️ Impossible d'extraire du texte. Si c'est un scan (photo), l'IA ne pourra pas le lire sans OCR.")

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

# --- FILTRES DE RECHERCHE INTÉGRÉS ---
with st.container(border=True):
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        num_ads = st.slider(S['num_ads'], min_value=1, max_value=50, value=10)
        sort_option = st.selectbox(S['sort_by'], [S['sort_relevant'], S['sort_recent'], S['sort_closest']])
    with col_f2:
        contrat = st.selectbox(S['contract'], ["CDI", "CDD", "Alternance", "Stage", "Interim"])
        remote = st.checkbox(S['remote'])
        global_search = False
        if remote:
            global_search = st.checkbox(S['global_search'], value=False)
    with col_f3:
        if global_search:
            ville = ""
            st.caption(f"🌐 {S['global_search']}")
        else:
            ville = st.text_input(S['location'], value=st.session_state['user_location'])
            st.session_state['user_location'] = ville
    
    st.markdown(f"**{S.get('select_sources', '📡 Sources')}**")
    all_available_sources = ["LinkedIn", "Indeed", "France Travail", "Google Jobs", "Adzuna", "Jooble", "Glassdoor", "ZipRecruiter", "Simplyhired", "Careerbuilder", "Monster"]
    selected_sources = []
    # Affichage des sources sur 4 colonnes pour la compacité
    src_cols = st.columns(4)
    for i, source in enumerate(all_available_sources):
        if src_cols[i % 4].checkbox(source, value=True, key=f"main_src_{source}"):
            selected_sources.append(source)
    
    if st.button(S.get('relaunch', 'Refresh'), key="main_relaunch", use_container_width=True):
        st.rerun()

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
        
        # Reset results
        st.session_state['offres'] = pd.DataFrame()
        st.session_state['job_ads_ft'] = []
        st.session_state['job_ads_adzuna'] = []
        st.session_state['job_ads_serpapi'] = []
        st.session_state['job_ads_jooble'] = []
        st.session_state['job_ads_apify'] = []

        # Utilisation du multi-threading pour accélérer la recherche
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            
            # On prépare les appels conditionnels
            js_sites = ["Indeed", "LinkedIn", "Google Jobs", "Glassdoor", "ZipRecruiter", "Simplyhired", "Careerbuilder", "Monster"]
            if any(s in selected_sources for s in js_sites):
                futures['jobspy'] = executor.submit(chercher_offres_jobspy, manual_query, ville_search, num_ads)
            
            if "Adzuna" in selected_sources:
                futures['adzuna'] = executor.submit(get_adzuna_jobs, manual_query, ville_search, num_ads)
                
            if "Google Jobs" in selected_sources:
                futures['serpapi'] = executor.submit(get_serpapi_jobs, manual_query, ville_search, num_ads)
                
            if "Jooble" in selected_sources:
                futures['jooble'] = executor.submit(get_jooble_jobs, manual_query, ville_search, num_ads)
                
            if "LinkedIn" in selected_sources:
                futures['apify'] = executor.submit(get_apify_jobs, manual_query, ville_search, num_ads)

            # Récupération sécurisée
            if 'jobspy' in futures: st.session_state['offres'] = pd.DataFrame(futures['jobspy'].result())
            if 'adzuna' in futures: st.session_state['job_ads_adzuna'] = futures['adzuna'].result()
            if 'serpapi' in futures: st.session_state['job_ads_serpapi'] = futures['serpapi'].result()
            if 'jooble' in futures: st.session_state['job_ads_jooble'] = futures['jooble'].result()
            if 'apify' in futures: st.session_state['job_ads_apify'] = futures['apify'].result()
        
        # Cas particulier France Travail
        if "France Travail" in selected_sources:
            if ft_client_id and ft_client_secret:
                st.session_state['job_ads_ft'] = get_france_travail_jobs_api(manual_query, limit=num_ads)
            
            if not st.session_state['job_ads_ft']:
                st.session_state['job_ads_ft'] = scrape_france_travail_jobs(manual_query, limit=num_ads)

        # --- UNIFICATION ET TRI IA ---
        all_results = []
        # Collecter JobSpy
        if st.session_state['offres'] is not None and not st.session_state['offres'].empty:
            for i, row in st.session_state['offres'].iterrows():
                js_site = str(row.get('site', 'JobSpy')).lower()
                # Standardisation des noms pour le filtrage
                source_label = "LinkedIn" if js_site == "linkedin" else ("Google Jobs" if js_site == "google" else js_site.capitalize())
                
                all_results.append({
                    "title": row.get('title', 'N/A'), "company": row.get('company', 'N/A'),
                    "link": row.get('job_url', '#'), "source": source_label,
                    "date": str(row.get('date_posted', '')),
                    "location": row.get('location', ''),
                    "desc": row.get('description', ""), "id": f"js_{i}_{hash(row.get('job_url'))}"
                })
        
        # Collecter APIs
        api_sources = [
            ('job_ads_adzuna', 'Adzuna'), 
            ('job_ads_serpapi', 'Google Jobs'), 
            ('job_ads_jooble', 'Jooble'), 
            ('job_ads_apify', 'LinkedIn'),
            ('job_ads_ft', 'France Travail')
        ]
        for key, name in api_sources:
            for i, ad in enumerate(st.session_state.get(key, [])):
                all_results.append({
                    "title": ad.get('titre'), "company": ad.get('entreprise'),
                    "link": ad.get('lien'), "source": ad.get('source', name),
                    "date": str(ad.get('date', '')), "location": ad.get('location', ''),
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

        # --- LOGGING DES RÉSULTATS EN CONSOLE ---
        logger.info("=== RÉSUMÉ DU SCAN DES SOURCES ===")
        source_counts = {}
        for res in all_results:
            src = res.get('source', 'Inconnue')
            source_counts[src] = source_counts.get(src, 0) + 1
        
        # Sources sélectionnées mais vides
        for src in selected_sources:
            if src not in source_counts:
                logger.warning(f"❌ SOURCE SANS RÉSULTAT (OU ÉCHEC) : {src}")
            else:
                logger.info(f"✅ SOURCE RÉUSSIE : {src} ({source_counts[src]} offres)")
        
        # Cas spécial pour les sources agrégées par JobSpy
        if 'jobspy' in futures and not st.session_state['offres'].empty:
            logger.info(f"ℹ️ Détails JobSpy : {st.session_state['offres']['site'].value_counts().to_dict()}")
        
        st.session_state['ranked_results'] = all_results

# --- TABLEAU DE BORD DES SOURCES ---
if st.session_state['offres'] is not None or st.session_state['job_ads_ft'] is not None:
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(S['scan_state'])
    st.caption(S.get('scan_help', ''))
    
    # Extraction des statistiques
    js_df = st.session_state['offres']
    js_counts = js_df['site'].value_counts().to_dict() if js_df is not None and not js_df.empty else {}
    ft_count = len(st.session_state['job_ads_ft']) if st.session_state['job_ads_ft'] else 0
    adzuna_count = len(st.session_state.get('job_ads_adzuna', []))
    serpapi_count = len(st.session_state.get('job_ads_serpapi', []))
    jooble_count = len(st.session_state.get('job_ads_jooble', []))
    apify_count = len(st.session_state.get('job_ads_apify', []))
    
    # Agrégation des comptes par LABEL unique pour éviter les doublons
    counts_by_label = {
        "LinkedIn": apify_count + js_counts.get('linkedin', 0),
        "Indeed": js_counts.get('indeed', 0),
        "France Travail": ft_count,
        "Google Jobs": serpapi_count + js_counts.get('google', 0),
        "Adzuna": adzuna_count,
        "Jooble": jooble_count,
        "Glassdoor": js_counts.get('glassdoor', 0),
        "ZipRecruiter": js_counts.get('zip_recruiter', 0),
        "SimplyHired": js_counts.get('simplyhired', 0),
        "CareerBuilder": js_counts.get('careerbuilder', 0),
        "Monster": js_counts.get('monster', 0)
    }
    
    active_sources = []
    for label, count in counts_by_label.items():
        if count > 0:
            active_sources.append((label, count))
        else:
            logger.info(f"🔍 [Console Scan] {label}: 0")

    # Style pour colorer les boutons en fonction de l'état (vert/rouge)
    st.markdown("""
        <style>
        div[data-testid="stColumn"] button {
            border-radius: 8px !important;
            transition: all 0.2s ease;
        }
        /* Style par défaut pour les boutons actifs (Vert) */
        div[data-testid="stColumn"] button p:contains("✅"), 
        div[data-testid="stColumn"] button:has(p:contains("✅")) {
            background-color: #28a745 !important;
            color: white !important;
        }
        /* Style pour les boutons exclus (Rouge) */
        div[data-testid="stColumn"] button p:contains("❌"), 
        div[data-testid="stColumn"] button:has(p:contains("❌")) {
            background-color: #dc3545 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Affichage en grille
    rows = [active_sources[i:i + 4] for i in range(0, len(active_sources), 4)]
    for row in rows:
        status_cols = st.columns(len(row))
        for idx, (label, count) in enumerate(row):
            is_excluded = label in st.session_state['excluded_sources']
            btn_label = f"❌ {label} ({count})" if is_excluded else f"✅ {label} ({count})"
            
            if status_cols[idx].button(btn_label, key=f"tgl_{label}", use_container_width=True):
                if is_excluded:
                    st.session_state['excluded_sources'].remove(label)
                else:
                    st.session_state['excluded_sources'].add(label)
                st.rerun()

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
    
    display_results = st.session_state['ranked_results']
    
    # Logique d'exclusion dynamique des sources
    if st.session_state.get('excluded_sources'):
        display_results = [j for j in display_results if j['source'] not in st.session_state['excluded_sources']]

    st.subheader(f"🔥 {S.get('top_matches', 'Top Matches')}")
    for job in display_results:
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
