from typing import Dict, Any, List

logger = __import__("logging").getLogger(__name__)


def validate_freelance_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize freelance-specific filters."""
    validated = {}

    if "missionType" in filters:
        valid_mission_types = [
            "Développement", "Design", "Conseil", "Rédaction",
            "Marketing", "Data", "DevOps", "Mobile",
        ]
        validated["missionType"] = (
            filters["missionType"]
            if filters["missionType"] in valid_mission_types
            else ""
        )

    if "duration" in filters:
        valid_durations = [
            "Court terme (< 1 mois)",
            "Moyen terme (1-3 mois)",
            "Long terme (> 3 mois)",
            "Récurrent",
        ]
        validated["duration"] = (
            filters["duration"]
            if filters["duration"] in valid_durations
            else ""
        )

    if "remote" in filters:
        validated["remote"] = filters["remote"]

    if "tjmMin" in filters:
        try:
            validated["tjmMin"] = max(0, float(filters["tjmMin"]))
        except (ValueError, TypeError):
            validated["tjmMin"] = 0

    if "tjmMax" in filters:
        try:
            validated["tjmMax"] = max(0, float(filters["tjmMax"]))
        except (ValueError, TypeError):
            validated["tjmMax"] = 0

    if "location" in filters:
        validated["location"] = str(filters["location"]).strip()

    if "numAds" in filters:
        try:
            validated["numAds"] = max(1, min(50, int(filters["numAds"])))
        except (ValueError, TypeError):
            validated["numAds"] = 10

    return validated