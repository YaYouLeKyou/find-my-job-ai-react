from typing import Dict, Any

logger = __import__("logging").getLogger(__name__)


def validate_job_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize job seeker-specific filters."""
    validated = {}

    if "contract" in filters:
        valid_contracts = ["CDI", "CDD", "Alternance", "Stage", "Intérim"]
        validated["contract"] = (
            filters["contract"]
            if filters["contract"] in valid_contracts
            else "CDI"
        )

    if "location" in filters:
        validated["location"] = str(filters["location"]).strip()

    if "remote" in filters:
        validated["remote"] = bool(filters["remote"])

    if "globalSearch" in filters:
        validated["globalSearch"] = bool(filters["globalSearch"])

    if "numAds" in filters:
        try:
            validated["numAds"] = max(1, min(100, int(filters["numAds"])))
        except (ValueError, TypeError):
            validated["numAds"] = 10

    if "sortOption" in filters:
        validated["sortOption"] = str(filters["sortOption"]).strip()

    return validated