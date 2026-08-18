"""
LLM Provider Management Service with Robust API Key Handling and Fallback Strategy

This service implements:
1. Multi-provider LLM management (Groq, Gemini, Mistral)
2. Priority-based fallback: User API Key > Groq Shared > Gemini Backup
3. Strict JSON validation for AI responses
4. Rate limit handling and retry logic
5. Comprehensive error handling and logging
"""

import json
import logging
import re
import time
from typing import Optional, List, Dict, Any, Tuple
import requests
from groq import Groq, RateLimitError as GroqRateLimitError

# Import configuration
from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

class LLMProviderManager:
    """Manages multiple LLM providers with fallback strategy and API key management."""

    def __init__(self):
        self.groq_client = None
        self.gemini_client = None
        self.mistral_client = None
        self.fallback_attempts = 0
        self.max_fallback_attempts = 3
        self.fallback_delay = 1  # seconds

    def initialize_clients(self):
        """Initialize LLM clients based on available API keys."""
        try:
            # Initialize Groq client if API key is available
            if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY.strip())
                logger.info("[LLM] Groq client initialized with shared API key")
            else:
                logger.warning("[LLM] No Groq API key found in settings")

            # Initialize Gemini client if API key is available
            if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
                try:
                    from google import genai
                    from google.genai import types
                    self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
                    logger.info("[LLM] Gemini client initialized with backup API key")
                except ImportError:
                    logger.warning("[LLM] Google Generative AI SDK not available")

            # Mistral client will be initialized with user-provided keys when needed

        except Exception as e:
            logger.error(f"[LLM] Error initializing LLM clients: {str(e)}")

    def validate_json_response(self, response_text: str) -> Tuple[bool, Optional[dict]]:
        """Validate that the AI response is proper JSON and extract it."""
        if not response_text:
            return False, None

        try:
            # Try to parse the entire response as JSON
            try:
                data = json.loads(response_text)
                return True, data
            except json.JSONDecodeError:
                pass

            # If that fails, try to extract JSON from the response
            json_match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return True, data
                except json.JSONDecodeError:
                    pass

            # If still no valid JSON, try to extract JSON objects more aggressively
            json_objects = re.findall(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_objects:
                try:
                    data = json.loads(json_objects[0])
                    return True, data
                except json.JSONDecodeError:
                    pass

            return False, None

        except Exception as e:
            logger.error(f"[LLM] JSON validation error: {str(e)}")
            return False, None

    def call_groq_with_retry(self, prompt: str, is_json: bool = False, max_retries: int = 3) -> Optional[str]:
        """Call Groq API with retry logic for rate limits."""
        if not self.groq_client:
            logger.warning("[LLM] Groq client not initialized")
            return None

        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                params = {
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "qwen/qwen3.6-27b",
                    "reasoning_effort": "none",
                }

                response = self.groq_client.chat.completions.create(**params)
                return response.choices[0].message.content

            except GroqRateLimitError as e:
                last_error = e
                retries += 1
                wait_time = 2 ** retries  # Exponential backoff
                logger.warning(f"[LLM] Groq rate limit hit (attempt {retries}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(f"[LLM] Groq API error: {str(e)}")
                break

        logger.error(f"[LLM] Groq failed after {retries} retries. Last error: {str(last_error)}")
        return None

    def call_gemini_with_retry(self, prompt: str, is_json: bool = False, max_retries: int = 2) -> Optional[str]:
        """Call Gemini API with retry logic."""
        if not self.gemini_client:
            logger.warning("[LLM] Gemini client not initialized")
            return None

        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                model_id = "gemini-3.5-flash"
                config = None

                if is_json:
                    from google.genai import types
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )

                response = self.gemini_client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=config
                )

                # Extract text from response
                try:
                    text = response.text
                except (ValueError, AttributeError):
                    if hasattr(response, "candidates") and response.candidates:
                        text = response.candidates[0].content.parts[0].text
                    else:
                        raise Exception("Gemini response has no text content")

                return text

            except Exception as e:
                last_error = e
                retries += 1
                if retries < max_retries:
                    wait_time = 1 * retries
                    logger.warning(f"[LLM] Gemini error (attempt {retries}/{max_retries}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[LLM] Gemini failed after {retries} retries. Last error: {str(last_error)}")
                    break

        return None

    def call_mistral_with_retry(self, prompt: str, api_key: str, is_json: bool = False, max_retries: int = 2) -> Optional[str]:
        """Call Mistral API with retry logic."""
        if not api_key or not api_key.strip():
            logger.warning("[LLM] No Mistral API key provided")
            return None

        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                headers = {
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "mistral-small",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }

                if is_json:
                    payload["response_format"] = {"type": "json_object"}

                response = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                last_error = e
                retries += 1
                if retries < max_retries:
                    wait_time = 1 * retries
                    logger.warning(f"[LLM] Mistral API error (attempt {retries}/{max_retries}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[LLM] Mistral failed after {retries} retries. Last error: {str(last_error)}")
                    break

        return None

    def call_llm_with_fallback(
        self,
        prompt: str,
        is_json: bool = False,
        user_gemini_key: Optional[str] = None,
        user_mistral_key: Optional[str] = None,
        selected_model: str = "Groq / Llama 3.3"
    ) -> Optional[str]:
        """
        Call LLM providers with comprehensive fallback strategy.

        Priority order:
        1. User-provided API keys (Gemini/Mistral) - highest priority
        2. Shared Groq API key - default for most users
        3. Backup Gemini API key - final fallback
        """

        # Track which providers we've tried
        tried_providers = []

        # Priority 1: User-provided API keys (highest priority)
        if user_gemini_key and (user_gemini_key.strip()):
            logger.info("[LLM] Attempting Gemini with user API key (highest priority)")
            tried_providers.append("gemini_user")
            result = self.call_gemini_with_retry(prompt, is_json)
            if result:
                logger.info("[LLM] Success: Gemini with user API key")
                return result

        if user_mistral_key and (user_mistral_key.strip()):
            logger.info("[LLM] Attempting Mistral with user API key (highest priority)")
            tried_providers.append("mistral_user")
            result = self.call_mistral_with_retry(prompt, user_mistral_key, is_json)
            if result:
                logger.info("[LLM] Success: Mistral with user API key")
                return result

        # Priority 2: Shared Groq API key (default for most users)
        if self.groq_client:
            logger.info("[LLM] Attempting Groq with shared API key (priority 2)")
            tried_providers.append("groq_shared")
            result = self.call_groq_with_retry(prompt, is_json)
            if result:
                logger.info("[LLM] Success: Groq with shared API key")
                return result

        # Priority 3: Backup Gemini API key (final fallback)
        if self.gemini_client:
            logger.info("[LLM] Attempting Gemini with backup API key (priority 3)")
            tried_providers.append("gemini_backup")
            result = self.call_gemini_with_retry(prompt, is_json)
            if result:
                logger.info("[LLM] Success: Gemini with backup API key")
                return result

        logger.error(f"[LLM] All LLM providers failed. Tried: {', '.join(tried_providers)}")
        return None

    def analyze_cv_with_robust_fallback(
        self,
        text: str,
        target_lang: str = "français",
        user_gemini_key: Optional[str] = None,
        user_mistral_key: Optional[str] = None,
        selected_model: str = "Groq / Llama 3.3"
    ) -> dict:
        """Analyze CV with robust AI fallback and validation."""

        # Fallback data structure
        fallback_strings = {
            "fr": {
                "resume": "Analyse en mode secours : métier détecté automatiquement à partir du CV.",
                "suggestions": [
                    "Passez votre souris sur une offre pour générer une lettre de motivation personnalisée.",
                    "Utilisez les filtres pour affiner vos sources et votre type de contrat.",
                    "Téléversez un CV plus complet pour obtenir une analyse plus précise.",
                ],
            },
            "en": {
                "resume": "Fallback analysis: job detected automatically from the CV.",
                "suggestions": [
                    "Hover over an offer to generate a personalized cover letter.",
                    "Use filters to refine your sources and contract type.",
                    "Upload a more complete CV for a more accurate analysis.",
                ],
            },
        }

        lang_key = "fr"
        if target_lang:
            lower = target_lang.lower()
            if "anglais" in lower or "english" in lower:
                lang_key = "en"

        # Try AI analysis first
        try:
            prompt = f"""Tu es un expert en recrutement. Analyse ce CV et retourne uniquement un objet JSON en {target_lang} avec les clés suivantes :
            "nom_complet", "contact", "metier", "mots_cles" (liste de chaînes), "resume" (maximum 3 lignes), "annees_experience" (nombre entier), "recommandations_metiers" (liste de 5 métiers suggérés), "metiers_alternatifs" (liste de 3 métiers radicalement différents utilisant les mêmes compétences transférables), "suggestions_amelioration" (liste de 3 à 5 conseils concrets pour améliorer l'impact de ce CV).

            LOGIQUE D'IDENTIFICATION DU MÉTIER :
            - Si le profil contient des métiers multiples (ex: "Consultant & Développeur"), NE les regroupe PAS.
            - Sélectionne le métier le plus porteur/pertinent pour une recherche d'emploi actuelle comme "metier" principal.
            - Place le second métier (ou les métiers connexes identifiés) en priorité absolue au début de la liste "recommandations_metiers".

            Texte du CV :
            {text}"""

            response_text = self.call_llm_with_fallback(
                prompt,
                is_json=True,
                user_gemini_key=user_gemini_key,
                user_mistral_key=user_mistral_key,
                selected_model=selected_model
            )

            if response_text:
                is_valid, data = self.validate_json_response(response_text)
                if is_valid and data:
                    metier = (data.get("metier") or "").strip()
                    if metier and len(metier) > 2 and metier.lower() not in ["non fourni", "non communiqué", "inconnu"]:
                        # Validate other key fields
                        invalid_fields = []
                        for field in ["nom_complet", "contact", "resume"]:
                            value = data.get(field, "")
                            if not value or len(value.strip()) < 2:
                                invalid_fields.append(field)

                        if len(invalid_fields) <= 1:  # Allow one missing field
                            data["is_fallback"] = False
                            data["ai_provider_used"] = "success"
                            return data

            logger.warning("[LLM] AI analysis failed or invalid. Falling back to regex parser.")

        except Exception as e:
            logger.error(f"[LLM] AI analysis error: {str(e)}. Falling back to regex parser.")

        # Fallback: Regex-based CV parsing
        return {
            "nom_complet": "",
            "contact": "",
            "metier": self.extract_job_title_fallback(text),
            "mots_cles": self.extract_keywords_from_text(text),
            "resume": fallback_strings[lang_key]["resume"],
            "annees_experience": 0,
            "recommandations_metiers": [],
            "metiers_alternatifs": [],
            "suggestions_amelioration": fallback_strings[lang_key]["suggestions"],
            "is_fallback": True,
            "ai_provider_used": "regex_fallback"
        }

    def extract_job_title_fallback(self, text: str) -> str:
        """Extract job title using regex patterns as fallback."""
        if not text or not text.strip():
            return "Développeur"

        # Comprehensive job title patterns
        job_patterns = [
            r"(?:Développeur|Développeuse)\s*(?:Web|Full[ -]?Stack|React|Vue|Angular|Node\.?js|Python|Java|JavaScript|PHP|Ruby|Go|Rust|Mobile|iOS|Android|Backend|Frontend|API|Symfony|Laravel|Django|Flask|Spring|C\+\+|C#|\.NET|Embedded|Embarqué|WordPress|Shopify|Webflow)?",
            r"(?:Ingénieur|Ingénieure)\s*(?:Logiciel|Informatique|Développement|Full[ -]?Stack|QA|Test|Validation|R\&D|Systèmes|Conception|Embedded)?",
            r"(?:Scrum\s*Master|Agile\s*Coach|Product\s*Owner|Lead\s*Developer|Tech\s*Lead)",
            r"(?:Intégrateur|Intégratrice)\s*(?:Web|HTML|CSS|CMS)|Webmaster",
            r"(?:Data\s*(?:Scientist|Analyst|Engineer|Architect|Specialist|Consultant|Analyste|Ingénieur))",
            r"(?:Machine\s*Learning\s*(?:Engineer|Scientist)|Ingénieur\s*IA)",
            r"(?:DevOps\s*(?:Engineer|Specialist|Consultant|Ingénieur)?|Cloud\s*Engineer|SRE)",
            r"(?:Architecte\s*(?:Logiciel|Informatique|Cloud|Solution|Data|Système|Web|Infrastructure|SI|Sécurité))",
            r"(?:Administrateur|Administratrice)\s*(?:Système|Réseaux|Base\s*de\s*Données|Cloud|DevOps|Infrastructure|AWS|Azure|GCP|DBA)",
            r"(?:Expert|Ingénieur|Consultant|Analyste)\s*(?:Cybersécurité|Sécurité\s*SI|SOC|Pentester)",
            r"(?:Technicien|Technicienne)\s*(?:Informatique|Support|Réseau|Système|Helpdesk|Micro-informatique|Proximité)",
        ]

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        header_text = " ".join(lines[:15])

        # Try to find job titles in header first
        for pattern in job_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        # Try full text if not found in header
        for pattern in job_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        # Fallback: return first reasonable line
        for line in lines[:5]:
            if len(line) < 60 and not re.search(r"@|phone|tél|adresse|curriculum|cv|permis|français", line, re.IGNORECASE):
                return line

        return "Développeur"

    def extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text for fallback analysis."""
        if not text:
            return []

        first_lines = " ".join(
            [line.strip() for line in text.splitlines() if line.strip()][:10]
        )

        keywords = []
        for token in re.split(r"[^A-Za-zÀ-ÖØ-öø-ÿ]+", first_lines):
            t = token.strip()
            if 3 <= len(t) <= 30:
                keywords.append(t)

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:12]

# Global LLM service instance
llm_service = LLMProviderManager()

def get_llm_service() -> LLMProviderManager:
    """Get the global LLM service instance."""
    return llm_service