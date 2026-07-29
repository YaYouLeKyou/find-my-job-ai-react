"""
Unit Tests for Job Search Service
Tests the core business logic independently
"""
import pytest
from unittest.mock import AsyncMock
from core.services.job_search_service import JobSearchService
from core.exceptions.job_search_error import JobSearchError, ValidationError
from core.models.job import Job

@pytest.mark.asyncio
async def test_search_jobs_success():
    """Test successful job search"""
    # Create mock repository
    mock_repo = AsyncMock()
    mock_repo.search_from_sources.return_value = [
        Job(id="1", title="Dev Python", company="TechCorp", location="Paris",
            source="LinkedIn", description="Python dev", salary=50000),
        Job(id="2", title="Dev Java", company="JavaCorp", location="Lyon",
            source="LinkedIn", description="Java dev", salary=45000)
    ]

    service = JobSearchService(mock_repo)

    # Test without CV data
    results = await service.search_jobs("Developer", "France", ["LinkedIn"])

    assert len(results) == 2
    assert all(job.is_high_quality() for job in results)
    mock_repo.search_from_sources.assert_called_once_with("Developer", "France", ["LinkedIn"])

@pytest.mark.asyncio
async def test_search_jobs_with_cv_data():
    """Test job search with CV data for pertinence scoring"""
    mock_repo = AsyncMock()
    mock_repo.search_from_sources.return_value = [
        Job(id="1", title="Python Developer", company="TechCorp", location="Paris",
            source="LinkedIn", description="Python Django Flask", salary=50000),
        Job(id="2", title="Java Developer", company="JavaCorp", location="Lyon",
            source="LinkedIn", description="Java Spring", salary=45000)
    ]

    service = JobSearchService(mock_repo)

    cv_data = {
        "skills": ["Python", "Django", "SQL"],
        "keywords": ["backend", "API development"]
    }

    results = await service.search_jobs(
        "Developer", "France", ["LinkedIn"], cv_data
    )

    # Python job should have higher score
    python_job = next(j for j in results if j.title == "Python Developer")
    java_job = next(j for j in results if j.title == "Java Developer")

    assert python_job.pertinence_score > java_job.pertinence_score
    assert results[0].title == "Python Developer"  # Should be first due to higher score

@pytest.mark.asyncio
async def test_search_jobs_validation_error():
    """Test validation errors"""
    mock_repo = AsyncMock()
    service = JobSearchService(mock_repo)

    # Test short query
    with pytest.raises(JobSearchError, match="Query must be at least 3 characters"):
        await service.search_jobs("De", "France", ["LinkedIn"])

    # Test no sources
    with pytest.raises(JobSearchError, match="At least one source must be selected"):
        await service.search_jobs("Developer", "France", [])

    # Test too many sources
    with pytest.raises(JobSearchError, match="Too many sources selected"):
        sources = ["Source" + str(i) for i in range(11)]
        await service.search_jobs("Developer", "France", sources)

@pytest.mark.asyncio
async def test_search_jobs_repository_error():
    """Test error handling when repository fails"""
    mock_repo = AsyncMock()
    mock_repo.search_from_sources.side_effect = Exception("Repository failed")

    service = JobSearchService(mock_repo)

    with pytest.raises(JobSearchError, match="Job search failed"):
        await service.search_jobs("Developer", "France", ["LinkedIn"])

@pytest.mark.asyncio
async def test_filter_low_quality_jobs():
    """Test that low quality jobs are filtered out"""
    mock_repo = AsyncMock()
    mock_repo.search_from_sources.return_value = [
        Job(id="1", title="Senior Dev", company="TechCorp", location="Paris",
            source="LinkedIn", description="Senior", salary=60000),  # High quality
        Job(id="2", title="Junior Dev", company="Startup", location="Paris",
            source="LinkedIn", description="Junior", salary=30000),  # Low quality
        Job(id="3", title="Dev", company="Corp", location="Paris",
            source="LinkedIn", description="Mid", salary=40000)       # High quality
    ]

    service = JobSearchService(mock_repo)
    results = await service.search_jobs("Developer", "France", ["LinkedIn"])

    # Should only return high quality jobs
    assert len(results) == 2
    assert all(job.salary >= 35000 for job in results)
    assert "Junior Dev" not in [job.title for job in results]

def test_pertinence_scoring_logic():
    """Test the pertinence scoring algorithm"""
    service = JobSearchService(AsyncMock())

    jobs = [
        Job(id="1", title="Python Backend Developer", description="Python Django API development",
            company="TechCorp", location="Paris", source="LinkedIn", salary=50000),
        Job(id="2", title="Frontend Developer", description="React JavaScript HTML CSS",
            company="WebCorp", location="Paris", source="LinkedIn", salary=45000)
    ]

    cv_data = {
        "skills": ["Python", "Django", "API"],
        "keywords": ["backend development"]
    }

    # Apply scoring (this is the internal method we're testing)
    scored_jobs = service._calculate_pertinence_scores(jobs, cv_data)

    python_job = next(j for j in scored_jobs if "Python" in j.title)
    frontend_job = next(j for j in scored_jobs if "Frontend" in j.title)

    assert python_job.pertinence_score > frontend_job.pertinence_score
    assert 0.3 <= python_job.pertinence_score <= 1.0