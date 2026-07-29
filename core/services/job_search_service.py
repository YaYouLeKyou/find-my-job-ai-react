"""
Job Search Service - Core Layer (Use Cases)
Part of Clean Architecture - Business Logic
"""
from typing import List, Optional
from core.models.job import Job
from core.repositories.job_repository import JobRepositoryInterface
from core.exceptions.job_search_error import JobSearchError

class JobSearchService:
    """Business logic service for job search operations"""

    def __init__(self, repository: JobRepositoryInterface):
        self.repository = repository

    async def search_jobs(
        self,
        query: str,
        location: str,
        sources: List[str],
        cv_data: Optional[dict] = None
    ) -> List[Job]:
        """
        Search jobs with business logic validation and processing

        Args:
            query: Search query
            location: Location filter
            sources: List of sources to search
            cv_data: Optional CV data for pertinence scoring

        Returns:
            List of Job objects sorted by pertinence

        Raises:
            JobSearchError: If validation fails or search error occurs
        """
        self._validate_search_params(query, sources)

        try:
            # Fetch jobs from repository
            jobs = await self.repository.search_from_sources(query, location, sources)

            # Apply business rules
            filtered_jobs = self._filter_low_quality_jobs(jobs)

            # Calculate pertinence scores if CV data provided
            if cv_data:
                scored_jobs = self._calculate_pertinence_scores(filtered_jobs, cv_data)
                return sorted(scored_jobs, key=lambda j: j.pertinence_score or 0, reverse=True)

            return filtered_jobs

        except Exception as e:
            raise JobSearchError(f"Job search failed: {str(e)}") from e

    def _validate_search_params(self, query: str, sources: List[str]):
        """Validate business rules for search parameters"""
        if not query or len(query.strip()) < 3:
            raise JobSearchError("Query must be at least 3 characters")

        if not sources:
            raise JobSearchError("At least one source must be selected")

        if len(sources) > 10:
            raise JobSearchError("Too many sources selected (max 10)")

    def _filter_low_quality_jobs(self, jobs: List[Job]) -> List[Job]:
        """Apply business filters to exclude low-quality jobs"""
        return [
            job for job in jobs
            if job.is_high_quality()  # Uses the domain model's business rule
        ]

    def _calculate_pertinence_scores(self, jobs: List[Job], cv_data: dict) -> List[Job]:
        """Calculate pertinence scores based on CV data"""
        cv_skills = set(skill.lower() for skill in cv_data.get('skills', []))
        cv_keywords = set(word.lower() for text in cv_data.get('keywords', [])
                         for word in text.split() if len(word) > 4)

        for job in jobs:
            job_keywords = set(word.lower() for word in f"{job.title} {job.description}".split()
                             if len(word) > 4)

            # Calculate match score based on skill overlap
            matches = cv_skills.intersection(job_keywords) | cv_keywords.intersection(job_keywords)
            job.pertinence_score = min(1.0, 0.3 + len(matches) * 0.1)

        return jobs