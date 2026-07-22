"""
Deduplication module using semantic similarity
Detects duplicate or near-duplicate job postings
"""

import logging
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    np = None

# Try to import the model
try:
    if EMBEDDINGS_AVAILABLE:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    else:
        model = None
except Exception as e:
    logger.warning(f"Could not load embedding model: {e}")
    model = None

def calculate_similarity(job1: Dict, job2: Dict) -> float:
    """
    Calculate similarity between two jobs
    Returns a score between 0 and 1
    """
    if not job1 or not job2:
        return 0.0
    
    # Use embeddings if available
    if EMBEDDINGS_AVAILABLE and model:
        try:
            text1 = f"{job1.get('title', '')} {job1.get('company', '')} {job1.get('location', '')}"
            text2 = f"{job2.get('title', '')} {job2.get('company', '')} {job2.get('location', '')}"
            
            emb1 = model.encode([text1])
            emb2 = model.encode([text2])
            
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        except Exception as e:
            logger.warning(f"Embedding similarity failed: {e}")
    
    # Fallback to string similarity
    title1 = job1.get('title', '')
    title2 = job2.get('title', '')
    
    if not title1 or not title2:
        return 0.0
    
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()

def deduplicate_jobs(jobs: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """
    Remove duplicate jobs from a list
    Uses semantic similarity to detect near-duplicates
    
    Args:
        jobs: List of job dictionaries
        threshold: Similarity threshold (0-1) above which jobs are considered duplicates
    
    Returns:
        Deduplicated list of jobs
    """
    if not jobs:
        return []
    
    logger.info(f"Deduplicating {len(jobs)} jobs with threshold {threshold}")
    
    unique_jobs = []
    seen_embeddings = []
    
    for job in jobs:
        is_duplicate = False
        
        # Check against already seen jobs
        for seen_job in unique_jobs:
            similarity = calculate_similarity(job, seen_job)
            
            if similarity >= threshold:
                is_duplicate = True
                logger.debug(f"Duplicate found: '{job.get('title')}' similar to '{seen_job.get('title')}' ({similarity:.2f})")
                break
        
        if not is_duplicate:
            unique_jobs.append(job)
    
    logger.info(f"Deduplication complete: {len(jobs)} -> {len(unique_jobs)} jobs")
    return unique_jobs

def find_similar_jobs(job: Dict, job_list: List[Dict], top_k: int = 5) -> List[Tuple[Dict, float]]:
    """
    Find the most similar jobs to a given job
    
    Returns:
        List of (job, similarity_score) tuples
    """
    if not job or not job_list:
        return []
    
    similarities = []
    for other_job in job_list:
        if other_job.get('id') == job.get('id'):
            continue
        
        similarity = calculate_similarity(job, other_job)
        similarities.append((other_job, similarity))
    
    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    return similarities[:top_k]