import json
import logging
from typing import Optional

from shared.ai import call_ai_provider

logger = logging.getLogger(__name__)


def _get_fallback_strings(target_lang: str) -> dict:
    fallbacks = {
        "fr": {
            "resume": "Analyse en mode secours : profil recruteur détecté automatiquement.",
            "suggestions": [
                "Précisez le niveau d'expérience requis.",
                "Ajoutez les compétences techniques attendues.",
                "Indiquez la fourchette salariale pour affiner les résultats.",
            ],
        },
        "en": {
            "resume": "Fallback analysis: recruiter profile detected automatically.",
            "suggestions": [
                "Specify the required experience level.",
                "Add the expected technical skills.",
                "Indicate the salary range to refine results.",
            ],
        },
        "es": {
            "resume": "Análisis en modo de respaldo: perfil de reclutador detectado automáticamente.",
            "suggestions": [
                "Especifique el nivel de experiencia requerido.",
                "Agregue las habilidades técnicas esperadas.",
                "Indique el rango salarial para refinar los resultados.",
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


def analyze_recruiter_cv(
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
    """Analyse a CV specifically for recruiter candidate matching.

    Focuses on: skills, experience level, salary expectations,
    candidate availability, and recruiter-specific requirements.
    """
    fallback_used = False
    ai_error_reason = None

    if force_fallback_mode:
        logger.warning("[RECRUITER CV] Mode secours forcé pour l'analyse recruteur.")
        fallback_used = True
    else:
        try:
            prompt = f"""Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON en {target_lang} avec les clés suivantes :

"nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier),
"niveau_experience" (débutant, junior, confirmé, senior, expert),
"salaire_min" (salaire minimum attendu en euros/mois, nombre), "salaire_max" (salaire maximum attendu en euros/mois, nombre),
"competences_techniques" (liste de compétences techniques),
"soft_skills" (liste de compétences comportementales),
"disponibilite" (immédiat, 1 mois, 3 mois, 6 mois),
"type_contrat_preference" (liste : CDI, CDD, Stage, Alternance, Intérim, Temps partiel),
"recommandations_candidats" (liste de 5 types de postes adaptés à ce candidat),
"suggestions_amelioration" (liste de 3 à 5 conseils pour améliorer le profil candidat).

LOGIQUE D'IDENTIFICATION DU CANDIDAT :
- Identifie le niveau d'expérience réel basé sur les années et les responsabilités.
- Détecte les compétences techniques clés pour le matching.
- Estime la fourchette salariale raisonnable.

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
                            logger.info("[RECRUITER CV] Analyse CV = IA (réponse valide)")
                            data["is_fallback"] = False
                            data["agent_type"] = "recruiter"
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

    logger.warning(f"[RECRUITER CV] Mode secours. Raison: {ai_error_reason}. Utilisation du parser regex local.")
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
        "niveau_experience": "",
        "salaire_min": 0,
        "salaire_max": 0,
        "competences_techniques": [],
        "soft_skills": [],
        "disponibilite": "",
        "type_contrat_preference": [],
        "recommandations_candidats": [metier],
        "suggestions_amelioration": _get_fallback_strings(target_lang)["suggestions"],
        "is_fallback": fallback_used,
        "agent_type": "recruiter",
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
    return "Candidat"