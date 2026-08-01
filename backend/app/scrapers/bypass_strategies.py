"""
🔧 BYPASS STRATEGIES MODULE 🔧
Stratégies de contournement et de maximisation des résultats pour scraper/API job sources.
Implémente les 5 stratégies de résilience demandées.
"""
import logging
import random
import re
import asyncio
from typing import List, Dict, Optional, Set, Callable, Any

logger = logging.getLogger(__name__)

# =============================================================================
# 1. 🔄 RELÂCHEMENT AUTOMATIQUE DES REQUÊTES (Query Relaxation / Fallback)
# =============================================================================

def generate_relaxed_queries(original_query: str, max_variations: int = 5) -> List[str]:
    """
    Génère des variantes élargies de la requête pour maximiser les résultats.
    Implémente un relâchement progressif : exact → large → générique.

    Args:
        original_query: La requête de recherche originale
        max_variations: Nombre maximum de variations à générer

    Returns:
        Liste de requêtes élargies, triées par spécificité décroissante
    """
    queries: Set[str] = set()
    queries.add(original_query)

    # 1. Nettoyer et extraire
    clean_q = re.sub(r'[^\w\s,-]', '', original_query)
    queries.add(clean_q)

    # 2. Domain expansion - termes plus larges
    words = original_query.split()
    if len(words) > 2:
        queries.add(" ".join(words[:2]))
        queries.add(words[0])
    elif len(words) > 1:
        queries.add(words[0])

    # 3. Ajouter des variations avec synonymes
    synonym_groups = [
        ["Ingénieur", "Développeur", "Concepteur", "Expert", "Spécialiste", "Technicien"],
        ["IA", "Intelligence Artificielle", "Machine Learning", "Deep Learning", "AI"],
        ["Data", "Données", "Analytics", "Big Data"],
        ["DevOps", "SRE", "Cloud", "Infrastructure"],
        ["Full Stack", "Fullstack", "Frontend", "Backend"],
        ["Intégrateur", "Intégration", "Déploiement", "CI/CD"],
        ["Robotique", "Automatisation", "Automation", "RPA"],
        ["Sécurité", "Cybersécurité", "Security", "SOC"],
        ["Réseau", "Network", "Réseaux", "Infrastructure"],
        ["ERP", "SAP", "Oracle", "CRM"],
        ["Manager", "Lead", "Chef", "Responsable"],
        ["Junior", "Confirmé", "Senior", "Expert"],
    ]

    for group in synonym_groups:
        for term in group:
            if term.lower() in original_query.lower():
                other_terms = [t for t in group if t.lower() != term.lower()]
                for other in other_terms[:2]:
                    relaxed = original_query.replace(term, other, 1)
                    queries.add(relaxed)
                break

    # 4. Termes génériques de dernier recours
    if len(words) >= 1:
        queries.add(words[0])

    # 5. Ajouter des variations avec des termes connexes
    industry_terms = [
        "Informatique", "IT", "Tech", "Numérique", "Digital",
        "Développement", "Programmation", "Software", "Logiciel",
    ]

    for term in industry_terms:
        if term.lower() not in original_query.lower():
            relaxed = f"{original_query} {term}"
            queries.add(relaxed)
            if len(queries) >= max_variations * 2:
                break

    # Trier : d'abord les plus spécifiques, puis les plus génériques
    # Mais toujours inclure la requête originale en premier
    other_queries = queries - {original_query}
    sorted_queries = sorted(
        list(other_queries),
        key=lambda q: (-len(q), -sum(1 for w in q.split() if w and w[0].isupper()))
    )

    # Toujours mettre l'originale en premier
    result = [original_query] + sorted_queries[:max_variations - 1]
    logger.info(f"[BYPASS:QueryRelaxation] Generated {len(result)} variations for '{original_query}': {result}")
    return result


# =============================================================================
# 2. 🛡️ BYPASS DES BLOCAGES & ANTI-BOTS
# =============================================================================

USER_AGENTS: List[str] = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Mobile Chrome Android
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.83 Mobile Safari/537.36",
    # Mobile Safari iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

REFERERS: List[str] = [
    "https://www.google.com/",
    "https://www.google.fr/",
    "https://www.bing.com/",
    "https://search.yahoo.com/",
    "https://www.linkedin.com/",
    "https://www.google.com/search?q=emploi",
    "https://duckduckgo.com/",
]


def get_rotated_headers(custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Génère des en-têtes HTTP avec rotation d'User-Agent pour imiter un navigateur réel.
    """
    user_agent = random.choice(USER_AGENTS)
    is_mobile = "Mobile" in user_agent

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Referer": random.choice(REFERERS),
    }

    if is_mobile:
        headers["Sec-CH-UA-Mobile"] = "?1"
    else:
        headers["Upgrade-Insecure-Requests"] = "1"
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = "none"
        headers["Sec-Fetch-User"] = "?1"

    if custom_headers:
        headers.update(custom_headers)

    return headers


def get_jitter_delay(min_delay: float = 0.5, max_delay: float = 2.0) -> float:
    """Génère un délai aléatoire (jitter) entre les requêtes pour éviter la détection."""
    return random.uniform(min_delay, max_delay)


# =============================================================================
# 3. 🔑 OPTIMISATION DES PARAMÈTRES D'APIS
# =============================================================================

def optimize_location_for_api(location: str, source_name: str) -> str:
    """
    Optimise le paramètre de localisation pour chaque API source.
    Supprime les filtres trop restrictifs et garantit un maximum de volume.
    """
    if not location or location.lower() in ["", "france", "global", "worldwide", "remote"]:
        return "France"

    clean_loc = re.sub(r',?\s*France\s*$', '', location, flags=re.IGNORECASE).strip()

    if "," in clean_loc:
        clean_loc = clean_loc.split(",")[0].strip()

    return clean_loc if clean_loc else "France"


def get_optimal_limit(requested_limit: int, source_name: str) -> int:
    """
    Augmente la taille des pages de résultats demandées à chaque API.
    Passe de limit=10 à limit=50 ou 100 pour maximiser le volume.
    """
    # Toujours demander au moins 50 résultats
    optimal = max(requested_limit, 50)

    # Certaines APIs supportent des limites plus élevées
    if source_name in ["France Travail", "Adzuna", "Enhanced"]:
        optimal = max(optimal, 100)

    return optimal


# =============================================================================
# 4. 🔀 PARALLÉLISME ET STRATÉGIE DE RETRY AVEC BACKOFF EXPONENTIEL
# =============================================================================

async def execute_with_retry_backoff(
    coro_factory: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    retryable_status_codes: Optional[List[int]] = None,
    source_name: str = "unknown"
) -> Optional[Any]:
    """
    Exécute une coroutine avec retry et backoff exponentiel.

    Args:
        coro_factory: Fonction asynchrone qui retourne la coroutine à exécuter
        max_retries: Nombre maximum de tentatives
        base_delay: Délai de base en secondes
        max_delay: Délai maximum en secondes
        backoff_factor: Facteur multiplicatif du backoff
        retryable_status_codes: Codes HTTP qui déclenchent un retry
        source_name: Nom de la source pour les logs

    Returns:
        Résultat de la coroutine ou None
    """
    if retryable_status_codes is None:
        retryable_status_codes = [429, 503, 502, 500, 403, 408]

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[RETRY:{source_name}] Attempt {attempt}/{max_retries}")
            result = await coro_factory()

            # Succès si on a un résultat non vide
            if result is not None:
                if isinstance(result, list) and len(result) > 0:
                    logger.info(f"[RETRY:{source_name}] ✅ Success on attempt {attempt}: {len(result)} items")
                    return result
                elif not isinstance(result, list):
                    logger.info(f"[RETRY:{source_name}] ✅ Success on attempt {attempt}")
                    return result
                else:
                    logger.warning(f"[RETRY:{source_name}] Empty result on attempt {attempt}")
            else:
                logger.warning(f"[RETRY:{source_name}] None result on attempt {attempt}")

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # Vérifier si l'erreur est retryable
            is_retryable = any(str(code) in error_msg for code in retryable_status_codes)
            is_retryable = is_retryable or any(kw in error_msg for kw in ["timeout", "connection", "reset", "refused"])

            if not is_retryable and attempt == 1:
                logger.error(f"[RETRY:{source_name}] Non-retryable error: {e}")
                return None

            logger.warning(f"[RETRY:{source_name}] Error on attempt {attempt}: {e}")

        # Backoff exponentiel avec jitter
        if attempt < max_retries:
            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
            delay += random.uniform(0, delay * 0.1)  # Jitter
            logger.info(f"[RETRY:{source_name}] Waiting {delay:.2f}s before retry...")
            await asyncio.sleep(delay)

    logger.error(f"[RETRY:{source_name}] ❌ All {max_retries} attempts failed. Last error: {last_error}")
    return None


async def search_with_query_relaxation(
    search_fn: Callable[[str, str, int], Any],
    query: str,
    location: str,
    limit: int,
    source_name: str,
    max_variations: int = 3
) -> List[dict]:
    """
    Exécute une recherche avec relâchement automatique des requêtes.
    Si la recherche exacte renvoie 0 résultat, réessaie avec des variantes plus larges.

    Args:
        search_fn: Fonction de recherche asynchrone (query, location, limit) -> List[dict]
        query: Requête originale
        location: Localisation
        limit: Nombre maximum de résultats
        source_name: Nom de la source pour les logs
        max_variations: Nombre maximum de variations à essayer

    Returns:
        Liste agrégée et dédupliquée des résultats
    """
    # Générer les variantes de requête
    relaxed_queries = generate_relaxed_queries(query, max_variations=max_variations)

    all_results: List[dict] = []
    seen_keys: Set[tuple] = set()

    for i, relaxed_query in enumerate(relaxed_queries):
        logger.info(f"[RELAX:{source_name}] Trying variation {i + 1}/{len(relaxed_queries)}: '{relaxed_query}'")

        try:
            # Ajouter un jitter entre les tentatives
            if i > 0:
                jitter = get_jitter_delay(0.3, 1.0)
                await asyncio.sleep(jitter)

            results = await search_fn(relaxed_query, location, limit)

            if results and len(results) > 0:
                logger.info(f"[RELAX:{source_name}] ✅ Variation '{relaxed_query}' returned {len(results)} results")

                # Déduplication
                for job in results:
                    key = _get_dedup_key(job)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append(job)

                # Si on a assez de résultats, on s'arrête
                if len(all_results) >= limit:
                    logger.info(f"[RELAX:{source_name}] Reached limit of {limit} results, stopping")
                    break
            else:
                logger.warning(f"[RELAX:{source_name}] Variation '{relaxed_query}' returned 0 results")

        except Exception as e:
            logger.error(f"[RELAX:{source_name}] Error with variation '{relaxed_query}': {e}")
            continue

    logger.info(f"[RELAX:{source_name}] Total unique results after relaxation: {len(all_results)}")
    return all_results[:limit]


# =============================================================================
# 5. 🧹 NORMALISATION & DÉDUPLICATION
# =============================================================================

def _get_dedup_key(job: dict) -> tuple:
    """
    Génère une clé de déduplication intelligente (Titre + Entreprise + Ville).
    Normalise les champs pour une comparaison robuste.
    """
    title = str(job.get("titre", job.get("title", ""))).strip().lower()
    company = str(job.get("entreprise", job.get("company", ""))).strip().lower()
    location = str(job.get("location", "")).strip().lower()

    # Normaliser les espaces
    title = re.sub(r'\s+', ' ', title)
    company = re.sub(r'\s+', ' ', company)
    location = re.sub(r'\s+', ' ', location)

    # Supprimer les suffixes communs
    title = re.sub(r'\s*\(h/f\)\s*|\s*h/f\s*|\s*f/h\s*', '', title, flags=re.IGNORECASE)

    return (title, company, location)


def deduplicate_jobs(jobs: List[dict]) -> List[dict]:
    """
    Déduplication intelligente par Titre + Entreprise + Ville.
    """
    seen_keys: Set[tuple] = set()
    deduped: List[dict] = []

    for job in jobs:
        key = _get_dedup_key(job)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(job)

    removed = len(jobs) - len(deduped)
    if removed > 0:
        logger.info(f"[DEDUP] Removed {removed} duplicates from {len(jobs)} jobs ({len(deduped)} unique)")

    return deduped


def normalize_job_fields(job: dict) -> dict:
    """
    Harmonise le format de sortie de chaque scraper.
    Garantit que tous les champs requis sont présents.
    PRÉSERVE les champs AI (pertinence_ai, match_score, ai_scored, match_reason).
    """
    normalized = {
        "titre": str(job.get("titre", job.get("title", ""))).strip(),
        "entreprise": str(job.get("entreprise", job.get("company", "Non précisé"))).strip(),
        "lien": str(job.get("lien", job.get("link", job.get("url", "#")))).strip(),
        "location": str(job.get("location", "")).strip(),
        "date": str(job.get("date", job.get("date_posted", ""))).strip()[:10],
        "source": str(job.get("source", "Inconnue")).strip(),
        "description": str(job.get("description", ""))[:2000].strip(),
        "contrat": str(job.get("contrat", job.get("contract_type", ""))).strip(),
    }

    # Compétences (optionnel)
    if "competences" in job:
        normalized["competences"] = job["competences"]
    elif "skills" in job:
        normalized["competences"] = job["skills"]

    # Salaire (optionnel)
    if "salaire_min" in job:
        normalized["salaire_min"] = job["salaire_min"]
    if "salaire_max" in job:
        normalized["salaire_max"] = job["salaire_max"]

    # ⚠️ PRÉSERVER les champs AI (critique pour les scores)
    if "pertinence_ai" in job:
        normalized["pertinence_ai"] = job["pertinence_ai"]
    if "match_score" in job:
        normalized["match_score"] = job["match_score"]
    if "ai_scored" in job:
        normalized["ai_scored"] = job["ai_scored"]
    if "match_reason" in job:
        normalized["match_reason"] = job["match_reason"]

    return normalized


def normalize_and_deduplicate(jobs: List[dict]) -> List[dict]:
    """
    Normalise et déduplique une liste d'offres d'emploi.
    """
    # Normaliser chaque job
    normalized = [normalize_job_fields(job) for job in jobs]

    # Dédupliquer
    deduped = deduplicate_jobs(normalized)

    return deduped