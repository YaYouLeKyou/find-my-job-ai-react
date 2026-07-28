"""
AI Scoring Service
Fast job scoring using TF-IDF and Cosine Similarity
Target: < 50ms per job
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class JobScorer:
    """
    Fast job scorer using TF-IDF and cosine similarity.
    Optimized for speed (< 50ms per job).
    """

    DEFAULT_SCORE = 50.0

    def __init__(self):
        """Initialize the scorer with TF-IDF vectorizer."""
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words=None,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self._fitted = False

    def _prepare_text(self, cv_data: Dict, job: Dict) -> Tuple[str, str]:
        """
        Prepare CV and job texts for comparison.

        Args:
            cv_data: CV analysis data
            job: Job dictionary

        Returns:
            Tuple of (cv_text, job_text)
        """
        cv_parts = []
        if cv_data.get('metier'):
            cv_parts.append(str(cv_data['metier']))
        if cv_data.get('mots_cles'):
            cv_parts.append(' '.join(cv_data['mots_cles']))
        if cv_data.get('experience'):
            cv_parts.append(str(cv_data['experience']))
        if cv_data.get('resume'):
            cv_parts.append(str(cv_data['resume']))
        cv_text = ' '.join(cv_parts)

        job_parts = []
        if job.get('title'):
            job_parts.append(str(job['title']))
        if job.get('description'):
            job_parts.append(str(job['description'])[:500])
        if job.get('skills'):
            job_parts.append(' '.join(job['skills']) if isinstance(job['skills'], list) else str(job['skills']))
        job_text = ' '.join(job_parts)

        return cv_text, job_text

    def _ensure_dict(self, data):
        if isinstance(data, str):
            return {"metier": data, "mots_cles": [], "experience": "", "resume": data,
                    "title": data, "description": data, "raw_text": data, "skills": []}
        return data if isinstance(data, dict) else {}

    def score_single(self, cv: dict, job: dict) -> float:
        """
        Score a single job against CV data.

        Args:
            cv: CV analysis data (dict or string)
            job: Job dictionary

        Returns:
            Similarity score (10-100)
        """
        job_dict = self._ensure_dict(job)
        cv_dict = self._ensure_dict(cv)

        job_text = f"{job_dict.get('title', '')} {job_dict.get('description', '')}".strip().lower()

        # Extract CV text using the same logic as _prepare_text
        cv_parts = []
        if cv_dict.get('metier'):
            cv_parts.append(str(cv_dict['metier']))
        if cv_dict.get('mots_cles'):
            cv_parts.append(' '.join(cv_dict['mots_cles']))
        if cv_dict.get('experience'):
            cv_parts.append(str(cv_dict['experience']))
        if cv_dict.get('resume'):
            cv_parts.append(str(cv_dict['resume']))
        cv_text = ' '.join(cv_parts).strip().lower()

        # Si l'un des deux est totalement vide
        if not job_text or not cv_text:
            return float(self.DEFAULT_SCORE)

        # Recherche de correspondance par mot-clé (sous-chaîne)
        cv_words = [w for w in cv_text.split() if len(w) > 2]
        matches = sum(1 for w in cv_words if w in job_text)

        if matches == 0:
            return 20.0

        # Score calculé en fonction du nombre de correspondances
        score = 50.0 + (matches * 10.0)
        return float(min(100.0, max(10.0, score)))

    def score_batch(self, cv: dict, jobs: list) -> list:
        """
        Score multiple jobs using score_single for perfect consistency.

        Args:
            cv: CV analysis data (dict or string)
            jobs: List of job dictionaries

        Returns:
            List of job dictionaries with 'score' field, sorted by score descending
        """
        if not jobs or not isinstance(jobs, list):
            return []

        scored_jobs = []
        for job in jobs:
            job_dict = self._ensure_dict(job)
            job_copy = job_dict.copy()
            job_copy["score"] = self.score_single(cv, job_copy)
            scored_jobs.append(job_copy)

        scored_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        return scored_jobs

    def score_with_details(self, cv_data: Dict, job: Dict) -> Dict:
        """
        Score a job and return detailed breakdown.

        Args:
            cv_data: CV analysis data
            job: Job dictionary

        Returns:
            Dictionary with score and breakdown (score between 10-100)
        """
        start_time = time.time()

        try:
            cv_text, job_text = self._prepare_text(cv_data, job)

            if not cv_text or not job_text:
                return {
                    "score": 50.0,
                    "breakdown": {
                        "semantic": 50.0,
                        "skills_match": 50.0,
                        "experience_match": 50.0
                    }
                }

            # Fit vectorizer with additional common terms
            if not self._fitted:
                self.vectorizer.fit([cv_text, job_text, "emploi travail job poste"])
                self._fitted = True

            # Transform and calculate
            tfidf_matrix = self.vectorizer.transform([cv_text, job_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

            # Convert to 10-100 scale
            score = max(10.0, min(100.0, float(similarity * 100)))

            # Calculate component scores
            cv_skills = set(cv_data.get('mots_cles', []))
            job_skills = set()
            if job.get('skills'):
                job_skills = set(job['skills'] if isinstance(job['skills'], list) else job['skills'].split(','))

            skills_overlap = len(cv_skills & job_skills) / max(len(cv_skills | job_skills), 1)
            skills_score = skills_overlap * 100

            # Experience match (simplified)
            cv_years = cv_data.get('annees_experience', 0)
            exp_score = min(100, max(0, 100 - abs(cv_years - 5) * 5))

            elapsed = time.time() - start_time

            return {
                "score": score,
                "breakdown": {
                    "semantic": score,
                    "skills_match": skills_score,
                    "experience_match": exp_score
                },
                "timing_ms": round(elapsed * 1000, 2)
            }

        except Exception as e:
            logger.error(f"Detailed scoring error: {e}")
            return {
                "score": 50.0,
                "breakdown": {
                    "semantic": 50.0,
                    "skills_match": 50.0,
                    "experience_match": 50.0
                }
            }


# Global scorer instance
_job_scorer = None


def get_scorer() -> JobScorer:
    """
    Get or create the global job scorer instance.

    Returns:
        JobScorer instance
    """
    global _job_scorer
    if _job_scorer is None:
        _job_scorer = JobScorer()
    return _job_scorer


def score_jobs(cv_data: Dict, jobs: List[Dict], fast: bool = True) -> List[Dict]:
    """
    Convenience function to score jobs.

    Args:
        cv_data: CV analysis data
        jobs: List of job dictionaries
        fast: If True, use batch scoring; if False, score individually with details

    Returns:
        List of jobs with added 'match_score' field
    """
    scorer = get_scorer()

    if fast:
        # score_batch now returns list of job dicts with 'score' field
        scored_jobs = scorer.score_batch(cv_data, jobs)
        # Map 'score' to 'match_score' for compatibility
        for job in scored_jobs:
            job['match_score'] = job.pop('score')
        return scored_jobs
    else:
        for job in jobs:
            result = scorer.score_with_details(cv_data, job)
            job['match_score'] = result['score']
            job['score_breakdown'] = result['breakdown']

        return jobs
