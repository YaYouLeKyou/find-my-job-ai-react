"""
Search Parameters DTO - Core Layer
Data Transfer Object for search operations
"""
from pydantic import BaseModel
from typing import List, Optional

class SearchParams(BaseModel):
    """DTO for job search parameters"""

    query: str
    location: str
    sources: List[str]
    num_ads: int = 100
    contract: str = "CDI"
    remote: bool = False
    cv_data: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Développeur Python",
                "location": "Paris, France",
                "sources": ["LinkedIn", "France Travail", "Google Jobs"],
                "num_ads": 50,
                "contract": "CDI",
                "remote": False,
                "cv_data": {
                    "skills": ["Python", "Django", "SQL"],
                    "experience": 5,
                    "keywords": ["backend", "API"]
                }
            }
        }

    def validate(self):
        """Validate the search parameters"""
        if len(self.query.strip()) < 3:
            raise ValueError("Query must be at least 3 characters")

        if not self.sources:
            raise ValueError("At least one source must be selected")

        if len(self.sources) > 10:
            raise ValueError("Maximum 10 sources allowed")

        if self.num_ads < 1 or self.num_ads > 500:
            raise ValueError("num_ads must be between 1 and 500")