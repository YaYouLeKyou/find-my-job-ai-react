"""
Job Search Controller - FastAPI SSE Implementation
Real-time job search with Server-Sent Events
"""
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import time
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Mock data for simulation
MOCK_JOBS_DATABASE = {
    "api_partners": [
        {
            "id": "ft_1",
            "titre": "Développeur Python Senior",
            "entreprise": "Capgemini",
            "location": "Paris",
            "date": "2024-01-15",
            "source": "France Travail",
            "description": "Recherche développeur Python avec 5+ ans d'expérience pour projet bancaire.",
            "contrat": "CDI",
            "competences": ["Python", "Django", "SQL", "AWS"]
        },
        {
            "id": "ft_2",
            "titre": "Ingénieur DevOps",
            "entreprise": "Atos",
            "location": "Lyon",
            "date": "2024-01-10",
            "source": "France Travail",
            "description": "Expertise Kubernetes, Docker, CI/CD pour environnement cloud.",
            "contrat": "CDI",
            "competences": ["Kubernetes", "Docker", "CI/CD", "AWS"]
        },
        {
            "id": "adz_1",
            "titre": "Data Scientist",
            "entreprise": "Sopra Steria",
            "location": "Toulouse",
            "date": "2024-01-12",
            "source": "Adzuna",
            "description": "Analyse de données et machine learning pour projet santé.",
            "contrat": "CDI",
            "competences": ["Python", "Machine Learning", "SQL", "TensorFlow"]
        }
    ],
    "scrapers": [
        {
            "id": "li_1",
            "titre": "Full Stack Developer (React/Node)",
            "entreprise": "Doctolib",
            "location": "Paris",
            "date": "2024-01-18",
            "source": "LinkedIn",
            "description": "Développement full stack pour plateforme médicale innovante.",
            "contrat": "CDI",
            "competences": ["React", "Node.js", "TypeScript", "GraphQL"]
        },
        {
            "id": "li_2",
            "titre": "Frontend Developer",
            "entreprise": "Alan",
            "location": "Paris",
            "date": "2024-01-16",
            "source": "LinkedIn",
            "description": "Création d'interfaces utilisateur modernes avec React et TypeScript.",
            "contrat": "CDI",
            "competences": ["React", "TypeScript", "CSS", "Figma"]
        },
        {
            "id": "gj_1",
            "titre": "Backend Engineer",
            "entreprise": "Google",
            "location": "Paris",
            "date": "2024-01-14",
            "source": "Google Jobs",
            "description": "Conception et développement de systèmes distribués.",
            "contrat": "CDI",
            "competences": ["Go", "Kubernetes", "gRPC", "Cloud"]
        }
    ]
}

def simulate_ai_sorting(jobs: List[Dict]) -> List[str]:
    """
    Simulate AI-powered job sorting based on relevance
    Returns sorted list of job IDs
    """
    # Simple relevance scoring based on title and description length
    scored_jobs = []
    for job in jobs:
        # Score based on title length and description length
        title_score = len(job["titre"]) * 0.1
        desc_score = len(job["description"]) * 0.05
        total_score = title_score + desc_score

        # Bonus for certain keywords
        if "Senior" in job["titre"] or "Senior" in job["description"]:
            total_score += 1.5
        if "CDI" in job.get("contrat", ""):
            total_score += 1.0

        scored_jobs.append((job["id"], total_score))

    # Sort by score (descending)
    scored_jobs.sort(key=lambda x: x[1], reverse=True)
    return [job_id for job_id, score in scored_jobs]

@router.get("/stream")
async def stream_jobs(
    request: Request,
    query: str = Query(..., min_length=3, description="Search query"),
    location: str = Query("France", description="Location filter")
):
    """
    Stream job search results using Server-Sent Events (SSE)

    This endpoint simulates a 3-step workflow:
    1. [0.5s] API partners (France Travail, Adzuna) - immediate results
    2. [2.0s] Web scrapers (LinkedIn, Google Jobs) - progressive results
    3. [2.5s] AI sorting - optimized ordering

    Returns:
        StreamingResponse with SSE events: progress, jobs_data, jobs_sorted, complete
    """
    async def event_generator():
        try:
            # Step 1: Initialization
            yield f"data: {json.dumps({'type': 'progress', 'progress': 0, 'message': 'Initialisation de la recherche...'})}\n\n"
            await asyncio.sleep(0.1)

            # Step 2: API Partners (0.5s) - France Travail, Adzuna
            yield f"data: {json.dumps({'type': 'progress', 'progress': 10, 'message': 'Interrogation des APIs partenaires (France Travail, Adzuna)...'})}\n\n"
            await asyncio.sleep(0.5)

            # Send API partner jobs
            api_jobs = MOCK_JOBS_DATABASE["api_partners"]
            yield f"data: {json.dumps({'type': 'jobs_data', 'jobs': api_jobs, 'source': 'api_partners'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 30, 'message': 'API partenaires terminées (3 résultats)'})}\n\n"

            # Step 3: Web Scrapers (2.0s) - LinkedIn, Google Jobs
            yield f"data: {json.dumps({'type': 'progress', 'progress': 40, 'message': 'Scraping en cours (LinkedIn, Google Jobs)...'})}\n\n"
            await asyncio.sleep(1.0)

            # Send LinkedIn jobs
            linkedin_jobs = [job for job in MOCK_JOBS_DATABASE["scrapers"] if job["source"] == "LinkedIn"]
            yield f"data: {json.dumps({'type': 'jobs_data', 'jobs': linkedin_jobs, 'source': 'scrapers'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 60, 'message': 'LinkedIn terminé (2 résultats)'})}\n\n"
            await asyncio.sleep(1.0)

            # Send Google Jobs
            google_jobs = [job for job in MOCK_JOBS_DATABASE["scrapers"] if job["source"] == "Google Jobs"]
            yield f"data: {json.dumps({'type': 'jobs_data', 'jobs': google_jobs, 'source': 'scrapers'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 80, 'message': 'Google Jobs terminé (1 résultat)'})}\n\n"

            # Step 4: AI Sorting (0.5s)
            yield f"data: {json.dumps({'type': 'progress', 'progress': 90, 'message': 'Optimisation IA des résultats...'})}\n\n"
            await asyncio.sleep(0.5)

            # Combine all jobs
            all_jobs = api_jobs + linkedin_jobs + google_jobs
            sorted_job_ids = simulate_ai_sorting(all_jobs)

            # Create sorted jobs list
            jobs_by_id = {job["id"]: job for job in all_jobs}
            sorted_jobs = [jobs_by_id[job_id] for job_id in sorted_job_ids]

            # Send sorted jobs
            yield f"data: {json.dumps({'type': 'jobs_sorted', 'jobs': sorted_jobs})}\n\n"

            # Final completion
            yield f"data: {json.dumps({
                'type': 'complete',
                'total_jobs': len(sorted_jobs),
                'message': f'Recherche terminée ! {len(sorted_jobs)} offres trouvées et triées par pertinence',
                'source_status': {
                    'France Travail': {'success': True, 'jobs_count': len(api_jobs), 'duration': 0.5, 'status': 'completed'},
                    'Adzuna': {'success': True, 'jobs_count': 0, 'duration': 0.5, 'status': 'completed'},  # Included in api_jobs
                    'LinkedIn': {'success': True, 'jobs_count': len(linkedin_jobs), 'duration': 1.0, 'status': 'completed'},
                    'Google Jobs': {'success': True, 'jobs_count': len(google_jobs), 'duration': 1.0, 'status': 'completed'}
                }
            })}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Erreur serveur: {str(e)}'})}\n\n"
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )