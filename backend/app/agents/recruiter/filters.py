from typing import Dict, Any, List

logger = __import__("logging").getLogger(__name__)


def validate_recruiter_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize recruiter/worker-specific filters."""
    validated = {}

    if "contract" in filters:
        valid_contracts = ["CDI", "CDD", "Stage", "Alternance", "Intérim", "Temps partiel"]
        validated["contract"] = (
            filters["contract"]
            if filters["contract"] in valid_contracts
            else "CDD"
        )

    if "experience" in filters:
        valid_experiences = [
            "Débutant", "Junior (1-3 ans)", "Confirmé (3-5 ans)",
            "Senior (5-10 ans)", "Expert (10+ ans)",
        ]
        validated["experience"] = (
            filters["experience"]
            if filters["experience"] in valid_experiences
            else ""
        )

    if "location" in filters:
        validated["location"] = str(filters["location"]).strip()

    if "remote" in filters:
        validated["remote"] = bool(filters["remote"])

    if "salaryMin" in filters:
        try:
            validated["salaryMin"] = max(0, float(filters["salaryMin"]))
        except (ValueError, TypeError):
            validated["salaryMin"] = 0

    if "salaryMax" in filters:
        try:
            validated["salaryMax"] = max(0, float(filters["salaryMax"]))
        except (ValueError, TypeError):
            validated["salaryMax"] = 0

    if "skills" in filters:
        if isinstance(filters["skills"], list):
            validated["skills"] = [str(s).strip() for s in filters["skills"] if str(s).strip()]
        elif isinstance(filters["skills"], str):
            validated["skills"] = [s.strip() for s in filters["skills"].split(",") if s.strip()]
        else:
            validated["skills"] = []

    if "numAds" in filters:
        try:
            validated["numAds"] = max(1, min(50, int(filters["numAds"])))
        except (ValueError, TypeError):
            validated["numAds"] = 10

    # Worker-specific filters
    if "targetContract" in filters:
        valid_targets = ["FREELANCE", "CDD", "MIXTE"]
        validated["targetContract"] = (
            filters["targetContract"]
            if filters["targetContract"].upper() in valid_targets
            else "MIXTE"
        )

    if "availability" in filters:
        validated["availability"] = str(filters["availability"]).strip()

    return validated