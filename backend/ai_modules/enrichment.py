"""
Enrichment module for job postings
Adds: salary estimation, skill tagging, quality scoring
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Salary estimation based on market data (France)
SALARY_BENCHMARKS = {
    'developer': {'junior': (30, 45), 'mid': (45, 65), 'senior': (65, 100)},
    'data': {'junior': (35, 50), 'mid': (50, 75), 'senior': (75, 120)},
    'devops': {'junior': (40, 55), 'mid': (55, 80), 'senior': (80, 130)},
    'manager': {'junior': (45, 60), 'mid': (60, 90), 'senior': (90, 150)},
    'designer': {'junior': (30, 40), 'mid': (40, 55), 'senior': (55, 80)},
}

def estimate_salary(job: Dict) -> Optional[Dict]:
    """
    Estimate salary if not provided in job description
    Based on job title, location, and experience level
    """
    title = job.get('title', '').lower()
    location = job.get('location', '').lower()
    
    # Detect job category
    category = 'developer'
    if any(word in title for word in ['data', 'données', 'analyst', 'scientist']):
        category = 'data'
    elif any(word in title for word in ['devops', 'sre', 'infrastructure']):
        category = 'devops'
    elif any(word in title for word in ['manager', 'lead', 'chef', 'director']):
        category = 'manager'
    elif any(word in title for word in ['designer', 'ux', 'ui', 'graphiste']):
        category = 'designer'
    
    # Detect experience level
    level = 'mid'
    if any(word in title for word in ['senior', 'lead', 'expert', 'principal']):
        level = 'senior'
    elif any(word in title for word in ['junior', 'débutant', 'entry', 'intern']):
        level = 'junior'
    
    # Get salary range
    benchmarks = SALARY_BENCHMARKS.get(category, SALARY_BENCHMARKS['developer'])
    min_salary, max_salary = benchmarks.get(level, (45, 65))
    
    # Adjust for location (Paris premium)
    if 'paris' in location or 'france' in location:
        min_salary *= 1.1
        max_salary *= 1.2
    
    # Calculate estimated salary
    estimated = (min_salary + max_salary) / 2
    
    return {
        'value': int(estimated * 1000),  # Convert to annual EUR
        'unit': 'yearly',
        'currency': 'EUR',
        'estimated': True,
        'range': f"{int(min_salary * 1000)}-{int(max_salary * 1000)}"
    }

def calculate_job_quality_score(job: Dict) -> float:
    """
    Calculate a quality score for a job posting (0-100)
    Based on: description completeness, salary info, company info, etc.
    """
    score = 0.0
    
    # Description completeness (max 30 points)
    desc = job.get('desc', '')
    if desc:
        score += min(len(desc) / 100, 30)  # 1 point per 100 chars, max 30
    
    # Has salary info (20 points)
    if job.get('salary') or any(word in (desc or '').lower() for word in ['salaire', 'rémunération', '€', 'k€']):
        score += 20
    
    # Has company info (15 points)
    if job.get('company') and job.get('company') != 'N/C':
        score += 15
    
    # Has location (10 points)
    if job.get('location'):
        score += 10
    
    # Has source (10 points)
    if job.get('source'):
        score += 10
    
    # Recent posting (15 points)
    date = job.get('date', '')
    if date:
        score += 15  # Assume recent if date exists
    
    return min(score, 100)

def enrich_job_data(job: Dict) -> Dict:
    """
    Enrich job data with additional information
    Adds: estimated salary, quality score, tags
    """
    enriched = job.copy()
    
    # Estimate salary if not present
    if not enriched.get('salary'):
        salary_est = estimate_salary(enriched)
        if salary_est:
            enriched['salary_estimated'] = salary_est
    
    # Calculate quality score
    enriched['quality_score'] = calculate_job_quality_score(enriched)
    
    # Generate tags
    tags = []
    title = enriched.get('title', '').lower()
    
    # Remote tag
    if any(word in title for word in ['remote', 'télétravail', 'distance', 'home']):
        tags.append('remote')
    
    # Urgent tag
    if any(word in title for word in ['urgent', 'recrutement', 'immediate']):
        tags.append('urgent')
    
    # International tag
    if any(word in title for word in ['english', 'international', 'global']):
        tags.append('international')
    
    enriched['tags'] = tags
    
    return enriched

def enrich_jobs_batch(jobs: List[Dict]) -> List[Dict]:
    """
    Enrich a batch of jobs
    """
    return [enrich_job_data(job) for job in jobs]