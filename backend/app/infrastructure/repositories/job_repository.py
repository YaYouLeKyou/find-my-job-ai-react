"""
Job Repository Implementation - Infrastructure Layer
Implements the JobRepositoryInterface with actual data access
"""

from typing import List
from backend.app.core.models.job import Job
from backend.app.core.exceptions import JobSearchError, APIError
from backend.app.interfaces.repositories.job_repository import JobRepositoryInterface
from backend.app.scrapers.api_sources import (
    get_france_travail_source, get_adzuna_source,
    get_google_jobs_source, get_jooble_source,
    get_apify_source
)
from backend.app.scrapers.web_sources import (
    scrape_linkedin, scrape_indeed,
    scrape_monster, scrape_hellowork,
    scrape_google_jobs, scrape_jobspy,
    scrape_enhanced
)
import asyncio
import logging

logger = logging.getLogger(__name__)

class JobRepository(JobRepositoryInterface):
    """Concrete implementation of JobRepositoryInterface"""

    def __init__(self):
        """Initialize the repository with source mappings"""
        self.source_map = {
            'France Travail': self._get_france_travail_source,
            'Adzuna': self._get_adzuna_source,
            'Google Jobs': self._get_google_jobs_source,
            'Jooble': self._get_jooble_source,
            'Apify': self._get_apify_source,
            'LinkedIn': scrape_linkedin,
            'Indeed': scrape_indeed,
            'Monster': scrape_monster,
            'HelloWork': scrape_hellowork,
            'JobSpy': scrape_jobspy,
            'Enhanced': scrape_enhanced,
        }

    async def search_from_sources(self, query: str, location: str, sources: List[str], limit: int = 100) -> List[Job]:
        """
        Search jobs from multiple sources concurrently

        Args:
            query: Search query
            location: Location
            sources: List of source names
            limit: Maximum results per source

        Returns:
            List of Job objects

        Raises:
            JobSearchError: If search fails
        """
        if not sources:
            raise JobSearchError("No sources specified")

        logger.info(f"Searching jobs: query={query!r} location={location!r} sources={sources}")

        # Filter to only available sources
        available_sources = [s for s in sources if s in self.source_map]
        if not available_sources:
            raise JobSearchError(f"No available sources from requested: {sources}")

        # Search from each source concurrently
        search_tasks = []
        for source_name in available_sources:
            try:
                search_func = self.source_map[source_name]
                source = await search_func()
                if source:
                    task = asyncio.create_task(self._search_source(source, source_name, query, location, limit))
                    search_tasks.append(task)
            except Exception as e:
                logger.warning(f"Failed to initialize source {source_name}: {e}")
                continue

        if not search_tasks:
            raise JobSearchError("No sources could be initialized")

        # Execute all searches concurrently
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Process results
        all_jobs = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Source search failed: {result}")
                continue
            if result:
                all_jobs.extend(result)

        logger.info(f"Found {len(all_jobs)} jobs from {len(available_sources)} sources")
        return all_jobs

    async def get_job_details(self, job_id: str) -> Job:
        """Get detailed information about a specific job"""
        # TODO: Implement job details fetching
        raise NotImplementedError("Job details fetching not yet implemented")

    async def get_suggested_jobs(self, cv_data: dict) -> List[Job]:
        """Get jobs suggested based on CV analysis"""
        # TODO: Implement CV-based job suggestions
        raise NotImplementedError("CV-based suggestions not yet implemented")

    async def _search_source(self, source, source_name: str, query: str, location: str, limit: int) -> List[Job]:
        """Search a single source and return results"""
        try:
            logger.info(f"Searching {source_name}: query={query!r} location={location!r}")

            if hasattr(source, 'search_jobs'):
                # API-based source
                jobs = await source.search_jobs(query, location, limit)
            else:
                # Function-based source (web scrapers)
                jobs = await source(query, location, limit)

            logger.info(f"Found {len(jobs)} jobs from {source_name}")
            return [self._map_to_job_model(job, source_name) for job in jobs]

        except Exception as e:
            logger.error(f"Error searching {source_name}: {e}")
            raise APIError(f"Source {source_name} failed: {str(e)}", status_code=500)

    def _map_to_job_model(self, job_data: dict, source: str) -> Job:
        """Map raw job data to Job model"""
        return Job(
            titre=job_data.get('titre', ''),
            entreprise=job_data.get('entreprise', ''),
            lien=job_data.get('lien', ''),
            location=job_data.get('location', ''),
            date=job_data.get('date', ''),
            source=source,
            description=job_data.get('description', ''),
            contrat=job_data.get('contrat', ''),
            competences=job_data.get('competences', []),
            salaire=job_data.get('salaire', ''),
            salaire_min=job_data.get('salaire_min'),
            salaire_max=job_data.get('salaire_max'),
            pertinence_ai=job_data.get('pertinence_ai', 0.5)
        )

    # Source initialization methods
    async def _get_france_travail_source(self):
        return get_france_travail_source()

    async def _get_adzuna_source(self):
        return get_adzuna_source()

    async def _get_google_jobs_source(self):
        return get_google_jobs_source()

    async def _get_jooble_source(self):
        return get_jooble_source()

    async def _get_apify_source(self):
        return get_apify_source()