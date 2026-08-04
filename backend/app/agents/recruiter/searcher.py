from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

FREELANCE_SOURCES = ["Malt", "LinkedIn", "Free-Work"]
CDD_SOURCES = ["LinkedIn", "France Travail", "GitHub", "StackOverflow"]


class WorkerSearcher:
    """Agent-specific searcher for the Find My Worker agent.

    Finds candidates (not job offers) based on a job posting (fiche de poste).
    Sources are grouped by contract type: FREELANCE or CDD/CDI.
    """

    def __init__(self):
        self.freelance_sources = FREELANCE_SOURCES
        self.cdd_sources = CDD_SOURCES

    def get_sources(self, contract_type: str = "FREELANCE", selected_sources: Optional[list] = None) -> list:
        """Return sources based on the desired contract type."""
        source_map = {
            "FREELANCE": self.freelance_sources,
            "CDD": self.cdd_sources,
            "CDI": self.cdd_sources,
            "MIXTE": self.freelance_sources + self.cdd_sources,
        }
        sources = source_map.get(contract_type.upper(), self.freelance_sources)

        if selected_sources:
            return [s for s in selected_sources if s in sources]
        return sources

    def get_contract_groups(self) -> dict:
        """Return the source groups by contract type."""
        return {
            "FREELANCE": self.freelance_sources,
            "CDD/CDI": self.cdd_sources,
        }

    def build_search_query(self, query: str, location: str, filters: dict) -> str:
        """Build a search query from the job posting requirements."""
        parts = [query]
        if filters.get("skills"):
            parts.append(filters["skills"])
        if location:
            parts.append(location)
        return " ".join(parts)

    def apply_filters(self, candidates: list, filters: dict) -> list:
        """Apply worker-specific filtering rules to candidates."""
        filtered = candidates

        if filters.get("contract"):
            contract = filters["contract"].lower()
            filtered = [
                c for c in filtered
                if contract in (c.get("target_contract") or "").lower()
                or contract in (c.get("headline_title") or "").lower()
            ]

        if filters.get("skills"):
            skills = [s.lower() for s in filters["skills"]]
            filtered = [
                c for c in filtered
                if any(s in (c.get("headline_title") or "").lower()
                       or any(s in (sk or "").lower() for sk in c.get("skills", []))
                       for s in skills)
            ]

        if filters.get("location"):
            loc = filters["location"].lower()
            filtered = [
                c for c in filtered
                if loc in (c.get("location") or "").lower()
            ]

        if filters.get("availability"):
            avail = filters["availability"].lower()
            filtered = [
                c for c in filtered
                if avail in (c.get("availability") or "").lower()
            ]

        if filters.get("targetContract"):
            tc = filters["targetContract"].upper()
            filtered = [
                c for c in filtered
                if tc == (c.get("target_contract") or "").upper()
            ]

        return filtered

    def validate_candidate(self, candidate: dict) -> bool:
        """Validate a candidate against the worker agent's rules."""
        headline = (candidate.get("headline_title") or "").lower()
        skills = [s.lower() for s in (candidate.get("skills") or [])]
        profile_text = f"{headline} {' '.join(skills)}".lower()

        company_indicators = [
            "cabinet de recrutement", "agence de recrutement", "societe de recrutement",
            "consulting firm", "recruitment agency", "talent acquisition",
        ]
        for indicator in company_indicators:
            if indicator in profile_text:
                return False

        freelance_indicators = [
            "freelance", "indépendant", "consultant indépendant",
            "portage salarial", "tjm", "facturation b2b", "b2b",
            "micro-entreprise", "auto-entrepreneur", "freelance it",
        ]
        is_freelance = any(ind in profile_text for ind in freelance_indicators)

        cdd_indicators = [
            "cdd", "contrat à durée déterminée", "disponible immédiatement",
            "open to work", "open for business", "recherche cdd",
            "remplacement", "mission temporaire", "intérim",
            "disponible sous", "disponible dès",
        ]
        is_cdd = any(ind in profile_text for ind in cdd_indicators)

        cdi_indicators = [
            "cdi chez", "employé chez", "staffed by",
            "permanent position", "full-time cdi",
        ]
        is_stable_cdi = any(ind in profile_text for ind in cdi_indicators)
        has_active_search = is_freelance or is_cdd or "open to work" in profile_text or "open for business" in profile_text

        if is_stable_cdi and not has_active_search:
            return False

        return is_freelance or is_cdd

    def normalize_candidate(self, raw_data: dict, source_platform: str) -> dict:
        """Normalize raw candidate data into the standard worker format."""
        return {
            "worker_id": raw_data.get("worker_id") or raw_data.get("id") or "",
            "full_name": raw_data.get("full_name") or raw_data.get("name") or "",
            "headline_title": raw_data.get("headline_title") or raw_data.get("title") or "",
            "target_contract": raw_data.get("target_contract") or "MIXTE",
            "skills": raw_data.get("skills") or [],
            "location": raw_data.get("location") or raw_data.get("city") or "",
            "tjm_or_rate": raw_data.get("tjm_or_rate") or raw_data.get("rate") or None,
            "availability": raw_data.get("availability") or raw_data.get("disponibilite") or "",
            "source_platform": source_platform,
            "profile_url": raw_data.get("profile_url") or raw_data.get("url") or "",
        }

    def score_candidate(self, job_posting: dict, candidate: dict) -> float:
        """Score a candidate against a job posting."""
        from app.services.scorer import get_scorer
        scorer = get_scorer()
        return scorer.score_single(job_posting, candidate)