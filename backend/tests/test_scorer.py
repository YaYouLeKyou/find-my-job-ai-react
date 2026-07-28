"""
Tests for AI Scoring Service
Validates TF-IDF + Cosine Similarity scoring performance
"""

import time
import pytest
from typing import Dict, List

# Import the scorer module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.scorer import get_scorer, score_jobs


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_cv_data() -> Dict:
    """Sample CV data for testing."""
    return {
        "metier": "Développeur Full Stack",
        "mots_cles": ["Python", "JavaScript", "React", "Node.js", "SQL", "Git", "Docker"],
        "experience": "5 ans d'expérience en développement web",
        "resume": "Développeur passionné avec expertise en technologies web modernes"
    }


@pytest.fixture
def sample_jobs() -> List[Dict]:
    """Sample job listings for testing."""
    return [
        {
            "title": "Développeur Full Stack Python/React",
            "company": "TechCorp",
            "description": "Nous recherchons un développeur Full Stack maîtrisant Python, React et SQL pour rejoindre notre équipe dynamique.",
            "skills": ["Python", "React", "SQL", "Docker"]
        },
        {
            "title": "Ingénieur JavaScript Node.js",
            "company": "StartupXYZ",
            "description": "Poste d'ingénieur backend spécialisé dans Node.js et les architectures microservices.",
            "skills": ["Node.js", "JavaScript", "MongoDB", "AWS"]
        },
        {
            "title": "Data Scientist Machine Learning",
            "company": "DataAI",
            "description": "Nous cherchons un data scientist pour développer des modèles de machine learning.",
            "skills": ["Python", "TensorFlow", "PyTorch", "SQL"]
        },
        {
            "title": "DevOps Engineer",
            "company": "CloudTech",
            "description": "Ingénieur DevOps pour gérer notre infrastructure cloud et nos pipelines CI/CD.",
            "skills": ["Docker", "Kubernetes", "AWS", "Python"]
        },
        {
            "title": "Développeur Frontend React",
            "company": "WebAgency",
            "description": "Développeur frontend spécialisé dans React et les interfaces utilisateur modernes.",
            "skills": ["React", "JavaScript", "CSS", "TypeScript"]
        }
    ]


@pytest.fixture
def scorer():
    """Get a fresh scorer instance for each test."""
    # Reset the global scorer to ensure clean state
    from app.services.scorer import _job_scorer
    import app.services.scorer as scorer_module
    scorer_module._job_scorer = None
    return get_scorer()


# ─── Test Score Range ─────────────────────────────────────────────────────────

class TestScoreRange:
    """Test that scores are within valid range."""

    def test_single_job_score_range(self, scorer, sample_cv_data, sample_jobs):
        """Test that a single job score is between 10 and 100."""
        job = sample_jobs[0]
        score = scorer.score_single(sample_cv_data, job)

        assert 10 <= score <= 100, f"Score {score} is out of range [10, 100]"

    def test_batch_scores_range(self, scorer, sample_cv_data, sample_jobs):
        """Test that all batch scores are between 10 and 100."""
        scores = scorer.score_batch(sample_cv_data, sample_jobs)

        assert len(scores) == len(sample_jobs), "Should return one score per job"

        for i, job in enumerate(scores):
            score = job.get('score', 0)
            assert 10 <= score <= 100, f"Score {score} for job {i} is out of range [10, 100]"

    def test_detailed_score_range(self, scorer, sample_cv_data, sample_jobs):
        """Test that detailed scores are within valid range."""
        result = scorer.score_with_details(sample_cv_data, sample_jobs[0])

        assert 10 <= result['score'] <= 100, f"Score {result['score']} is out of range [10, 100]"
        assert 'breakdown' in result, "Should include score breakdown"
        assert 'timing_ms' in result, "Should include timing information"


# ─── Test Performance ────────────────────────────────────────────────────────

class TestPerformance:
    """Test scoring performance targets."""

    def test_single_job_performance(self, scorer, sample_cv_data, sample_jobs):
        """Test that single job scoring is under 50ms."""
        job = sample_jobs[0]

        start = time.time()
        score = scorer.score_single(sample_cv_data, job)
        elapsed = time.time() - start

        assert score > 0, "Score should be positive"
        assert elapsed < 0.05, f"Single job scoring took {elapsed*1000:.1f}ms (target: <50ms)"

    def test_batch_performance_50_jobs(self, scorer, sample_cv_data):
        """Test that batch scoring of 50 jobs is under 50ms per job on average."""
        # Create 50 sample jobs
        jobs_50 = []
        for i in range(50):
            jobs_50.append({
                "title": f"Développeur Poste {i}",
                "company": f"Company {i}",
                "description": f"Poste de développeur avec Python, JavaScript, React, Node.js et SQL. Mission numéro {i}.",
                "skills": ["Python", "JavaScript", "React"]
            })

        start = time.time()
        scores = scorer.score_batch(sample_cv_data, jobs_50)
        elapsed = time.time() - start

        assert len(scores) == 50, "Should score all 50 jobs"

        avg_time_ms = (elapsed / 50) * 1000
        assert avg_time_ms < 50, f"Average scoring time {avg_time_ms:.1f}ms/job exceeds 50ms target"

        # Log performance for monitoring
        print(f"\n✅ Batch scoring performance: {elapsed*1000:.1f}ms total, {avg_time_ms:.1f}ms/job")

    def test_batch_performance_100_jobs(self, scorer, sample_cv_data):
        """Test that batch scoring of 100 jobs maintains performance."""
        # Create 100 sample jobs
        jobs_100 = []
        for i in range(100):
            jobs_100.append({
                "title": f"Ingénieur Software {i}",
                "company": f"Tech Company {i}",
                "description": f"Recherche ingénieur logiciel avec compétences en Python, Docker, Git, SQL et cloud computing.",
                "skills": ["Python", "Docker", "Git", "SQL"]
            })

        start = time.time()
        scores = scorer.score_batch(sample_cv_data, jobs_100)
        elapsed = time.time() - start

        assert len(scores) == 100, "Should score all 100 jobs"

        avg_time_ms = (elapsed / 100) * 1000
        assert avg_time_ms < 50, f"Average scoring time {avg_time_ms:.1f}ms/job exceeds 50ms target"

        print(f"\n✅ Batch scoring (100 jobs): {elapsed*1000:.1f}ms total, {avg_time_ms:.1f}ms/job")


# ─── Test Sorting ────────────────────────────────────────────────────────────

class TestSorting:
    """Test that jobs are correctly sorted by score."""

    def test_batch_sorting_descending(self, scorer, sample_cv_data, sample_jobs):
        """Test that batch scoring returns jobs sorted by descending score."""
        # Score jobs using the convenience function
        scored_jobs = score_jobs(sample_cv_data, sample_jobs.copy(), fast=True)

        # Extract scores
        scores = [job.get('match_score', 0) for job in scored_jobs]

        # Check descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i+1], \
                f"Score at index {i} ({scores[i]}) should be >= score at index {i+1} ({scores[i+1]})"

    def test_manual_sorting(self, scorer, sample_cv_data, sample_jobs):
        """Test manual sorting of jobs by score."""
        # Score jobs
        scored_jobs = []
        for job in sample_jobs:
            score = scorer.score_single(sample_cv_data, job)
            job_copy = job.copy()
            job_copy['match_score'] = score
            scored_jobs.append(job_copy)

        # Sort manually
        sorted_jobs = sorted(scored_jobs, key=lambda x: x.get('match_score', 0), reverse=True)

        # Verify descending order
        scores = [job['match_score'] for job in sorted_jobs]
        assert scores == sorted(scores, reverse=True), "Jobs should be sorted by descending score"


# ─── Test Score Quality ──────────────────────────────────────────────────────

class TestScoreQuality:
    """Test that scoring produces meaningful results."""

    def test_relevant_job_has_higher_score(self, scorer, sample_cv_data):
        """Test that a highly relevant job gets a higher score than an irrelevant one."""
        relevant_job = {
            "title": "Développeur Full Stack Python React",
            "company": "TechCorp",
            "description": "Développeur Full Stack avec Python, React, SQL, Git, Docker",
            "skills": ["Python", "React", "SQL", "Docker", "Git"]
        }

        irrelevant_job = {
            "title": "Comptable Général",
            "company": "AccountingFirm",
            "description": "Nous recherchons un comptable pour gérer notre comptabilité générale.",
            "skills": ["Comptabilité", "Sage", "Excel"]
        }

        relevant_score = scorer.score_single(sample_cv_data, relevant_job)
        irrelevant_score = scorer.score_single(sample_cv_data, irrelevant_job)

        assert relevant_score > irrelevant_score, \
            f"Relevant job score ({relevant_score}) should be higher than irrelevant job ({irrelevant_score})"

    def test_score_consistency(self, scorer, sample_cv_data, sample_jobs):
        """Test that scoring the same job multiple times gives consistent results."""
        job = sample_jobs[0]

        score1 = scorer.score_single(sample_cv_data, job)
        score2 = scorer.score_single(sample_cv_data, job)

        # Scores should be very close (within 1 point)
        assert abs(score1 - score2) < 1.0, \
            f"Scoring is inconsistent: {score1} vs {score2}"

    def test_batch_vs_single_consistency(self, scorer, sample_cv_data, sample_jobs):
        """Test that batch scoring gives similar results to single scoring."""
        # Single scoring
        single_scores = [scorer.score_single(sample_cv_data, job) for job in sample_jobs]

        # Batch scoring
        batch_results = scorer.score_batch(sample_cv_data, sample_jobs)

        # Extract scores from batch results and sort both for comparison
        batch_scores = sorted([job.get('score', 0) for job in batch_results], reverse=True)
        single_sorted = sorted(single_scores, reverse=True)

        # Compare (allow small differences due to vectorizer fitting)
        for i, (single, batch) in enumerate(zip(single_sorted, batch_scores)):
            assert abs(single - batch) < 5.0, \
                f"Batch and single scoring differ too much for job {i}: {single} vs {batch}"


# ─── Test Edge Cases ─────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_cv_data(self, scorer):
        """Test scoring with empty CV data."""
        job = {
            "title": "Développeur Python",
            "description": "Poste de développeur Python",
            "skills": ["Python"]
        }

        score = scorer.score_single({}, job)
        assert score == 50.0, "Should return default score for empty CV"

    def test_empty_job_data(self, scorer, sample_cv_data):
        """Test scoring with empty job data."""
        score = scorer.score_single(sample_cv_data, {})
        assert score == 50.0, "Should return default score for empty job"

    def test_missing_fields(self, scorer, sample_cv_data):
        """Test scoring with missing fields."""
        job = {
            "title": "Développeur"
            # Missing description and skills
        }

        score = scorer.score_single(sample_cv_data, job)
        assert 10 <= score <= 100, "Should handle missing fields gracefully"

    def test_empty_jobs_list(self, scorer, sample_cv_data):
        """Test batch scoring with empty jobs list."""
        scores = scorer.score_batch(sample_cv_data, [])
        assert scores == [], "Should return empty list for empty jobs"


# ─── Test Convenience Function ───────────────────────────────────────────────

class TestConvenienceFunction:
    """Test the score_jobs convenience function."""

    def test_score_jobs_fast(self, scorer, sample_cv_data, sample_jobs):
        """Test score_jobs with fast=True."""
        from app.services.scorer import score_jobs

        jobs_copy = sample_jobs.copy()
        scored = score_jobs(sample_cv_data, jobs_copy, fast=True)

        assert all('match_score' in job for job in scored), "All jobs should have match_score"
        assert all(10 <= job['match_score'] <= 100 for job in scored), "All scores should be in range"

    def test_score_jobs_detailed(self, scorer, sample_cv_data, sample_jobs):
        """Test score_jobs with fast=False."""
        from app.services.scorer import score_jobs

        jobs_copy = sample_jobs.copy()
        scored = score_jobs(sample_cv_data, jobs_copy, fast=False)

        assert all('match_score' in job for job in scored), "All jobs should have match_score"
        assert all('score_breakdown' in job for job in scored), "All jobs should have score_breakdown"
