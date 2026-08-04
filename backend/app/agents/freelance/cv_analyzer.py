import json
import logging
from typing import Optional

from shared.ai import call_ai_provider

logger = logging.getLogger(__name__)


def _get_fallback_strings(target_lang: str) -> dict:
    fallbacks = {
        "fr": {
            "resume": "Analyse en mode secours : profil freelance détecté automatiquement.",
            "suggestions": [
                "Précisez votre TJM souhaité dans votre profil.",
                "Ajoutez vos compétences techniques pour une meilleure matching.",
                "Indiquez votre expérience en freelance pour des recommandations ciblées.",
            ],
        },
        "en": {
            "resume": "Fallback analysis: freelance profile detected automatically.",
            "suggestions": [
                "Specify your desired TJM in your profile.",
                "Add your technical skills for better matching.",
                "Indicate your freelance experience for targeted recommendations.",
            ],
        },
        "es": {
            "resume": "Análisis en modo de respaldo: perfil freelance detectado automáticamente.",
            "suggestions": [
                "Especifique su TJM deseado en su perfil.",
                "Agregue sus habilidades técnicas para una mejor coincidencia.",
                "Indique su experiencia como freelance para recomendaciones específicas.",
            ],
        },
    }
    lang_key = "fr"
    if target_lang:
        lower = target_lang.lower()
        if "anglais" in lower or "english" in lower:
            lang_key = "en"
        elif "espagnol" in lower or "español" in lower:
            lang_key = "es"
    return fallbacks.get(lang_key, fallbacks["fr"])


def analyze_freelance_cv(
    text: str,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
    force_fallback_mode: bool = False,
) -> dict:
    """Analyse a CV specifically for freelance mission matching.

    Focuses on: skills, hourly rates, project types, duration preferences,
    remote work preferences, and freelance-specific experience.
    """
    fallback_used = False
    ai_error_reason = None

    if force_fallback_mode:
        logger.warning("[FREELANCE CV] Mode secours forcé pour l'analyse freelance.")
        fallback_used = True
    else:
        try:
            prompt = f"""Tu es un expert en recrutement freelance. Analyse ce CV et retourne uniquement un objet JSON en {target_lang} avec les clés suivantes :

"nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier),
"tjm_min" (tarif journalier minimum en euros, nombre), "tjm_max" (tarif journalier maximum en euros, nombre),
"mission_types" (liste de types de missions privilégiées : développement, design, conseil, rédaction, marketing, data, devops, mobile),
"duree_preference" (liste : court terme, moyen terme, long terme, récurrent),
"remote_preference" (liste : remote, hybride, présentiel),
"competences_techniques" (liste de compétences techniques),
"recommandations_metiers" (liste de 5 types de missions freelance suggérées),
"suggestions_amelioration" (liste de 3 à 5 conseils pour améliorer le profil freelance).

LOGIQUE D'IDENTIFICATION DU PROFIL FREELANCE :
- Identifie le TJM optimal basé sur les années d'expérience et les compétences.
- Détecte les préférences de travail à distance.
- Identifie les types de missions les plus adaptés au profil.

Texte du CV :
{text}"""
            response_text = call_ai_provider(
                prompt,
                selected_model,
                is_json=True,
                gemini_api_key=gemini_api_key,
                xai_api_key=xai_api_key,
                groq_api_key=groq_api_key,
                ollama_url=ollama_url,
                custom_gemini_key=custom_gemini_key,
            )
            if response_text:
                try:
                    data = json.loads(response_text)
                    metier = (data.get("metier") or "").strip()
                    if metier and not _is_placeholder_value(metier):
                        invalid_fields = [
                            k for k in ["nom_complet", "contact", "resume"]
                            if _is_placeholder_value(data.get(k))
                        ]
                        if len(invalid_fields) <= 1:
                            logger.info("[FREELANCE CV] Analyse CV = IA (réponse valide)")
                            data["is_fallback"] = False
                            data["agent_type"] = "freelance"
                            return data
                        ai_error_reason = f"IA: champs placeholders detects={invalid_fields}"
                    else:
                        ai_error_reason = "IA: metier vide ou placeholder"
                except (json.JSONDecodeError, TypeError) as e:
                    ai_error_reason = f"IA: JSON invalide ({e})"
            else:
                ai_error_reason = "IA: réponse vide"
        except Exception as e:
            ai_error_reason = f"IA: exception {e}"

    logger.warning(f"[FREELANCE CV] Mode secours. Raison: {ai_error_reason}. Utilisation du parser regex local.")
    fallback_used = True
    metier = _extract_job_title_fallback(text or "")

    first_lines = " ".join(
        [line.strip() for line in (text or "").splitlines() if line.strip()][:10]
    )
    keywords = []
    for token in __import__("re").split(r"[^A-Za-zÀ-ÖØ-öø-ÿ]+", first_lines):
        t = token.strip()
        if 3 <= len(t) <= 30:
            keywords.append(t)
    keywords = list(dict.fromkeys(keywords))[:12]

    return {
        "nom_complet": "",
        "contact": "",
        "metier": metier,
        "mots_cles": keywords,
        "resume": _get_fallback_strings(target_lang)["resume"],
        "annees_experience": 0,
        "tjm_min": 0,
        "tjm_max": 0,
        "mission_types": [],
        "duree_preference": [],
        "remote_preference": ["remote"],
        "competences_techniques": [],
        "recommandations_metiers": [metier],
        "suggestions_amelioration": _get_fallback_strings(target_lang)["suggestions"],
        "is_fallback": fallback_used,
        "agent_type": "freelance",
    }


def _is_placeholder_value(value) -> bool:
    if not value or not isinstance(value, str):
        return True
    v = value.lower().strip()
    placeholders = [
        "inconnu", "unknown", "n/a", "na", "none", "null", "",
        "pas de", "no", "tbd", "to be determined",
    ]
    return v in placeholders


def _extract_job_title_fallback(text: str) -> str:
    import re
    patterns = [
        r"(?:développeur|developer|dev|programmeur|programmer)\s+(?:web|full.?stack|front.?end|back.?end|mobile|python|javascript|react|node|java|c#)?",
        r"(?:designer|UX|UI|graphiste|illustrateur)",
        r"(?:consultant|conseil|consulting)",
        r"(?:rédacteur|writer|copywriter|content)",
        r"(?:marketeur|marketer|growth|product)",
        r"(?:data.?scientist|data.?analyst|ML|IA|intelligence.?artificielle)",
        r"(?:devops|SRE|administrateur.?système|sysadmin)",
        r"(?:mobile|iOS|Android|flutter|react.?native)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "Freelance"