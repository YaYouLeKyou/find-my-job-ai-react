# 🚀 Guide Complet de Refactorisation - FindMyJobAI

## 📋 Sommaire

1. [Diagnostic Architectural](#-diagnostic-architectural)
2. [Nouvelle Architecture Cible](#-nouvelle-architecture-cible)
3. [Stratégie de Migration Sécurisée](#-stratégie-de-migration-sécurisée)
4. [Prompts de Refactorisation](#-prompts-de-refactorisation)
5. [Bonnes Pratiques et Patterns](#-bonnes-pratiques-et-patterns)

---

## 🔍 Diagnostic Architectural

### 🔴 Problèmes Critiques

| Problème | Localisation | Impact |
|----------|-------------|--------|
| God Object (901 lignes) | `frontend/src/App.jsx` | Maintenance difficile, tests impossibles |
| Couplage fort | Frontend ↔ Backend | Évolutivité limitée, refactorisation risquée |
| Duplication de code | Gestion SSE, logging, erreurs | Maintenance coûteuse, bugs potentiels |
| Mauvaise séparation | Mix présentation/logique | Réutilisation impossible, tests difficiles |
| Architecture monolithique | Backend et Frontend | Scalabilité limitée, onboardings complexes |

### 🟠 Problèmes Modérés

| Problème | Localisation | Solution Proposée |
|----------|-------------|-------------------|
| Gestion d'état non optimisée | `useState` partout | Migration vers Zustand/Redux |
| Absence de TypeScript | Frontend complet | Ajout progressif de TypeScript |
| Structure de dossiers floue | Backend/Frontend | Organisation par features/domaines |
| Gestion d'erreurs inconsistante | Partout | Middleware d'erreurs centralisé |

---

## 📁 Nouvelle Architecture Cible

### Backend: Clean Architecture

```
backend/
└── app/
    ├── main.py                # FastAPI app + routes seulement
    ├── config/                # Configuration centralisée
    │   ├── settings.py         # Settings class avec validation
    │   └── dependencies.py    # Dependency injection
    ├── core/                  # Logique métier pure (indépendante)
    │   ├── models/            # Modèles métier (Job, Source, etc.)
    │   ├── services/          # Services métier (JobSearchService)
    │   ├── repositories/      # Interfaces de persistence
    │   ├── exceptions.py      # Exceptions personnalisées
    │   └── dto/               # Data Transfer Objects
    ├── infrastructure/        # Implémentations concrètes
    │   ├── api/               # Endpoints FastAPI
    │   │   ├── controllers/   # Contrôleurs
    │   │   └── routes.py      # Définition des routes
    │   ├── scrapers/          # Scrapers externes
    │   ├── databases/         # Accès base de données
    │   └── external/          # Services externes (AI, APIs)
    └── interfaces/            # Contrats/interfaces
        ├── repositories/      # Interfaces repositories
        └── services/         # Interfaces services
```

### Frontend: Feature-First Architecture

```
frontend/
└── src/
    ├── main.jsx               # Point d'entrée React
    ├── App.jsx                # Routing principal
    ├── features/              # Fonctionnalités métiers
    │   ├── job-search/        # Recherche d'emplois
    │   │   ├── components/    # Composants spécifiques
    │   │   ├── hooks/         # Hooks personnalisés
    │   │   ├── services/      # Services API
    │   │   ├── store/         # État local (Zustand)
    │   │   ├── types/         # Types TypeScript
    │   │   └── index.jsx      # Export principal
    │   ├── cv-analysis/       # Analyse de CV
    │   └── user-profile/      # Profil utilisateur
    ├── shared/                # Partagé entre features
    │   ├── components/        # Composants UI réutilisables
    │   ├── hooks/            # Hooks génériques
    │   ├── services/         # Services partagés (API client)
    │   ├── store/            # Store global
    │   ├── utils/            # Utilitaires
    │   └── types/            # Types TypeScript globaux
    ├── lib/                  # Bibliothèques internes
    └── styles/               # Styles globaux et thèmes
```

---

## 🛠️ Stratégie de Migration Sécurisée

### Phase 1: Préparation (1-2 jours)
```bash
# 1. Ajouter TypeScript au frontend
npm install --save-dev typescript @types/react @types/react-dom @types/node
npx tsc --init --jsx react --esModuleInterop true --strict true --skipLibCheck true

# 2. Installer les dépendances backend
pip install pydantic python-dotenv inject

# 3. Créer la nouvelle structure de dossiers
mkdir -p backend/app/core/{models,services,repositories,exceptions,dto}
mkdir -p backend/app/infrastructure/{api/controllers,scrapers,databases,external}
mkdir -p backend/app/interfaces/{repositories,services}
mkdir -p frontend/src/features/job-search/{components,hooks,services,store,types}
```

### Phase 2: Refactorisation Backend (3-5 jours)

#### Étape 2.1: Extraire les modèles métier
```python
# backend/app/core/models/job.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    source: str
    description: str
    posted_date: Optional[datetime] = None
    salary: Optional[float] = None
    contract_type: Optional[str] = None
    url: Optional[str] = None
    pertinence_score: Optional[float] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "linkedin_12345",
                "title": "Développeur Full-Stack",
                "company": "TechCorp",
                "location": "Paris, France",
                "source": "LinkedIn",
                "description": "Recherche développeur Full-Stack...",
                "posted_date": "2023-01-15T10:30:00",
                "salary": 50000,
                "contract_type": "CDI",
                "url": "https://linkedin.com/jobs/12345",
                "pertinence_score": 0.95
            }
        }
```

#### Étape 2.2: Créer les interfaces repositories
```python
# backend/app/interfaces/repositories/job_repository.py
from abc import ABC, abstractmethod
from typing import List
from backend.app.core.models.job import Job

class JobRepositoryInterface(ABC):
    @abstractmethod
    async def search_from_sources(self, query: str, location: str, sources: List[str]) -> List[Job]:
        """Search jobs from multiple sources"""

    @abstractmethod
    async def get_job_details(self, job_id: str) -> Job:
        """Get detailed information about a specific job"""

    @abstractmethod
    async def get_suggested_jobs(self, cv_data: dict) -> List[Job]:
        """Get jobs suggested based on CV analysis"""
```

#### Étape 2.3: Implémenter le service métier
```python
# backend/app/core/services/job_search_service.py
from typing import List
from backend.app.core.models.job import Job
from backend.app.core.exceptions import JobSearchError
from backend.app.interfaces.repositories.job_repository import JobRepositoryInterface
from backend.app.core.dto.search_params import SearchParams

class JobSearchService:
    def __init__(self, repository: JobRepositoryInterface):
        self.repository = repository

    async def search_jobs(self, params: SearchParams) -> List[Job]:
        """
        Search jobs with proper business logic separation

        Args:
            params: SearchParams containing query, location, sources, etc.

        Returns:
            List of Job objects

        Raises:
            JobSearchError: If search fails
        """
        self._validate_search_params(params)

        try:
            jobs = await self.repository.search_from_sources(
                query=params.query,
                location=params.location,
                sources=params.sources
            )

            # Apply business rules
            filtered_jobs = self._filter_low_quality_jobs(jobs)
            scored_jobs = self._calculate_pertinence_scores(filtered_jobs, params.cv_data)

            return sorted(scored_jobs, key=lambda j: j.pertinence_score or 0, reverse=True)

        except Exception as e:
            raise JobSearchError(f"Job search failed: {str(e)}") from e

    def _validate_search_params(self, params: SearchParams):
        """Validate business rules for search parameters"""
        if not params.query or len(params.query.strip()) < 3:
            raise JobSearchError("Query must be at least 3 characters")

        if not params.sources:
            raise JobSearchError("At least one source must be selected")

        if len(params.sources) > 10:
            raise JobSearchError("Too many sources selected (max 10)")

    def _filter_low_quality_jobs(self, jobs: List[Job]) -> List[Job]:
        """Apply business filters to exclude low-quality jobs"""
        return [
            job for job in jobs
            if not (job.title and "senior" in job.title.lower() and (job.salary or 0) < 40000)
        ]

    def _calculate_pertinence_scores(self, jobs: List[Job], cv_data: dict = None) -> List[Job]:
        """Calculate pertinence scores based on CV data when available"""
        for job in jobs:
            if cv_data and 'skills' in cv_data:
                # Simple keyword matching - could be enhanced with ML
                job.pertinence_score = self._calculate_keyword_match_score(job, cv_data)
            else:
                job.pertinence_score = 0.5  # Default score
        return jobs

    def _calculate_keyword_match_score(self, job: Job, cv_data: dict) -> float:
        """Calculate score based on keyword matching between job and CV"""
        cv_skills = set(skill.lower() for skill in cv_data.get('skills', []))
        job_keywords = set(word.lower() for word in f"{job.title} {job.description}".split() if len(word) > 4)

        matches = cv_skills.intersection(job_keywords)
        return min(1.0, 0.3 + len(matches) * 0.15)  # Score between 0.3 and 1.0
```

#### Étape 2.4: Créer le contrôleur FastAPI
```python
# backend/app/infrastructure/api/controllers/jobs_controller.py
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from typing import List
from backend.app.core.services.job_search_service import JobSearchService
from backend.app.core.dto.search_params import SearchParams
from backend.app.core.exceptions import JobSearchError
import json
import logging

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/stream")
async def stream_jobs(
    request: Request,
    query: str = Query(..., min_length=3),
    location: str = Query("Paris, France"),
    sources: str = Query("LinkedIn,France Travail,Google Jobs"),
    num_ads: int = Query(100, ge=10, le=500),
    contract: str = Query("CDI"),
    remote: bool = Query(False)
):
    """
    Stream job search results using Server-Sent Events (SSE)

    Args:
        query: Search query (min 3 chars)
        location: Location for job search
        sources: Comma-separated list of sources
        num_ads: Number of ads to return
        contract: Contract type filter
        remote: Remote jobs only filter

    Returns:
        StreamingResponse with SSE events
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()]

    params = SearchParams(
        query=query,
        location=location,
        sources=source_list,
        num_ads=num_ads,
        contract=contract,
        remote=remote
    )

    async def event_generator():
        try:
            # Initialize service (would be injected in production)
            service = JobSearchService(repository=request.app.state.job_repository)

            # Send started event
            yield f"data: {json.dumps({'type': 'STARTED', 'query': query, 'total_sources': len(source_list)})}\n\n"

            # Perform search
            jobs = await service.search_jobs(params)

            # Send progress events (simplified for example)
            for i, source in enumerate(source_list):
                yield f"data: {json.dumps({
                    'type': 'PROGRESS',
                    'source': source,
                    'status': 'completed',
                    'progress': (i+1)/len(source_list)*100
                })}\n\n"

            # Send final results
            yield f"data: {json.dumps({
                'type': 'COMPLETED',
                'jobs': [job.dict() for job in jobs],
                'progress': 100
            })}\n\n"

        except JobSearchError as e:
            yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"
            logging.error(f"Job search failed: {e}")
        except Exception as e:
            yield f"data: {json.dumps({'type': 'ERROR', 'message': 'Unexpected error occurred'})}\n\n"
            logging.exception("Unexpected error in job search")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

### Phase 3: Refactorisation Frontend (3-4 jours)

#### Étape 3.1: Créer le store global avec Zustand
```javascript
// frontend/src/features/job-search/store/useJobSearchStore.js
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { jobSearchService } from '../services/jobSearchService';

/**
 * Job Search Store - Centralized state management
 * @typedef {Object} JobSearchState
 * @property {Array} jobs - List of job results
 * @property {boolean} loading - Loading state
 * @property {string|null} error - Error message
 * @property {Object} sourceCounts - Counts by source
 * @property {number} totalResults - Total results count
 * @property {function} searchJobs - Search function
 * @property {function} clearResults - Clear results
 * @property {function} excludeSource - Exclude a source
 */

export const useJobSearchStore = create()(
  devtools(
    (set, get) => ({
      // State
      jobs: [],
      loading: false,
      error: null,
      sourceCounts: {},
      totalResults: 0,
      excludedSources: [],

      // Actions
      searchJobs: async (query, location, sources = ['LinkedIn', 'France Travail', 'Google Jobs']) => {
        try {
          set({ loading: true, error: null, jobs: [], sourceCounts: {}, totalResults: 0 });

          const result = await jobSearchService.search({
            query,
            location,
            sources: sources.filter(s => !get().excludedSources.includes(s))
          });

          set({
            jobs: result.jobs,
            sourceCounts: result.sourceCounts,
            totalResults: result.jobs.length,
            loading: false
          });

          return result;
        } catch (error) {
          set({
            error: error.message || 'Failed to search jobs',
            loading: false
          });
          throw error;
        }
      },

      clearResults: () => {
        set({
          jobs: [],
          sourceCounts: {},
          totalResults: 0,
          error: null
        });
      },

      excludeSource: (source) => {
        const excluded = get().excludedSources.includes(source)
          ? get().excludedSources.filter(s => s !== source)
          : [...get().excludedSources, source];

        set({ excludedSources: excluded });
        return excluded;
      },

      // Selectors
      getActiveJobs: () => {
        const { jobs, excludedSources } = get();
        return jobs.filter(job => !excludedSources.includes(job.source));
      },

      getActiveSourceCounts: () => {
        const { sourceCounts, excludedSources } = get();
        const activeCounts = { ...sourceCounts };
        excludedSources.forEach(source => delete activeCounts[source]);
        return activeCounts;
      }
    }),
    { name: 'JobSearchStore' }
  )
);

// Custom hooks for component usage
export const useJobSearchActions = () => {
  const { searchJobs, clearResults, excludeSource } = useJobSearchStore();
  return { searchJobs, clearResults, excludeSource };
};

export const useJobSearchData = () => {
  const { jobs, loading, error, sourceCounts, totalResults, getActiveJobs, getActiveSourceCounts } = useJobSearchStore();
  return { jobs, loading, error, sourceCounts, totalResults, activeJobs: getActiveJobs(), activeSourceCounts: getActiveSourceCounts() };
};
```

#### Étape 3.2: Créer le service API
```javascript
// frontend/src/features/job-search/services/jobSearchService.js
import axios from 'axios';
import { API_BASE_URL } from '../../../shared/constants/api';

/**
 * Job Search Service - Encapsulates API calls
 */
class JobSearchService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      }
    });
  }

  /**
   * Search jobs using SSE
   * @param {Object} params - Search parameters
   * @param {string} params.query - Search query
   * @param {string} params.location - Location
   * @param {string[]} params.sources - Array of sources
   * @param {number} [params.numAds=100] - Number of results
   * @param {string} [params.contract='CDI'] - Contract type
   * @param {boolean} [params.remote=false] - Remote only
   * @returns {Promise<Object>} - Search results
   */
  async search({ query, location, sources, numAds = 100, contract = 'CDI', remote = false }) {
    const params = new URLSearchParams({
      query,
      location,
      selected_sources: sources.join(','),
      num_ads: numAds.toString(),
      contract,
      remote: remote.toString()
    });

    try {
      const response = await this.api.get(`/api/jobs/stream?${params.toString()}`, {
        responseType: 'stream'
      });

      return this._processSSEStream(response.data);
    } catch (error) {
      this._handleApiError(error);
    }
  }

  /**
   * Process SSE stream and aggregate results
   * @param {ReadableStream} stream - SSE stream
   * @returns {Promise<Object>} - Aggregated results
   */
  async _processSSEStream(stream) {
    return new Promise((resolve, reject) => {
      const reader = stream.getReader();
      const results = {
        jobs: [],
        sourceCounts: {},
        completed: false,
        error: null
      };

      const processEvent = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'STARTED':
              console.log(`[SSE] Search started: ${data.query}`);
              break;

            case 'PROGRESS':
              if (data.source && data.jobs) {
                results.sourceCounts[data.source] = data.jobs.length;
                console.log(`[SSE] ${data.source}: ${data.jobs.length} jobs`);
              }
              break;

            case 'SCORES_UPDATED':
              if (data.jobs) {
                results.jobs = data.jobs;
              }
              break;

            case 'COMPLETED':
              if (data.jobs) {
                results.jobs = data.jobs;
              }
              if (data.source_status) {
                Object.entries(data.source_status).forEach(([source, status]) => {
                  results.sourceCounts[source] = status.jobs_count || 0;
                });
              }
              results.completed = true;
              resolve(results);
              break;

            case 'ERROR':
              results.error = data.message;
              results.completed = true;
              reject(new Error(data.message));
              break;
          }
        } catch (parseError) {
          console.error('[SSE] Error parsing event:', parseError);
        }
      };

      const readStream = () => {
        reader.read().then(({ done, value }) => {
          if (done) {
            if (!results.completed) {
              reject(new Error('Stream closed before completion'));
            }
            return;
          }

          // Process SSE event
          const text = new TextDecoder().decode(value);
          text.split('\n\n').filter(line => line.startsWith('data:')).forEach(line => {
            processEvent({ data: line.substring(6) });
          });

          if (!results.completed) {
            readStream();
          }
        }).catch(reject);
      };

      readStream();
    });
  }

  /**
   * Handle API errors consistently
   * @param {Error} error - API error
   * @throws {Error} - Formatted error
   */
  _handleApiError(error) {
    if (error.response) {
      // Server responded with a status other than 2xx
      const status = error.response.status;
      const data = error.response.data;

      let message = `API Error: ${status}`;
      if (data && data.message) {
        message += ` - ${data.message}`;
      } else if (data && data.detail) {
        message += ` - ${data.detail}`;
      }

      throw new Error(message);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('API Error: No response from server');
    } else {
      // Something happened in setting up the request
      throw new Error(`API Error: ${error.message}`);
    }
  }
}

// Singleton instance
export const jobSearchService = new JobSearchService();
```

#### Étape 3.3: Créer un composant JobSearch propre
```jsx
// frontend/src/features/job-search/components/JobSearch.jsx
import React, { useEffect, useState } from 'react';
import { useJobSearchData, useJobSearchActions } from '../store/useJobSearchStore';
import JobCard from '../../../../shared/components/JobCard';
import SearchFilters from './SearchFilters';
import SourceDashboard from './SourceDashboard';
import LoadingSpinner from '../../../../shared/components/LoadingSpinner';
import ErrorDisplay from '../../../../shared/components/ErrorDisplay';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * JobSearch Component - Main job search interface
 */
const JobSearch = () => {
  const { jobs, loading, error, activeSourceCounts, totalResults } = useJobSearchData();
  const { searchJobs, clearResults } = useJobSearchActions();
  const [searchQuery, setSearchQuery] = useState('');
  const [location, setLocation] = useState('Paris, France');

  // Auto-search when query changes (debounced in real app)
  useEffect(() => {
    if (searchQuery.length > 2) {
      const timer = setTimeout(() => {
        searchJobs(searchQuery, location);
      }, 500);

      return () => clearTimeout(timer);
    } else {
      clearResults();
    }
  }, [searchQuery, location, searchJobs]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchJobs(searchQuery, location);
    }
  };

  return (
    <div className="job-search-container max-w-6xl mx-auto p-4">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Recherche d'Emploi Intelligente</h1>

      <div className="mb-6">
        <SearchFilters
          query={searchQuery}
          setQuery={setSearchQuery}
          location={location}
          setLocation={setLocation}
          onSearch={handleSearch}
        />
      </div>

      {/* Source Dashboard */}
      {Object.keys(activeSourceCounts).length > 0 && (
        <div className="mb-6">
          <SourceDashboard sourceCounts={activeSourceCounts} totalResults={totalResults} />
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-12">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Recherche en cours sur {Object.keys(activeSourceCounts).length} sources...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mb-6">
          <ErrorDisplay
            message={error}
            onRetry={() => searchJobs(searchQuery, location)}
          />
        </div>
      )}

      {/* Empty State */}
      {!loading && jobs.length === 0 && searchQuery.length > 2 && (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">Aucun résultat trouvé pour "{searchQuery}"</p>
          <button
            onClick={() => searchJobs(searchQuery, location)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
          >
            Réessayer
          </button>
        </div>
      )}

      {/* Results */}
      {jobs.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              {totalResults} résultat{totalResults > 1 ? 's' : ''} trouvé{totalResults > 1 ? 's' : ''}
            </h2>
            <div className="text-sm text-gray-500">
              {Object.keys(activeSourceCounts).length} source{Object.keys(activeSourceCounts).length > 1 ? 's' : ''} active{Object.keys(activeSourceCounts).length > 1 ? 's' : ''}
            </div>
          </div>

          <AnimatePresence>
            {jobs.map((job, index) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <JobCard job={job} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

export default React.memo(JobSearch);
```

---

## 📜 Prompts de Refactorisation Complets

### Prompt 1: Configuration initiale du projet
```bash
# 1. Mettre à jour les dépendances backend
pip install --upgrade fastapi uvicorn pydantic python-dotenv inject slowapi httpx scikit-learn

# 2. Installer les outils de développement
pip install --upgrade pytest pytest-asyncio black isort mypy

# 3. Configurer le linting backend
echo "[tool.black]
line-length = 88
target-version = ['py310']
include = '\\.pyi?$'
exclude = '''
/(
    \\.git
  | \\.hg
  | \\.mypy_cache
  | \\.tox
  | \\.venv
  | _build
  | buck-out
  | build
  | dist
)/
''' > backend/pyproject.toml

# 4. Configurer TypeScript pour le frontend
npx tsc --init --jsx react --esModuleInterop true --strict true --skipLibCheck true --outDir dist --rootDir src

# 5. Ajouter les scripts package.json
echo '{
  "scripts": {
    "start": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx",
    "test": "vitest run",
    "format": "prettier --write .",
    "prepare": "husky install"
  }
}' >> frontend/package.json
```

### Prompt 2: Refactorisation du backend étape par étape
```python
# Étape 1: Créer le fichier de configuration centralisée
# backend/app/config/settings.py
from pydantic import BaseSettings, AnyHttpUrl
from typing import List, Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:5173,http://localhost:3000"
    SCRAPER_MAX_WORKERS: int = 30
    SCRAPER_TIMEOUT: float = 6.0

    # AI Providers
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_URL: Optional[AnyHttpUrl] = "http://localhost:11434"
    SERPAPI_KEY: Optional[str] = None

    # Database (future)
    DATABASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate(self):
        """Validate configuration and return service status"""
        services = {
            "groq_configured": bool(self.GROQ_API_KEY),
            "gemini_configured": bool(self.GEMINI_API_KEY),
            "ollama_configured": bool(self.OLLAMA_URL),
            "database_configured": bool(self.DATABASE_URL)
        }
        return services

# Étape 2: Mettre à jour main.py pour utiliser la nouvelle structure
# backend/app/main.py
from fastapi import FastAPI
from backend.app.config.settings import Settings
from backend.app.infrastructure.api.routes import jobs_router
from backend.app.infrastructure.api.routes import health_router
from backend.app.infrastructure.api.routes import ai_router

# Initialize settings
settings = Settings()

# Create app
app = FastAPI(
    title="FindMyJobAI API",
    description="Job search API with AI-powered features",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Include routers
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])

# Store settings in app state for dependency injection
app.state.settings = settings

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

### Prompt 3: Migration frontend vers TypeScript
```typescript
// 1. Convertir un composant simple en TypeScript
// frontend/src/shared/components/JobCard.tsx
import React from 'react';
import { motion } from 'framer-motion';

interface JobCardProps {
  job: {
    id: string;
    title: string;
    company: string;
    location: string;
    source: string;
    description: string;
    posted_date?: string;
    salary?: number | string;
    contract_type?: string;
    url?: string;
    pertinence_score?: number;
  };
  onSave?: (jobId: string) => void;
  isSaved?: boolean;
}

const JobCard: React.FC<JobCardProps> = ({ job, onSave, isSaved = false }) => {
  const handleSaveClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSave?.(job.id);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-lg text-gray-800">{job.title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full">
            {job.source}
          </span>
          {onSave && (
            <button
              onClick={handleSaveClick}
              className="p-1 text-gray-400 hover:text-yellow-500 transition"
              aria-label={isSaved ? "Retirer des favoris" : "Ajouter aux favoris"}
            >
              {isSaved ? '⭐' : '☆'}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
        <span className="font-medium">{job.company}</span>
        <span>•</span>
        <span>{job.location}</span>
        {job.posted_date && (
          <>
            <span>•</span>
            <span>{new Date(job.posted_date).toLocaleDateString()}</span>
          </>
        )}
      </div>

      <p className="text-gray-700 text-sm mb-3 line-clamp-2">
        {job.description}
      </p>

      <div className="flex flex-wrap gap-2 mb-3">
        {job.salary && (
          <span className="text-sm bg-green-100 text-green-700 px-2 py-1 rounded">
            {typeof job.salary === 'number'
              ? `${Math.round(job.salary / 1000)}k€`
              : job.salary}
          </span>
        )}
        {job.contract_type && (
          <span className="text-sm bg-purple-100 text-purple-700 px-2 py-1 rounded">
            {job.contract_type}
          </span>
        )}
        {job.pertinence_score && (
          <span className="text-sm bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
            ✓ {Math.round(job.pertinence_score * 100)}% pertinent
          </span>
        )}
      </div>

      {job.url && (
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 text-sm font-medium inline-flex items-center gap-1"
        >
          Voir l'offre <span className="text-xs">↗</span>
        </a>
      )}
    </motion.div>
  );
};

export default React.memo(JobCard);
```

### Prompt 4: Mise en place des tests unitaires
```bash
# Backend: Configuration pytest
echo "[tool.pytest.ini_options]
pythonpath = .
testpaths = [
    "tests",
]
asyncio_mode = "auto"
log_cli = true
log_cli_level = "INFO"
log_cli_format = "%(asctime)s [%(levelname)s] %(message)s"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"

[tool.coverage.run]
source = ["app"]
omit = [
    "app/main.py",
    "app/config/*",
    "*__init__.py",
    "tests/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstractmethod"
]" > backend/pyproject.toml

# Frontend: Configuration Vitest
echo "import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.js',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'dist/**',
        '.{js,jsx,ts,tsx}',
        '**/*.d.ts',
        'tests/**',
        'mock**',
        '**/vite-env.d.ts'
      ]
    }
  }
});" > frontend/vite.config.test.js
```

---

## 🎯 Bonnes Pratiques et Patterns

### Principes Architecturaux Appliqués

1. **SOLID Principles**
   - Single Responsibility: Chaque classe/composant a une seule raison de changer
   - Open/Closed: Les modules sont ouverts à l'extension mais fermés à la modification
   - Liskov Substitution: Les interfaces sont bien définies et substituables
   - Interface Segregation: Les interfaces sont spécifiques aux clients
   - Dependency Inversion: Dépendance aux abstractions, pas aux implémentations

2. **Clean Architecture**
   - Séparation claire entre couches (UI → Use Cases → Domain → Infrastructure)
   - Dépendances pointent toujours vers l'intérieur
   - Logique métier indépendante des frameworks

3. **Feature-First Organization**
   - Organisation par fonctionnalités plutôt que par type technique
   - Meilleure cohésion et moindre couplage
   - Plus facile à maintenir et faire évoluer

### Patterns Utilisés

1. **Dependency Injection**
   ```python
   # Exemple backend
   def get_job_repository() -> JobRepositoryInterface:
       if settings.USE_MOCK_REPO:
           return MockJobRepository()
       return RealJobRepository()

   app.state.job_repository = get_job_repository()
   ```

2. **Repository Pattern**
   ```typescript
   // Exemple frontend
   interface JobRepository {
     findAll: () => Promise<Job[]>;
     findById: (id: string) => Promise<Job | null>;
     save: (job: Job) => Promise<Job>;
   }
   ```

3. **Observer Pattern (SSE)**
   ```javascript
   // Gestion propre des événements SSE
   const eventSource = new EventSource(url);
   eventSource.onmessage = (event) => {
     const data = JSON.parse(event.data);
     dispatchEvent({ type: data.type, payload: data });
   };
   ```

4. **Strategy Pattern**
   ```python
   # Différentes stratégies de scoring
   class ScoringStrategy(ABC):
       @abstractmethod
       def score(self, jobs: List[Job], cv_data: dict) -> List[Job]:
           pass

   class TFIDFScoring(ScoringStrategy): ...
   class AIScoring(ScoringStrategy): ...
   ```

---

## 📌 Recommandations Finales

1. **Prioriser la migration par étapes** :
   - Commencer par le backend (plus facile à tester)
   - Puis migrer le frontend composant par composant
   - Maintenir les fonctionnalités existantes pendant la transition

2. **Mettre en place une CI/CD solide** :
   ```yaml
   # Exemple GitHub Actions
   name: CI/CD Pipeline

   on: [push, pull_request]

   jobs:
     backend-test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v4
         - run: pip install -r requirements.txt
         - run: pytest --cov=app --cov-report=xml

     frontend-test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v3
         - run: npm install
         - run: npm run lint
         - run: npm test

     deploy:
       needs: [backend-test, frontend-test]
       if: github.ref == 'refs/heads/main'
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - run: echo "Deploy to production..."
   ```

3. **Documenter chaque étape** :
   - Garder un journal des changements (CHANGELOG.md)
   - Documenter les décisions architecturales (ADR)
   - Mettre à jour la documentation technique

4. **Former l'équipe** :
   - Session sur Clean Architecture et SOLID
   - Atelier sur TypeScript pour le frontend
   - Bonnes pratiques de tests unitaires

Cette refactorisation transformera votre application en une architecture professionnelle, maintenable et scalable, tout en minimisant les risques pendant la transition.