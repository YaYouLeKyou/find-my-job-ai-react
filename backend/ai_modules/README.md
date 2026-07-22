# AI Modules for Enhanced Job Scraping

This package contains AI/ML modules to boost your job scraping with intelligent data extraction, deduplication, enrichment, and ranking.

## 📦 Modules

### 1. Data Extraction (`data_extraction.py`)
Extracts structured information from job postings:

- **Skills extraction**: Keyword matching + NER (Named Entity Recognition)
- **Salary detection**: Regex patterns for salary extraction
- **Contract type**: CDI, CDD, Freelance, Stage, Alternance
- **Experience level**: Junior, Confirmé, Senior

**Usage:**
```python
from ai_modules.data_extraction import extract_job_data

job = {
    "title": "Senior Python Developer",
    "desc": "We are looking for a senior developer...",
    "company": "Tech Corp"
}

enhanced = extract_job_data(job)
# Returns: {
#   'skills': ['python', 'django', 'postgresql', ...],
#   'salary': {'value': 65000, 'unit': 'yearly', 'currency': 'EUR'},
#   'contract_type': 'CDI',
#   'experience_level': 'Senior'
# }
```

### 2. Deduplication (`deduplication.py`)
Removes duplicate and near-duplicate job postings:

- **Semantic similarity**: Uses Sentence-BERT embeddings
- **Fallback**: String similarity with SequenceMatcher
- **Configurable threshold**: Adjustable similarity threshold (default: 0.85)

**Usage:**
```python
from ai_modules.deduplication import deduplicate_jobs

jobs = [job1, job2, job3, ...]
unique_jobs = deduplicate_jobs(jobs, threshold=0.85)
# Returns: [job1, job3, ...] (duplicates removed)
```

### 3. Enrichment (`enrichment.py`)
Adds valuable metadata to job postings:

- **Salary estimation**: Predicts salary if not provided
- **Quality scoring**: 0-100 score based on completeness
- **Auto-tagging**: Remote, urgent, international tags

**Usage:**
```python
from ai_modules.enrichment import enrich_job_data, enrich_jobs_batch

# Single job
enriched_job = enrich_job_data(job)
# Adds: salary_estimated, quality_score, tags

# Batch processing
enriched_jobs = enrich_jobs_batch(jobs)
```

### 4. Ranking (`ranking.py`)
Advanced ML-based job ranking:

- **Semantic scoring**: CV-job match using embeddings
- **Quality weighting**: Boosts high-quality postings
- **Diversity**: Avoids showing too many similar jobs
- **Recency**: Prefers recent postings
- **Completeness**: Rewards complete data

**Usage:**
```python
from ai_modules.ranking import rank_jobs_ml

ranked_jobs = rank_jobs_ml(
    jobs=jobs,
    cv_data=cv_data,  # Optional: for semantic matching
    filters={"contract": "CDI", "remote": True},
    weights={
        'semantic': 0.4,
        'quality': 0.2,
        'diversity': 0.1,
        'recency': 0.1,
        'completeness': 0.2
    }
)

# Each job gets: ml_score, score_breakdown
```

## 🚀 Installation

### Prerequisites
```bash
# Install Python packages
pip install sentence-transformers spacy scikit-learn nltk

# Download spaCy models
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm
```

### Add to requirements.txt
```txt
sentence-transformers>=2.2.0
spacy>=3.7.0
scikit-learn>=1.3.0
nltk>=3.8.0
```

## 🔧 Configuration

The modules are automatically imported in `api.py` and will be available if the packages are installed. If not, the system falls back to basic functionality.

Check availability:
```python
from ai_modules import AI_MODULES_AVAILABLE

if AI_MODULES_AVAILABLE:
    print("AI modules are ready!")
else:
    print("AI modules not available, using basic mode")
```

## 📊 Integration in API

The AI modules are integrated into the job search pipeline in `api.py`:

```python
# After collecting all results
if AI_MODULES_AVAILABLE:
    # 1. Enrich jobs with additional data
    all_results = enrich_jobs_batch(all_results)
    
    # 2. Deduplicate
    all_results = deduplicate_jobs(all_results, threshold=0.85)
    
    # 3. Rank with ML (if CV data available)
    if req.cv_data:
        all_results = rank_jobs_ml(all_results, cv_data=req.cv_data)
```

## 🎯 Benefits

1. **Better data quality**: Extracted skills, salary, contract type
2. **No duplicates**: Semantic deduplication removes near-duplicates
3. **Smarter ranking**: ML-based scoring considers multiple factors
4. **Richer results**: Estimated salaries, quality scores, tags
5. **Improved UX**: More relevant job recommendations

## ⚠️ Notes

- **Performance**: First run loads ML models (may take a few seconds)
- **Memory**: Sentence-BERT model uses ~500MB RAM
- **Fallback**: If packages not installed, basic functionality still works
- **Optional**: AI modules enhance but are not required

## 🔄 Workflow

```
Job Scraping → Data Extraction → Deduplication → Enrichment → ML Ranking → Results
```

## 📈 Performance Tips

1. **Cache embeddings**: Store embeddings to avoid recomputing
2. **Batch processing**: Process jobs in batches for efficiency
3. **Threshold tuning**: Adjust deduplication threshold (0.8-0.9)
4. **Model selection**: Use smaller models for faster inference

## 🛠️ Troubleshooting

**Import errors:**
```bash
# If modules not found, check Python path
python -c "import sys; print(sys.path)"
```

**spaCy model not found:**
```bash
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm
```

**Memory issues:**
- Use smaller embedding models
- Process jobs in smaller batches
- Disable modules if not needed

## 📝 TODO

- [ ] Add more skills to SKILLS_DB
- [ ] Improve salary estimation with ML
- [ ] Add support for more languages
- [ ] Implement caching for embeddings
- [ ] Add A/B testing for ranking weights
- [ ] Fine-tune models on job data

## 📊 Metrics

Track these metrics to measure improvement:
- Duplicate rate before/after deduplication
- User click-through rate on ranked jobs
- Quality score distribution
- Processing time per search

---

**Author**: Yanès Hadiouche  
**Email**: findmyworkai@gmail.com  
**GitHub**: https://github.com/YaYouLeKyou/find-my-job-ai-react