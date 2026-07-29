"""
Unit Tests for Job Model
Tests the core domain model independently
"""
import pytest
from datetime import datetime
from core.models.job import Job

def test_job_creation():
    """Test basic job creation"""
    job = Job(
        id="test_123",
        title="Développeur Python",
        company="TechCorp",
        location="Paris",
        source="LinkedIn",
        description="Poste de développeur Python"
    )

    assert job.id == "test_123"
    assert job.title == "Développeur Python"
    assert job.company == "TechCorp"
    assert job.source == "LinkedIn"

def test_job_with_optional_fields():
    """Test job with all optional fields"""
    job = Job(
        id="test_456",
        title="Ingénieur DevOps",
        company="CloudTech",
        location="Lyon",
        source="France Travail",
        description="Poste DevOps",
        posted_date=datetime(2023, 1, 15),
        salary=60000,
        contract_type="CDI",
        url="https://example.com/job",
        pertinence_score=0.85
    )

    assert job.salary == 60000
    assert job.contract_type == "CDI"
    assert job.pertinence_score == 0.85
    assert job.posted_date == datetime(2023, 1, 15)

def test_job_high_quality():
    """Test high quality job detection"""
    # High quality job
    high_quality = Job(
        id="high_1",
        title="Senior Developer",
        company="PremiumTech",
        location="Paris",
        source="LinkedIn",
        description="Senior position",
        salary=75000
    )

    assert high_quality.is_high_quality() == True

def test_job_low_quality():
    """Test low quality job detection"""
    # Low quality - no salary
    no_salary = Job(
        id="low_1",
        title="Junior Developer",
        company="Startup",
        location="Paris",
        source="LinkedIn",
        description="Junior position"
    )

    # Low quality - junior position
    junior = Job(
        id="low_2",
        title="Junior Developer",
        company="TechCorp",
        location="Paris",
        source="LinkedIn",
        description="Junior position",
        salary=30000
    )

    # Low quality - internship
    internship = Job(
        id="low_3",
        title="Stage Développeur",
        company="BigCorp",
        location="Paris",
        source="LinkedIn",
        description="Stage",
        salary=1500
    )

    assert no_salary.is_high_quality() == False
    assert junior.is_high_quality() == False
    assert internship.is_high_quality() == False

def test_job_boundary_quality():
    """Test boundary case for quality"""
    # Exactly at threshold
    boundary = Job(
        id="boundary",
        title="Developer",
        company="TechCorp",
        location="Paris",
        source="LinkedIn",
        description="Mid position",
        salary=35000
    )

    assert boundary.is_high_quality() == True

def test_job_from_dict():
    """Test job creation from dictionary"""
    job_data = {
        "id": "dict_test",
        "title": "Data Scientist",
        "company": "AI Corp",
        "location": "Paris",
        "source": "LinkedIn",
        "description": "Data science position",
        "salary": 55000,
        "contract_type": "CDI"
    }

    job = Job(**job_data)
    assert job.id == "dict_test"
    assert job.salary == 55000