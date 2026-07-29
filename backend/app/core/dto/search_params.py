"""
Data Transfer Object for search parameters
"""

from pydantic import BaseModel
from typing import Optional, List

class SearchParams(BaseModel):
    query: str
    location: str = "France"
    sources: List[str] = ["LinkedIn", "France Travail", "Google Jobs"]
    limit: int = 100
    contract: str = "CDI"
    remote: bool = False
    cv_data: Optional[dict] = None
    ranking_engine: str = "Groq / Llama 3.3"

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Développeur Python",
                "location": "Paris, France",
                "sources": ["LinkedIn", "France Travail", "Google Jobs"],
                "limit": 50,
                "contract": "CDI",
                "remote": False,
                "cv_data": {
                    "skills": ["Python", "Django", "React"],
                    "experience": 5
                },
                "ranking_engine": "Groq / Llama 3.3"
            }
        }