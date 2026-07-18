"""Fonctions d'appel aux fournisseurs d'IA : Groq, Gemini, Ollama, xAI."""

import json
import logging
import re
from typing import Optional, List, Dict, Any

import requests
from groq import Groq
import google.generativeai as genai

logger = logging.getLogger(__name__)


def is_ollama_online(ollama_url: str = "http://localhost:11434") -> bool:
    """Vérifie si le serveur Ollama répond."""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_ollama_version(ollama_url: str = "http://localhost:11434") -> Optional[str]:
    """Récupère la version d'Ollama via l'API."""
    try:
        response = requests.get(f"{ollama_url}/api/version", timeout=2)
        if response.status_code == 200:
            return response.json().get("version")
    except Exception:
        return None
    return None


def call_local_llama(prompt: str, model_name: str, ollama_url: str = "http://localhost:11434", is_json: bool = False) -> Optional[str]:
    """Appelle l'instance locale d'Ollama."""
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


def call_ai_provider(
    prompt: str,
    selected_model: str,
    is_json: bool = False,
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[str]:
    """Fonction centralisée pour appeler Gemini, Groq, xAI ou Ollama.

    Args:
        prompt: Le texte du prompt à envoyer.
        selected_model: Le nom du modèle sélectionné (ex: "Gemini 3.5", "Groq / Llama 3.3").
        is_json: Si True, demande une réponse JSON structurée.
        gemini_api_key: Clé API Gemini du .env.
        xai_api_key: Clé API xAI (Grok) du .env.
        groq_api_key: Clé API Groq du .env.
        ollama_url: URL du serveur Ollama local.
        custom_gemini_key: Clé API Gemini personnalisée saisie par l'utilisateur.

    Returns:
        Texte de la réponse ou None en cas d'erreur.
    """
    active_gemini_key = (custom_gemini_key or gemini_api_key or "").strip()

    try:
        if "Gemini" in selected_model:
            if not active_gemini_key:
                raise Exception("Clé API Gemini manquante.")
            genai.configure(api_key=active_gemini_key)
            model_id = "models/gemini-2.0-flash" if "3.5" in selected_model else "models/gemini-1.5-flash"
            logger.info(f"Appel Gemini AI : {model_id}")
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
                logger.warning(f"Gemini finish_reason inhabituel : {reason}")
                if reason == 3:
                    raise Exception("L'analyse a été bloquée par les filtres de sécurité de Google.")

            try:
                text = response.text
            except (ValueError, AttributeError):
                if response.candidates and len(response.candidates[0].content.parts) > 0:
                    text = response.candidates[0].content.parts[0].text
                else:
                    raise Exception("Gemini a refusé de générer du texte pour ce contenu (Filtre de sécurité).")

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
            return call_local_llama(prompt, ollama_model, ollama_url, is_json=is_json)

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
            if not groq_api_key:
                raise Exception("Clé Groq non configurée")
            client = Groq(api_key=groq_api_key)
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
        raise Exception(err_msg)


def analyze_cv(
    text: str,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[dict]:
    """Analyse un CV via l'IA et retourne un dict structuré."""
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
        response_text = call_ai_provider(
            prompt, selected_model, is_json=True,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
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


def generate_cover_letter(
    cv_data: dict,
    job_title: str,
    company: str,
    job_description: str = "",
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[str]:
    """Génère une lettre de motivation personnalisée via l'IA."""
    if not cv_data:
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
        return call_ai_provider(
            prompt, selected_model, is_json=False,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
    except Exception:
        return None


def rank_jobs_with_ai(
    cv_data: dict,
    jobs: List[dict],
    filters: dict,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> List[dict]:
    """Utilise l'IA pour classer les offres par pertinence par rapport au CV."""
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
        response_text = call_ai_provider(
            prompt, selected_model, is_json=True,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
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
            except (ValueError, TypeError):
                continue

        for i in range(len(jobs_to_rank)):
            if i not in ranked_indices:
                ranked_list.append(jobs_to_rank[i])

        if len(jobs) > limit_tri:
            ranked_list.extend(jobs[limit_tri:])

        return ranked_list
    except Exception as e:
        logger.error(f"Erreur tri IA: {e}")
        return jobs


def estimate_workload(
    mission_description: str,
    mission_title: str = "",
    cv_data: Optional[dict] = None,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
) -> Optional[dict]:
    """Estime la charge de travail d'une mission freelance via l'IA."""
    
    # Build context about the candidate if available
    candidate_context = ""
    if cv_data:
        candidate_context = f"""
        PROFIL DU CANDIDAT :
        - Métier : {cv_data.get('metier', 'Non spécifié')}
        - Années d'expérience : {cv_data.get('annees_experience', 'Non spécifié')}
        - Compétences clés : {', '.join(cv_data.get('mots_cles', []))}
        """
    
    prompt = f"""
    Tu es un expert en estimation de projets freelance. Analyse cette mission et estime la charge de travail.
    
    TITRE DE LA MISSION : {mission_title}
    DESCRIPTION DE LA MISSION :
    {mission_description}
    
    {candidate_context}
    
    INSTRUCTIONS :
    Retourne UNIQUEMENT un objet JSON avec les clés suivantes :
    {{
        "estimated_hours": nombre entier d'heures estimées (arrondi à la dizaine la plus proche),
        "complexity_level": "low", "medium", "high", ou "very_high",
        "complexity_description": brève description du niveau de complexité (1-2 phrases),
        "key_tasks": liste de 3-5 tâches principales pour cette mission,
        "recommended_duration": durée recommandée en jours ou semaines
    }}
    
    Pour estimated_hours :
    - Faible complexité : 8-40 heures
    - Complexité moyenne : 40-80 heures  
    - Haute complexité : 80-160 heures
    - Très haute complexité : 160+ heures
    """
    
    try:
        response_text = call_ai_provider(
            prompt, selected_model, is_json=True,
            gemini_api_key=gemini_api_key, xai_api_key=xai_api_key,
            groq_api_key=groq_api_key, ollama_url=ollama_url,
            custom_gemini_key=custom_gemini_key
        )
        if not response_text:
            return None
            
        return json.loads(response_text)
    except json.JSONDecodeError as je:
        logger.error(f"JSONDecodeError in workload estimation: {je}")
        if response_text:
            logger.error(f"Response text: {response_text}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'estimation de la charge de travail: {e}")
        return None