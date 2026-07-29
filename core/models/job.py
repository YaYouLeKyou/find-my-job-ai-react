"""
Job Model - Core Domain Model
Part of Clean Architecture - Inner Layer (Domain)
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Job(BaseModel):
    """Domain model representing a job offer"""

    id: str
    title: str
    company: str
    location: str
    source: str
    description: str
    posted_date: Optional[datetime] = None
    salary: Optional[float] = None
    contract_type: Optional[str] = None
    url: Optional[str] = None
    pertinence_score: Optional[float] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "linkedin_12345",
                "title": "Développeur Full-Stack",
                "company": "TechCorp",
                "location": "Paris, France",
                "source": "LinkedIn",
                "description": "Recherche développeur Full-Stack avec expérience React et Node.js",
                "posted_date": "2023-01-15T10:30:00",
                "salary": 50000,
                "contract_type": "CDI",
                "url": "https://linkedin.com/jobs/12345",
                "pertinence_score": 0.95
            }
        }

    def is_high_quality(self) -> bool:
        """Business rule: Determine if this is a high quality job"""
        # High quality if:
        # - Has salary information
        # - Not an internship/junior position
        # - Has reasonable salary
        if not self.salary:
            return False

        if self.title and "junior" in self.title.lower():
            return False

        if self.title and "stage" in self.title.lower():
            return False

        return self.salary >= 35000  # Minimum threshold for quality