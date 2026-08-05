import re
from typing import Optional

logger = __import__("logging").getLogger(__name__)

# Freelance-specific sources that return missions (not candidates)
FREELANCE_SOURCES = ["Free-Work", "LinkedIn", "Enhanced", "JobSpy"]

# ─── Freelance Qualification Rules (STRICT) ─────────────────────────────────

# Mots-clés de REJET IMMÉDIAT (Anti-Salariat) - dans le TITRE ou TYPE DE CONTRAT
SALARIED_CONTRACT_KEYWORDS = [
    "cdi", "cdd", "contrat pro", "alternance", "apprentissage", "stage", "intérim", "interim",
    "contrat à durée indéterminée", "contrat à durée déterminée",
]

# Phrases d'exclusion explicites (n'importe où dans le texte)
EXCLUSION_PHRASES = [
    "pas de freelance", "no freelancers", "freelances s'abstenir",
    "uniquement en cdi", "cabinet de recrutement recherche pour son client en cdi",
    "non à la sous-traitance", "pas de prestation",
]

# Mots-clés POSITIFS FORTS (indiquent une offre freelance/prestation EXPLICITE)
# Ces mots doivent être dans le TITRE, TYPE DE CONTRAT, ou SALAIRE (pas juste la description)
FREELANCE_EXPLICIT_KEYWORDS = [
    "freelance", "indépendant", "independant", "prestation", "contractor",
    "sous-traitance", "sous traitance", "régie", "regie", "forfait",
    "portage", "portage salarial", "facturation b2b", "contrat de prestation",
    "mission b2b", "prestation de service",
    "consultant indépendant", "consultant freelance",
    "auto-entrepreneur", "auto entrepreneur", "micro-entreprise",
    "eurl", "sasu", "sarl", "profession libérale",
    "mission freelance", "mission prestation",
]

# Regex pour détecter un TJM (ex: "500€/j", "TJM à négocier", "400-450€/jour")
TJM_REGEX = re.compile(
    r'(tjm|taux\s*journalier|tarif\s*journalier|€\s*/\s*j|€\s*/\s*jour|euros\s*/\s*jour|euros\s*/\s*j|\d+\s*€\s*/\s*j|\d+\s*€\s*/\s*jour|\d+\s*-\s*\d+\s*€\s*/\s*j)',
    re.IGNORECASE
)

# Regex pour détecter un salaire annuel brut (à REJETER)
SALARY_ANNUAL_REGEX = re.compile(
    r'(\d+\s*k\s*€\s*/?\s*an|\d+\s*000\s*€\s*/?\s*an|brut\s*/\s*an|brut\s*annuel|\d+\s*k€|\d+\s*k\s*euros)',
    re.IGNORECASE
)

# Regex pour détecter "ou freelance" ou "ou prestation" (statut mixte)
MIXTE_REGEX = re.compile(
    r'(cdi\s+ou\s+freelance|cdd\s+ou\s+freelance|ou\s+freelance|ou\s+en\s+freelance|ou\s+prestation|cdi\s+ou\s+prestation|ouvert\s+en\s+cdi\s+ou\s+freelance|ouvert\s+aux\s+deux\s+statuts)',
    re.IGNORECASE
)


def is_freelance_offer(job: dict) -> bool:
    """Détermine si une offre est une offre freelance/prestation valide.
    
    RÈGLES STRICTES - Par défaut: REJET (sauf preuve explicite de freelance)
    
    1. REJET IMMÉDIAT si phrases d'exclusion explicites
    2. REJET si CDI/CDD/Alternance/Stage dans titre ou contrat (sauf "ou freelance")
    3. REJET si salaire annuel brut sans TJM
    4. CONSERVATION uniquement si preuve EXPLICITE de freelance:
       - Type de contrat: "Freelance", "Indépendant", "Prestation", etc.
       - TJM ou tarif horaire détecté
       - Modalité de facturation B2B, portage salarial
    5. Doute absolu: REJET par sécurité
    """
    title = (job.get("title") or job.get("titre") or "").lower().strip()
    description = (job.get("description") or job.get("desc") or job.get("resume") or "").lower().strip()
    contract_type = (job.get("contract_type") or job.get("contract") or job.get("type_contrat") or "").lower().strip()
    salary = (job.get("salary") or job.get("salaire") or "").lower().strip()
    
    # Texte court pour vérifications rapides (titre + contrat + salaire)
    short_text = f"{title} {contract_type} {salary}"
    # Texte complet pour vérifications approfondies
    full_text = f"{title} {description} {contract_type} {salary}"
    
    # ─── ÉTAPE 1: REJET IMMÉDIAT - Phrases d'exclusion explicites ───
    for phrase in EXCLUSION_PHRASES:
        if phrase in full_text:
            return False
    
    # ─── ÉTAPE 2: REJET - Contrats salariés dans le TITRE ou TYPE DE CONTRAT ───
    # Vérifier si le titre ou le type de contrat contient CDI/CDD/etc.
    has_salaried_contract = False
    for kw in SALARIED_CONTRACT_KEYWORDS:
        # Vérifier dans le titre (mot entier, pas juste substring)
        title_words = title.split()
        if kw in title_words or kw in contract_type:
            has_salaried_contract = True
            break
        # Vérifier aussi "en CDI", "en CDD" dans le titre
        if f"en {kw}" in title or f"en {kw}" in contract_type:
            has_salaried_contract = True
            break
        # Vérifier "poste en CDI", "contrat CDI" dans le titre
        if f"contrat {kw}" in title or f"poste {kw}" in title:
            has_salaried_contract = True
            break
    
    # Si contrat salarié détecté, vérifier si "ou freelance" est mentionné
    if has_salaried_contract:
        if MIXTE_REGEX.search(full_text):
            # Statut mixte: CONSERVER avec flag
            job["freelance_status"] = "mixte"
            return True
        # Sinon: REJETER
        return False
    
    # ─── ÉTAPE 3: REJET - Salaire annuel brut sans TJM ───
    if SALARY_ANNUAL_REGEX.search(short_text) and not TJM_REGEX.search(full_text):
        # Salaire annuel détecté sans TJM → REJETER
        return False
    
    # ─── ÉTAPE 4: VÉRIFICATION POSITIVE - Preuve EXPLICITE de freelance ───
    # On vérifie d'abord dans le texte court (titre + contrat + salaire)
    has_positive = False
    
    # 4a. Mots-clés explicites dans le titre, type de contrat ou salaire
    for kw in FREELANCE_EXPLICIT_KEYWORDS:
        if kw in short_text:
            has_positive = True
            break
    
    # 4b. TJM ou tarif horaire détecté (regex) dans le texte court
    if not has_positive and TJM_REGEX.search(short_text):
        has_positive = True
    
    # 4c. Si pas trouvé dans le texte court, vérifier dans la description
    # MAIS seulement si le mot "freelance" n'est pas dans un contexte de prérequis
    if not has_positive:
        for kw in FREELANCE_EXPLICIT_KEYWORDS:
            if kw in description:
                # Vérifier que ce n'est pas "expérience en freelance appréciée"
                # ou "profil freelance" dans les prérequis
                bad_contexts = [
                    "expérience en freelance appréciée",
                    "experience en freelance appreciée",
                    "expérience en freelance souhaitée",
                    "profil freelance",
                    "background freelance",
                    "passé en freelance",
                    "ayant travaillé en freelance",
                ]
                is_bad_context = False
                for bad_ctx in bad_contexts:
                    if bad_ctx in description:
                        is_bad_context = True
                        break
                
                if not is_bad_context:
                    has_positive = True
                    break
    
    # 4d. TJM dans la description
    if not has_positive and TJM_REGEX.search(description):
        has_positive = True
    
    # ─── ÉTAPE 5: Doute absolu - REJET par sécurité ───
    if not has_positive:
        return False
    
    return True


class FreelanceSearcher:
    """Agent-specific searcher for freelance missions.
    
    Uses the SAME 6 sources as Job and Recruiter agents.
    The freelance filtering is done post-search via apply_filters().
    """

    def __init__(self):
        self.sources = FREELANCE_SOURCES

    def get_sources(self, selected_sources: Optional[list] = None) -> list:
        """Return the same 6 sources as other agents."""
        if selected_sources:
            # Filter to only known sources
            known_sources = set(FREELANCE_SOURCES)
            return [s for s in selected_sources if s in known_sources]
        return self.sources

    def build_search_query(self, query: str, location: str, filters: dict) -> str:
        """Build search query - same as other agents."""
        parts = [query]
        if location:
            parts.append(location)
        return " ".join(parts)

    def apply_filters(self, jobs: list, filters: dict) -> list:
        """Apply freelance-specific filters.
        
        1. FIRST: Filter to keep ONLY freelance/prestation offers (is_freelance_offer) - if strict_mode
        2. THEN: Apply user filters (TJM, mission type, duration, remote)
        """
        # Check if strict freelance filtering is enabled (default: False for broader results)
        strict_mode = filters.get("strictFreelanceFilter", False)
        
        if strict_mode:
            # ─── ÉTAPE 1: Filtrer pour ne garder QUE les offres freelance ───
            freelance_jobs = []
            rejected_count = 0
            for job in jobs:
                if is_freelance_offer(job):
                    freelance_jobs.append(job)
                else:
                    rejected_count += 1
            
            logger.info(f"[FREELANCE_FILTER] Total jobs: {len(jobs)}, Freelance kept: {len(freelance_jobs)}, Rejected: {rejected_count}")
            filtered = freelance_jobs
        else:
            # Non-strict mode: keep all jobs, just log
            logger.info(f"[FREELANCE_FILTER] Non-strict mode: keeping all {len(jobs)} jobs")
            filtered = jobs
        
        # ─── ÉTAPE 2: Appliquer les filtres utilisateur ───
        # Filtre TJM min
        if filters.get("tjmMin"):
            try:
                tjm_min = int(filters["tjmMin"])
                filtered = [j for j in filtered if (j.get("tjm") or 0) >= tjm_min]
            except (ValueError, TypeError):
                pass
        
        # Filtre TJM max
        if filters.get("tjmMax"):
            try:
                tjm_max = int(filters["tjmMax"])
                filtered = [j for j in filtered if (j.get("tjm") or 0) <= tjm_max]
            except (ValueError, TypeError):
                pass
        
        # Filtre type de mission
        if filters.get("missionType"):
            mt = filters["missionType"].lower()
            filtered = [j for j in filtered if mt in (j.get("title") or "").lower() or mt in (j.get("description") or "").lower()]
        
        # Filtre durée
        if filters.get("duration"):
            dur = filters["duration"]
            filtered = [j for j in filtered if dur.lower() in (j.get("description") or "").lower()]
        
        # Filtre remote
        if filters.get("remote") and filters["remote"] != "":
            remote_val = filters["remote"].lower()
            filtered = [j for j in filtered if remote_val in (j.get("location") or "").lower() or remote_val in (j.get("description") or "").lower()]
        
        logger.info(f"[FREELANCE_FILTER] After user filters: {len(filtered)} jobs")
        return filtered

    def score_mission(self, cv_data: dict, job: dict) -> float:
        from app.services.scorer import get_scorer
        scorer = get_scorer()
        return scorer.score_single(cv_data, job)