"""
Advanced ranking module using ML
Improves job ranking with: semantic scoring, quality weighting, diversity
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Try to import AI libraries
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    np = None

# Try to load model
try:
    if ML_AVAILABLE:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    else:
        model = None
except Exception as e:
    logger.warning(f"Could not load ranking model: {e}")
    model = None

def calculate_semantic_score(job: Dict, cv_data: Dict) -> float:
    """
    Calculate semantic similarity between job and CV
    Returns score 0-100
    """
    if not cv_data or not model:
        return 50.0  # Default score
    
    try:
        # Build CV text
        cv_text = f"{cv_data.get('metier', '')} {cv_data.get('skills', '')} {cv_data.get('experience', '')}"
        
        # Build job text
        job_text = f"{job.get('title', '')} {job.get('desc', '')} {job.get('skills', '')}"
        
        # Calculate similarity
        embeddings = model.encode([cv_text, job_text])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        return float(similarity * 100)
    except Exception as e:
        logger.warning(f"Semantic scoring failed: {e}")
        return 50.0

def calculate_quality_weight(job: Dict) -> float:
    """
    Calculate quality weight for a job (0-1)
    Higher quality jobs get boosted
    """
    quality_score = job.get('quality_score', 50)
    return min(quality_score / 100, 1.0)

def calculate_diversity_score(job: Dict, selected_jobs: List[Dict]) -> float:
    """
    Calculate diversity score to avoid showing too many similar jobs
    Returns 0-1, where 1 means highly diverse
    """
    if not selected_jobs:
        return 1.0
    
    # Check source diversity
    sources = [j.get('source') for j in selected_jobs]
    source_count = sources.count(job.get('source'))
    
    # Penalize if too many jobs from same source
    if source_count >= 3:
        return 0.5
    elif source_count >= 2:
        return 0.7
    else:
        return 1.0

def rank_jobs_ml(
    jobs: List[Dict],
    cv_data: Optional[Dict] = None,
    filters: Dict = None,
    weights: Dict = None
) -> List[Dict]:
    """
    Advanced ML-based job ranking
    
    Args:
        jobs: List of job dictionaries
        cv_data: CV data for matching
        filters: Search filters (contract, remote, etc.)
        weights: Custom weights for scoring factors
    
    Returns:
        Ranked list of jobs with scores
    """
    if not jobs:
        return []
    
    # Default weights
    default_weights = {
        'semantic': 0.4,      # CV-job match
        'quality': 0.2,       # Job quality
        'diversity': 0.1,     # Source diversity
        'recency': 0.1,       # Date posted
        'completeness': 0.2   # Data completeness
    }
    
    if weights:
        default_weights.update(weights)
    
    logger.info(f"Ranking {len(jobs)} jobs with ML")
    
    # Calculate scores for each job
    scored_jobs = []
    selected_jobs = []  # Track selected for diversity
    
    for job in jobs:
        scores = {}
        
        # 1. Semantic score (CV match)
        scores['semantic'] = calculate_semantic_score(job, cv_data) if cv_data else 50.0
        
        # 2. Quality score
        quality_weight = calculate_quality_weight(job)
        scores['quality'] = quality_weight * 100
        
        # 3. Diversity score
        scores['diversity'] = calculate_diversity_score(job, selected_jobs) * 100
        
        # 4. Recency score
        date = job.get('date', '')
        if date:
            scores['recency'] = 80.0  # Assume recent
        else:
            scores['recency'] = 50.0
        
        # 5. Completeness score
        completeness = 0
        if job.get('title'):
            completeness += 25
        if job.get('company'):
            completeness += 25
        if job.get('desc'):
            completeness += 25
        if job.get('location'):
            completeness += 25
        scores['completeness'] = completeness
        
        # Calculate weighted total
        total_score = sum(
            scores.get(key, 0) * weight
            for key, weight in default_weights.items()
        )
        
        # Apply filter penalties
        if filters:
            contract = filters.get('contract', '').lower()
            remote = filters.get('remote', False)
            
            # Penalize if contract doesn't match
            if contract and contract != 'all':
                job_contract = (job.get('contract_type') or '').lower()
                if job_contract and job_contract != contract:
                    total_score *= 0.8  # 20% penalty
        
        job['ml_score'] = round(total_score, 2)
        job['score_breakdown'] = {k: round(v, 2) for k, v in scores.items()}
        
        scored_jobs.append(job)
    
    # Sort by score descending
    ranked_jobs = sorted(scored_jobs, key=lambda x: x.get('ml_score', 0), reverse=True)
    
    logger.info(f"Ranking complete. Top job score: {ranked_jobs[0].get('ml_score', 0) if ranked_jobs else 0}")
    
    return ranked_jobs

def get_ranking_explanation(job: Dict) -> str:
    """
    Generate human-readable explanation for job ranking
    """
    breakdown = job.get('score_breakdown', {})
    
    explanations = []
    
    if breakdown.get('semantic', 0) > 70:
        explanations.append("✅ Excellent match with your profile")
    elif breakdown.get('semantic', 0) > 50:
        explanations.append("👍 Good match with your profile")
    
    if breakdown.get('quality', 0) > 70:
        explanations.append("⭐ High quality job posting")
    
    if breakdown.get('diversity', 0) < 70:
        explanations.append("📊 Similar to other results")
    
    if not explanations:
        return "Standard match"
    
    return " | ".join(explanations)