from typing import Optional

logger = __import__("logging").getLogger(__name__)

JOB_SOURCES = ["LinkedIn", "France Travail", "Google Jobs", "Adzuna", "Enhanced", "JobSpy"]


class JobSearcher:
    """Agent-specific searcher for job seekers."""

    def __init__(self):
        self.sources = JOB_SOURCES

    def get_sources(self, selected_sources: Optional[list] = None) -> list:
        if selected_sources:
            return [s for s in selected_sources if s in self.sources]
        return self.sources

    def build_search_query(self, query: str, location: str, filters: dict) -> str:
        parts = [query]
        if location:
            parts.append(location)
        return " ".join(parts)

    def apply_filters(self, jobs: list, filters: dict) -> list:
        filtered = jobs
        if filters.get("contract"):
            contract = filters["contract"].lower()
            filtered = [j for j in filtered if contract in (j.get("contract_type") or "").lower() or contract in (j.get("description") or "").lower()]
        if filters.get("remote") is True:
            filtered = [j for j in filtered if "remote" in (j.get("location") or "").lower() or "télétravail" in (j.get("description") or "").lower()]
        if filters.get("location"):
            loc = filters["location"].lower()
            filtered = [j for j in filtered if loc in (j.get("location") or "").lower()]
        return filtered

    def score_job(self, cv_data: dict, job: dict) -> float:
        from app.services.scorer import get_scorer
        scorer = get_scorer()
        return scorer.score_single(cv_data, job)