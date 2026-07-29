"""
Job Search Service - Core business logic for job searching
"""

from typing import List, Optional
from backend.app.core.models.job import Job
from backend.app.core.exceptions import JobSearchError
from backend.app.core.dto.search_params import SearchParams
from backend.app.interfaces.repositories.job_repository import JobRepositoryInterface

class JobSearchService:
    def __init__(self, repository: JobRepositoryInterface):
        self.repository = repository

    async def search_jobs(self, params: SearchParams) -> List[Job]:
        """
        Search jobs with proper business logic separation

        Args:
            params: SearchParams containing query, location, sources, etc.

        Returns:
            List of Job objects

        Raises:
            JobSearchError: If search fails
        """
        self._validate_search_params(params)

        try:
            jobs = await self.repository.search_from_sources(
                query=params.query,
                location=params.location,
                sources=params.sources,
                limit=params.limit
            )

            # Apply business rules
            filtered_jobs = self._filter_low_quality_jobs(jobs)
            scored_jobs = self._calculate_pertinence_scores(filtered_jobs, params.cv_data)

            return sorted(scored_jobs, key=lambda j: j.pertinence_ai or 0, reverse=True)

        except Exception as e:
            raise JobSearchError(f"Job search failed: {str(e)}") from e

    def _validate_search_params(self, params: SearchParams):
        """Validate business rules for search parameters"""
        if not params.query or len(params.query.strip()) < 3:
            raise JobSearchError("Query must be at least 3 characters")

        if not params.sources:
            raise JobSearchError("At least one source must be selected")

        if len(params.sources) > 10:
            raise JobSearchError("Too many sources selected (max 10)")

    def _filter_low_quality_jobs(self, jobs: List[Job]) -> List[Job]:
        """Apply business filters to exclude low-quality jobs"""
        return [
            job for job in jobs
            if not (job.titre and "senior" in job.titre.lower() and (job.salaire_min or 0) < 40000)
        ]

    def _calculate_pertinence_scores(self, jobs: List[Job], cv_data: Optional[dict] = None) -> List[Job]:
        """Calculate pertinence scores based on CV data when available"""
        for job in jobs:
            if cv_data and 'skills' in cv_data:
                # Simple keyword matching - could be enhanced with ML
                job.pertinence_ai = self._calculate_keyword_match_score(job, cv_data)
            else:
                job.pertinence_ai = 0.5  # Default score
        return jobs

    def _calculate_keyword_match_score(self, job: Job, cv_data: dict) -> float:
        """Calculate score based on keyword matching between job and CV"""
        cv_skills = set(skill.lower() for skill in cv_data.get('skills', []))
        job_keywords = set(word.lower() for word in f"{job.titre} {job.description}".split() if len(word) > 4)

        matches = cv_skills.intersection(job_keywords)
        return min(1.0, 0.3 + len(matches) * 0.15)  # Score between 0.3 and 1.0