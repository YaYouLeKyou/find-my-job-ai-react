"""
Job model representing a job posting
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Job(BaseModel):
    id: Optional[str] = None
    titre: str
    entreprise: str
    lien: str
    location: str
    date: Optional[str] = None
    source: str
    description: str
    contrat: Optional[str] = None
    competences: Optional[List[str]] = None
    salaire: Optional[str] = None
    salaire_min: Optional[float] = None
    salaire_max: Optional[float] = None
    pertinence_ai: Optional[float] = None
    distance_score: Optional[float] = None
    posted_date: Optional[datetime] = None
    contract_type: Optional[str] = None
    remote: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "linkedin_12345",
                "titre": "Développeur Full-Stack",
                "entreprise": "TechCorp",
                "lien": "https://linkedin.com/jobs/12345",
                "location": "Paris, France",
                "date": "2023-01-15",
                "source": "LinkedIn",
                "description": "Recherche développeur Full-Stack avec expérience en React et Python...",
                "contrat": "CDI",
                "competences": ["React", "Python", "Django", "JavaScript"],
                "salaire": "50000-60000",
                "salaire_min": 50000,
                "salaire_max": 60000,
                "pertinence_ai": 0.95,
                "distance_score": 0.8,
                "contract_type": "CDI",
                "remote": False
            }
        }