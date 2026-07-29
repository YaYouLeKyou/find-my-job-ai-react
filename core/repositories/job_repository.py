"""
Job Repository Interface - Core Layer
Part of Clean Architecture - Ports (Interfaces)
"""
from abc import ABC, abstractmethod
from typing import List
from core.models.job import Job

class JobRepositoryInterface(ABC):
    """Abstract base class for job repositories"""

    @abstractmethod
    async def search_from_sources(self, query: str, location: str, sources: List[str]) -> List[Job]:
        """Search jobs from multiple sources"""

    @abstractmethod
    async def get_job_details(self, job_id: str) -> Job:
        """Get detailed information about a specific job"""

    @abstractmethod
    async def get_suggested_jobs(self, cv_data: dict) -> List[Job]:
        """Get jobs suggested based on CV analysis"""

    @abstractmethod
    async def save_job(self, job: Job) -> Job:
        """Save a job to favorites/shortlist"""