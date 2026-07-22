"""
Data extraction module for job postings
Extracts: skills, salary, contract type, experience level from job descriptions
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import AI libraries
try:
    import spacy
    try:
        nlp = spacy.load("fr_core_news_sm")
    except:
        try:
            nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("Spacy model not found. Install with: python -m spacy download fr_core_news_sm")
            nlp = None
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None

try:
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    embedding_model = None

# Common skills database
SKILLS_DB = {
    'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'go', 'rust', 'swift', 'kotlin'],
    'web': ['react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'laravel', 'html', 'css', 'bootstrap'],
    'data': ['sql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch', 'pandas', 'numpy', 'spark', 'hadoop'],
    'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ci/cd', 'devops'],
    'ai_ml': ['tensorflow', 'pytorch', 'scikit-learn', 'machine learning', 'deep learning', 'nlp', 'computer vision'],
    'soft_skills': ['communication', 'leadership', 'teamwork', 'problem solving', 'agile', 'scrum']
}

def extract_skills(text: str) -> List[str]:
    """Extract skills from job description using keyword matching and NER"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = []
    
    # Keyword matching
    for category, skills in SKILLS_DB.items():
        for skill in skills:
            if skill in text_lower:
                found_skills.append(skill)
    
    # NER extraction if spacy is available
    if nlp:
        doc = nlp(text[:1000])  # Limit text length for performance
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'LANGUAGE']:
                found_skills.append(ent.text)
    
    return list(set(found_skills))

def extract_salary(text: str) -> Optional[Dict]:
    """Extract salary information from job description"""
    if not text:
        return None
    
    # Common salary patterns
    patterns = [
        r'(\d{2,3})\s*[kK€]\s*(?:/an|par an|annuel|year)',
        r'(\d{2,3})\s*000\s*[€E]',
        r'(\d{2,3})\s*[€E]\s*(?:/jour|par jour|jour|/day)',
        r'salaire\s*:?\s*(\d{2,3})',
        r'rémunération\s*:?\s*(\d{2,3})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            salary_value = int(match.group(1))
            if 'jour' in pattern.lower() or '/day' in pattern.lower():
                return {'value': salary_value, 'unit': 'daily', 'currency': 'EUR'}
            else:
                return {'value': salary_value * 1000 if salary_value < 100 else salary_value, 'unit': 'yearly', 'currency': 'EUR'}
    
    return None

def extract_contract_type(text: str, title: str = "") -> str:
    """Extract contract type from job description"""
    combined = f"{title} {text}".lower()
    
    if any(word in combined for word in ['cdi', 'permanent', 'indefinite']):
        return 'CDI'
    elif any(word in combined for word in ['cdd', 'fixed term', 'temporary']):
        return 'CDD'
    elif any(word in combined for word in ['freelance', 'independent', 'contractor']):
        return 'Freelance'
    elif any(word in combined for word in ['stage', 'internship', 'intern']):
        return 'Stage'
    elif any(word in combined for word in ['apprentissage', 'alternance', 'apprentice']):
        return 'Alternance'
    else:
        return 'CDI'  # Default

def extract_experience_level(text: str, title: str = "") -> str:
    """Extract experience level from job description"""
    combined = f"{title} {text}".lower()
    
    if any(word in combined for word in ['senior', 'lead', 'expert', '5+', '6+', '7+', '8+', '10+']):
        return 'Senior'
    elif any(word in combined for word in ['junior', 'débutant', 'entry', '0-2', '1-2']):
        return 'Junior'
    elif any(word in combined for word in ['confirmé', 'mid', 'intermediate', '3+', '4+', '5+']):
        return 'Confirmé'
    else:
        return 'Non spécifié'

def extract_job_data(job: Dict) -> Dict:
    """Extract all enhanced data from a job posting"""
    text = f"{job.get('title', '')} {job.get('desc', '')} {job.get('company', '')}"
    
    return {
        'skills': extract_skills(text),
        'salary': extract_salary(text),
        'contract_type': extract_contract_type(text, job.get('title', '')),
        'experience_level': extract_experience_level(text, job.get('title', '')),
    }