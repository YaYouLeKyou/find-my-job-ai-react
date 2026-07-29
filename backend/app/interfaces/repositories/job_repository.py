"""
Job Repository Interface - Contract for job data access
"""

from abc import ABC, abstractmethod
from typing import List
from backend.app.core.models.job import Job

class JobRepositoryInterface(ABC):
    @abstractmethod
    async def search_from_sources(self, query: str, location: str, sources: List[str], limit: int = 100) -> List[Job]:
        """Search jobs from multiple sources"""

    @abstractmethod
    async def get_job_details(self, job_id: str) -> Job:
        """Get detailed information about a specific job"""

    @abstractmethod
    async def get_suggested_jobs(self, cv_data: dict) -> List[Job]:
        """Get jobs suggested based on CV analysis"""