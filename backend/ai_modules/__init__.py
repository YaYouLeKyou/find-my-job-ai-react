# AI/ML modules for job scraping enhancement
# This package contains modules for:
# - Data extraction (NER, skill extraction, salary detection)
# - Deduplication (semantic similarity with Sentence-BERT)
# - Enrichment (salary estimation, auto-tagging)
# - Advanced ranking (ML-based scoring)

__version__ = "1.0.0"

# Import will be done lazily to avoid loading heavy models at startup
try:
    from .data_extraction import extract_job_data, extract_skills, extract_salary
    from .deduplication import deduplicate_jobs, calculate_similarity
    from .enrichment import enrich_job_data, estimate_salary
    from .ranking import rank_jobs_ml
    AI_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"AI modules not fully available: {e}")
    AI_MODULES_AVAILABLE = False