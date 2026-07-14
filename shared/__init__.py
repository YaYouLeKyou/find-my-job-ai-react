# FindMyJobAI - Package de code partagé
# Ce package contient la logique métier commune à main.py (Streamlit) et backend/api.py (FastAPI)

from .ai import (
    is_ollama_online,
    get_ollama_version,
    call_local_llama,
    call_ai_provider,
    analyze_cv,
    generate_cover_letter,
    rank_jobs_with_ai,
)

from .jobs import (
    clean_html,
    scrape_france_travail_jobs,
    get_france_travail_token,
    get_france_travail_jobs_api,
    chercher_offres_jobspy,
    get_adzuna_jobs,
    get_serpapi_jobs,
    get_jooble_jobs,
    get_apify_jobs,
)

from .utils import (
    extract_text_from_pdf,
    reverse_geocoding,
    clean_job_title,
    get_geolocation,
    generate_job_search_links,
)

__all__ = [
    # ai
    "is_ollama_online", "get_ollama_version", "call_local_llama",
    "call_ai_provider", "analyze_cv", "generate_cover_letter", "rank_jobs_with_ai",
    # jobs
    "clean_html", "scrape_france_travail_jobs", "get_france_travail_token",
    "get_france_travail_jobs_api", "chercher_offres_jobspy",
    "get_adzuna_jobs", "get_serpapi_jobs", "get_jooble_jobs", "get_apify_jobs",
    # utils
    "extract_text_from_pdf", "reverse_geocoding", "clean_job_title",
    "get_geolocation", "generate_job_search_links",
]