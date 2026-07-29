"""
AI Provider Architecture - Core Domain Layer
Advanced AI orchestration with BYOK, fallback, and caching strategies
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel
import json
import hashlib
from datetime import datetime, timedelta
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProviderType(Enum):
    """Supported AI providers"""
    GROQ = "groq"
    GEMINI = "gemini"

class AITaskType(Enum):
    """Types of AI tasks"""
    CV_ANALYSIS = "cv_analysis"
    JOB_MATCHING = "job_matching"
    SEARCH_OPTIMIZATION = "search_optimization"
    PROFILE_ANALYSIS = "profile_analysis"

class AIError(BaseModel):
    """Standardized AI error response"""
    error_type: str
    message: str
    provider: Optional[str] = None
    status_code: Optional[int] = None
    suggestion: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class AICacheStrategy(Enum):
    """Cache strategies for different AI tasks"""
    NO_CACHE = "no_cache"
    SHORT_TERM = "short_term"  # 5 minutes
    MEDIUM_TERM = "medium_term"  # 1 hour
    LONG_TERM = "long_term"  # 24 hours

class AICacheKey(BaseModel):
    """Cache key structure"""
    task_type: AITaskType
    user_id: str
    query_hash: str
    parameters_hash: str

    def generate_key(self) -> str:
        """Generate a unique cache key"""
        key_data = f"{self.task_type.value}:{self.user_id}:{self.query_hash}:{self.parameters_hash}"
        return hashlib.sha256(key_data.encode()).hexdigest()

class AIResponse(BaseModel):
    """Standardized AI response format"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {
        "provider": None,
        "model": None,
        "tokens_used": 0,
        "cache_hit": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    error: Optional[AIError] = None

class AIProviderInterface(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    async def analyze_cv(self, cv_text: str, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        """Analyze CV content and extract structured information"""

    @abstractmethod
    async def match_jobs(self, query: str, jobs: List[Dict], user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        """Match jobs based on query and user preferences"""

    @abstractmethod
    async def optimize_search(self, search_query: str, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        """Optimize search query for better results"""

    @abstractmethod
    async def analyze_profile(self, profile_data: Dict, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        """Analyze user profile for matching purposes"""

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and capabilities"""

class GroqProvider(AIProviderInterface):
    """Concrete implementation for Groq AI provider"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.default_model = "llama-3-70b-8192"

    async def _call_groq_api(self, endpoint: str, payload: Dict, task_type: AITaskType) -> Dict[str, Any]:
        """Internal method to call Groq API"""
        # In a real implementation, this would make an actual HTTP call
        # For this architecture, we'll simulate the response
        import asyncio
        await asyncio.sleep(0.3)  # Simulate network delay

        # Simulate rate limiting (10% chance for demo purposes)
        import random
        if random.random() < 0.1:
            raise Exception("{\"error\": {\"type\": \"rate_limit_exceeded\", \"message\": \"Quota exceeded\", \"status_code\": 429}}")

        # Return mock response based on task type
        if task_type == AITaskType.CV_ANALYSIS:
            return {
                "skills": ["Python", "Django", "SQL"],
                "experience_years": 5,
                "job_title": "Senior Python Developer",
                "summary": "Experienced Python developer with 5 years in web applications"
            }
        elif task_type == AITaskType.JOB_MATCHING:
            return {
                "matches": [
                    {"job_id": "1", "score": 0.95, "reason": "Perfect skill match"},
                    {"job_id": "2", "score": 0.87, "reason": "Good experience match"}
                ]
            }
        elif task_type == AITaskType.SEARCH_OPTIMIZATION:
            return {
                "optimized_query": f"enhanced: {payload.get('query', '')}",
                "keywords": ["senior", "python", "backend"]
            }
        else:
            return {"result": "success"}

    async def analyze_cv(self, cv_text: str, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_groq_api(
                "/chat/completions",
                {"text": cv_text, **task_params},
                AITaskType.CV_ANALYSIS
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GROQ.value,
                    "model": self.default_model,
                    "tokens_used": len(cv_text) // 4,  # Rough estimate
                    "cache_hit": False
                }
            )
        except Exception as e:
            error_data = json.loads(str(e))
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GROQ.value},
                error=AIError(
                    error_type=error_data["error"]["type"],
                    message=error_data["error"]["message"],
                    provider=AIProviderType.GROQ.value,
                    status_code=error_data["error"]["status_code"],
                    suggestion="Please add your Gemini API key to continue"
                )
            )

    async def match_jobs(self, query: str, jobs: List[Dict], user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_groq_api(
                "/chat/completions",
                {"query": query, "jobs": jobs, **task_params},
                AITaskType.JOB_MATCHING
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GROQ.value,
                    "model": self.default_model,
                    "tokens_used": len(query) + sum(len(job.get("description", "")) for job in jobs),
                    "cache_hit": False
                }
            )
        except Exception as e:
            error_data = json.loads(str(e))
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GROQ.value},
                error=AIError(
                    error_type=error_data["error"]["type"],
                    message=error_data["error"]["message"],
                    provider=AIProviderType.GROQ.value,
                    status_code=error_data["error"]["status_code"],
                    suggestion="Please add your Gemini API key to continue"
                )
            )

    async def optimize_search(self, search_query: str, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_groq_api(
                "/chat/completions",
                {"query": search_query, **task_params},
                AITaskType.SEARCH_OPTIMIZATION
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GROQ.value,
                    "model": self.default_model,
                    "tokens_used": len(search_query) * 2,
                    "cache_hit": False
                }
            )
        except Exception as e:
            error_data = json.loads(str(e))
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GROQ.value},
                error=AIError(
                    error_type=error_data["error"]["type"],
                    message=error_data["error"]["message"],
                    provider=AIProviderType.GROQ.value,
                    status_code=error_data["error"]["status_code"],
                    suggestion="Please add your Gemini API key to continue"
                )
            )

    async def analyze_profile(self, profile_data: Dict, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_groq_api(
                "/chat/completions",
                {"profile": profile_data, **task_params},
                AITaskType.PROFILE_ANALYSIS
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GROQ.value,
                    "model": self.default_model,
                    "tokens_used": sum(len(str(v)) for v in profile_data.values()),
                    "cache_hit": False
                }
            )
        except Exception as e:
            error_data = json.loads(str(e))
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GROQ.value},
                error=AIError(
                    error_type=error_data["error"]["type"],
                    message=error_data["error"]["message"],
                    provider=AIProviderType.GROQ.value,
                    status_code=error_data["error"]["status_code"],
                    suggestion="Please add your Gemini API key to continue"
                )
            )

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "name": "Groq",
            "model": self.default_model,
            "capabilities": ["cv_analysis", "job_matching", "search_optimization", "profile_analysis"],
            "rate_limits": {
                "requests_per_minute": 60,
                "tokens_per_minute": 150000
            }
        }

class GeminiProvider(AIProviderInterface):
    """Concrete implementation for Gemini AI provider"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.default_model = "gemini-1.5-pro-latest"

    async def _call_gemini_api(self, endpoint: str, payload: Dict, task_type: AITaskType) -> Dict[str, Any]:
        """Internal method to call Gemini API"""
        # In a real implementation, this would make an actual HTTP call
        # For this architecture, we'll simulate the response
        import asyncio
        await asyncio.sleep(0.2)  # Simulate network delay (Gemini is faster)

        # Return mock response based on task type
        if task_type == AITaskType.CV_ANALYSIS:
            return {
                "skills": ["Python", "Django", "SQL", "Cloud"],
                "experience_years": 5,
                "job_title": "Senior Python Developer",
                "summary": "Experienced Python developer with cloud expertise",
                "certifications": ["AWS Certified"]
            }
        elif task_type == AITaskType.JOB_MATCHING:
            return {
                "matches": [
                    {"job_id": "1", "score": 0.97, "reason": "Perfect skill and experience match"},
                    {"job_id": "2", "score": 0.92, "reason": "Excellent profile match"},
                    {"job_id": "3", "score": 0.88, "reason": "Good overall match"}
                ],
                "suggestions": ["Consider remote positions", "Look for cloud-focused roles"]
            }
        elif task_task == AITaskType.SEARCH_OPTIMIZATION:
            return {
                "optimized_query": f"enhanced: {payload.get('query', '')}",
                "keywords": ["senior", "python", "backend", "cloud"],
                "synonyms": ["developer", "engineer", "programmer"]
            }
        else:
            return {"result": "success", "quality": "high"}

    async def analyze_cv(self, cv_text: str, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_gemini_api(
                "/models/gemini-1.5-pro-latest:generateContent",
                {"text": cv_text, **task_params},
                AITaskType.CV_ANALYSIS
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GEMINI.value,
                    "model": self.default_model,
                    "tokens_used": len(cv_text) // 4,
                    "cache_hit": False,
                    "quality": "high"
                }
            )
        except Exception as e:
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GEMINI.value},
                error=AIError(
                    error_type="api_error",
                    message=str(e),
                    provider=AIProviderType.GEMINI.value,
                    status_code=500,
                    suggestion="Check your Gemini API key and try again"
                )
            )

    async def match_jobs(self, query: str, jobs: List[Dict], user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_gemini_api(
                "/models/gemini-1.5-pro-latest:generateContent",
                {"query": query, "jobs": jobs, **task_params},
                AITaskType.JOB_MATCHING
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GEMINI.value,
                    "model": self.default_model,
                    "tokens_used": len(query) + sum(len(job.get("description", "")) for job in jobs),
                    "cache_hit": False,
                    "quality": "high"
                }
            )
        except Exception as e:
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GEMINI.value},
                error=AIError(
                    error_type="api_error",
                    message=str(e),
                    provider=AIProviderType.GEMINI.value,
                    status_code=500,
                    suggestion="Check your Gemini API key and try again"
                )
            )

    async def optimize_search(self, search_query: str, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_gemini_api(
                "/models/gemini-1.5-pro-latest:generateContent",
                {"query": search_query, **task_params},
                AITaskType.SEARCH_OPTIMIZATION
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GEMINI.value,
                    "model": self.default_model,
                    "tokens_used": len(search_query) * 2,
                    "cache_hit": False,
                    "quality": "high"
                }
            )
        except Exception as e:
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GEMINI.value},
                error=AIError(
                    error_type="api_error",
                    message=str(e),
                    provider=AIProviderType.GEMINI.value,
                    status_code=500,
                    suggestion="Check your Gemini API key and try again"
                )
            )

    async def analyze_profile(self, profile_data: Dict, user_id: str, task_params: Dict[str, Any]) -> AIResponse:
        try:
            result = await self._call_gemini_api(
                "/models/gemini-1.5-pro-latest:generateContent",
                {"profile": profile_data, **task_params},
                AITaskType.PROFILE_ANALYSIS
            )

            return AIResponse(
                success=True,
                data=result,
                metadata={
                    "provider": AIProviderType.GEMINI.value,
                    "model": self.default_model,
                    "tokens_used": sum(len(str(v)) for v in profile_data.values()),
                    "cache_hit": False,
                    "quality": "high"
                }
            )
        except Exception as e:
            return AIResponse(
                success=False,
                data={},
                metadata={"provider": AIProviderType.GEMINI.value},
                error=AIError(
                    error_type="api_error",
                    message=str(e),
                    provider=AIProviderType.GEMINI.value,
                    status_code=500,
                    suggestion="Check your Gemini API key and try again"
                )
            )

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "name": "Gemini",
            "model": self.default_model,
            "capabilities": ["cv_analysis", "job_matching", "search_optimization", "profile_analysis"],
            "rate_limits": {
                "requests_per_minute": 120,
                "tokens_per_minute": 300000
            },
            "quality": "high",
            "features": ["multi-modal", "long-context", "advanced-reasoning"]
        }

class AIProviderFactory:
    """Factory for creating AI provider instances"""

    @staticmethod
    def create_provider(provider_type: AIProviderType, api_key: str) -> AIProviderInterface:
        """Create appropriate AI provider instance"""
        if provider_type == AIProviderType.GROQ:
            return GroqProvider(api_key)
        elif provider_type == AIProviderType.GEMINI:
            return GeminiProvider(api_key)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

class AICacheManager:
    """Advanced cache manager with multiple strategies"""

    def __init__(self):
        # In production, this would connect to Redis
        # For this architecture, we'll use an in-memory cache
        self.cache = {}
        self.cache_ttl = {
            AICacheStrategy.SHORT_TERM: timedelta(minutes=5),
            AICacheStrategy.MEDIUM_TERM: timedelta(hours=1),
            AICacheStrategy.LONG_TERM: timedelta(hours=24)
        }

    def _generate_cache_key(self, cache_key: AICacheKey) -> str:
        """Generate consistent cache key"""
        return cache_key.generate_key()

    def get_cached_response(self, cache_key: AICacheKey) -> Optional[AIResponse]:
        """Get cached response if available and not expired"""
        key = self._generate_cache_key(cache_key)
        cached_item = self.cache.get(key)

        if cached_item and 'timestamp' in cached_item['metadata']:
            cache_age = datetime.utcnow() - datetime.fromisoformat(cached_item['metadata']['timestamp'])
            strategy = cached_item['metadata'].get('cache_strategy', AICacheStrategy.SHORT_TERM.value)

            if cache_age < self.cache_ttl[AICacheStrategy(strategy)]:
                # Update cache hit metadata
                cached_item['metadata']['cache_hit'] = True
                return AIResponse(**cached_item)
            else:
                # Cache expired, remove it
                self.invalidate_cache(cache_key)

        return None

    def cache_response(self, cache_key: AICacheKey, response: AIResponse, strategy: AICacheStrategy) -> None:
        """Cache AI response with specified strategy"""
        if strategy == AICacheStrategy.NO_CACHE:
            return

        key = self._generate_cache_key(cache_key)
        response_dict = response.dict()
        response_dict['metadata']['cache_strategy'] = strategy.value
        response_dict['metadata']['timestamp'] = datetime.utcnow().isoformat()

        self.cache[key] = response_dict
        logger.info(f"Cached response for key: {key[:8]}... with strategy: {strategy.value}")

    def invalidate_cache(self, cache_key: AICacheKey) -> None:
        """Invalidate cache for specific key"""
        key = self._generate_cache_key(cache_key)
        if key in self.cache:
            del self.cache[key]
            logger.info(f"Invalidated cache for key: {key[:8]}...")

    def clear_all_cache(self) -> None:
        """Clear entire cache (use with caution)"""
        self.cache.clear()
        logger.warning("Cleared entire AI cache")

class AIOrchestrator:
    """Main AI orchestrator with BYOK, fallback, and caching"""

    def __init__(self, default_groq_key: str):
        self.default_groq_key = default_groq_key
        self.cache_manager = AICacheManager()
        self.user_providers = {}  # user_id -> provider_instance

    def set_user_gemini_key(self, user_id: str, gemini_key: str) -> None:
        """Set Gemini key for specific user (BYOK)"""
        if gemini_key and gemini_key.strip():
            self.user_providers[user_id] = AIProviderFactory.create_provider(
                AIProviderType.GEMINI, gemini_key
            )
            logger.info(f"User {user_id} switched to Gemini provider")
        else:
            if user_id in self.user_providers:
                del self.user_providers[user_id]
            logger.info(f"User {user_id} reverted to default Groq provider")

    def get_provider_for_user(self, user_id: str) -> AIProviderInterface:
        """Get appropriate provider for user with fallback logic"""
        # Check if user has custom provider (Gemini)
        if user_id in self.user_providers:
            return self.user_providers[user_id]

        # Use default Groq provider
        return AIProviderFactory.create_provider(AIProviderType.GROQ, self.default_groq_key)

    async def execute_ai_task(
        self,
        user_id: str,
        task_type: AITaskType,
        task_data: Dict[str, Any],
        cache_strategy: AICacheStrategy = AICacheStrategy.SHORT_TERM,
        force_refresh: bool = False
    ) -> AIResponse:
        """
        Execute AI task with caching, BYOK routing, and fallback handling

        Args:
            user_id: User identifier
            task_type: Type of AI task
            task_data: Task-specific data
            cache_strategy: Caching strategy to use
            force_refresh: Bypass cache if True

        Returns:
            AIResponse with results or error
        """
        # Generate cache key
        query_hash = hashlib.md5(json.dumps(task_data).encode()).hexdigest()
        parameters_hash = hashlib.md5(json.dumps({
            "cache_strategy": cache_strategy.value,
            "force_refresh": force_refresh
        }).encode()).hexdigest()

        cache_key = AICacheKey(
            task_type=task_type,
            user_id=user_id,
            query_hash=query_hash,
            parameters_hash=parameters_hash
        )

        # Check cache if not forcing refresh
        if not force_refresh:
            cached_response = self.cache_manager.get_cached_response(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {task_type.value} task")
                return cached_response

        # Get appropriate provider for user
        provider = self.get_provider_for_user(user_id)
        logger.info(f"Using {provider.get_provider_info()['name']} for {task_type.value} task")

        # Execute task based on type
        try:
            if task_type == AITaskType.CV_ANALYSIS:
                response = await provider.analyze_cv(
                    task_data.get("cv_text", ""),
                    user_id,
                    task_data.get("params", {})
                )
            elif task_type == AITaskType.JOB_MATCHING:
                response = await provider.match_jobs(
                    task_data.get("query", ""),
                    task_data.get("jobs", []),
                    user_id,
                    task_data.get("params", {})
                )
            elif task_type == AITaskType.SEARCH_OPTIMIZATION:
                response = await provider.optimize_search(
                    task_data.get("query", ""),
                    user_id,
                    task_data.get("params", {})
                )
            elif task_type == AITaskType.PROFILE_ANALYSIS:
                response = await provider.analyze_profile(
                    task_data.get("profile_data", {}),
                    user_id,
                    task_data.get("params", {})
                )
            else:
                raise ValueError(f"Unsupported task type: {task_type}")

            # Handle Groq rate limiting with fallback suggestion
            if (response.error and
                response.error.status_code == 429 and
                response.error.provider == AIProviderType.GROQ.value):

                logger.warning(f"Groq rate limit exceeded for user {user_id}")
                # Add specific suggestion for frontend
                response.error.suggestion = (
                    "Quota Groq épuisé. Ajoutez votre clé API Gemini personnelle "
                    "dans les paramètres pour continuer avec des quotas plus élevés."
                )

            # Cache successful responses
            if response.success and cache_strategy != AICacheStrategy.NO_CACHE:
                self.cache_manager.cache_response(cache_key, response, cache_strategy)

            return response

        except Exception as e:
            logger.error(f"AI task execution failed: {str(e)}")
            return AIResponse(
                success=False,
                data={},
                error=AIError(
                    error_type="execution_error",
                    message=str(e),
                    provider=provider.get_provider_info()["name"],
                    status_code=500,
                    suggestion="An unexpected error occurred. Please try again."
                )
            )

    def invalidate_cache_for_task(
        self,
        user_id: str,
        task_type: AITaskType,
        task_data: Dict[str, Any]
    ) -> None:
        """Invalidate cache for specific task (cache busting)"""
        query_hash = hashlib.md5(json.dumps(task_data).encode()).hexdigest()
        parameters_hash = hashlib.md5(json.dumps({"default": "params"}).encode()).hexdigest()

        cache_key = AICacheKey(
            task_type=task_type,
            user_id=user_id,
            query_hash=query_hash,
            parameters_hash=parameters_hash
        )

        self.cache_manager.invalidate_cache(cache_key)
        logger.info(f"Cache invalidated for {task_type.value} task")

    def clear_user_cache(self, user_id: str) -> None:
        """Clear all cache entries for specific user"""
        # In a real implementation, we would filter by user_id
        # For this demo, we'll just log the action
        logger.info(f"Clearing cache for user {user_id} (simulated)")

# Agent Implementations
class FindMyFreelanceMissionAgent:
    """Agent for finding freelance missions"""

    def __init__(self, ai_orchestrator: AIOrchestrator):
        self.ai_orchestrator = ai_orchestrator

    async def search_missions(
        self,
        user_id: str,
        skills: List[str],
        tjm_range: tuple,
        remote: bool,
        location: Optional[str] = None,
        force_refresh: bool = False
    ) -> AIResponse:
        """Search for freelance missions matching criteria"""
        task_data = {
            "query": f"Freelance missions for {', '.join(skills)} at {tjm_range[0]}-{tjm_range[1]}€/day",
            "skills": skills,
            "tjm_min": tjm_range[0],
            "tjm_max": tjm_range[1],
            "remote": remote,
            "location": location,
            "params": {
                "match_threshold": 0.85,
                "max_results": 20
            }
        }

        return await self.ai_orchestrator.execute_ai_task(
            user_id=user_id,
            task_type=AITaskType.JOB_MATCHING,
            task_data=task_data,
            cache_strategy=AICacheStrategy.MEDIUM_TERM,
            force_refresh=force_refresh
        )

    def invalidate_search_cache(self, user_id: str, skills: List[str], tjm_range: tuple, remote: bool):
        """Invalidate cache for specific search"""
        task_data = {
            "skills": skills,
            "tjm_min": tjm_range[0],
            "tjm_max": tjm_range[1],
            "remote": remote
        }
        self.ai_orchestrator.invalidate_cache_for_task(
            user_id=user_id,
            task_type=AITaskType.JOB_MATCHING,
            task_data=task_data
        )

class FindMyWorkerAgent:
    """Agent for finding workers/candidates"""

    def __init__(self, ai_orchestrator: AIOrchestrator):
        self.ai_orchestrator = ai_orchestrator

    async def search_workers(
        self,
        user_id: str,
        job_description: str,
        required_skills: List[str],
        contract_type: str,
        location: Optional[str] = None,
        force_refresh: bool = False
    ) -> AIResponse:
        """Search for workers matching job requirements"""
        task_data = {
            "query": job_description,
            "required_skills": required_skills,
            "contract_type": contract_type,
            "location": location,
            "params": {
                "match_threshold": 0.90,
                "max_results": 15,
                "experience_weight": 0.7,
                "skill_weight": 0.3
            }
        }

        return await self.ai_orchestrator.execute_ai_task(
            user_id=user_id,
            task_type=AITaskType.PROFILE_ANALYSIS,
            task_data=task_data,
            cache_strategy=AICacheStrategy.MEDIUM_TERM,
            force_refresh=force_refresh
        )

    def invalidate_search_cache(
        self,
        user_id: str,
        job_description: str,
        required_skills: List[str],
        contract_type: str
    ):
        """Invalidate cache for specific worker search"""
        task_data = {
            "job_description": job_description,
            "required_skills": required_skills,
            "contract_type": contract_type
        }
        self.ai_orchestrator.invalidate_cache_for_task(
            user_id=user_id,
            task_type=AITaskType.PROFILE_ANALYSIS,
            task_data=task_data
        )

# Example usage and testing
async def example_usage():
    """Example of how to use the AI architecture"""

    # Initialize orchestrator with default Groq key
    orchestrator = AIOrchestrator(default_groq_key="default-groq-key-123")

    # Set up agents
    freelance_agent = FindMyFreelanceMissionAgent(orchestrator)
    worker_agent = FindMyWorkerAgent(orchestrator)

    # Example 1: User without Gemini key (uses Groq)
    print("=== User without Gemini key ===")
    response = await freelance_agent.search_missions(
        user_id="user1",
        skills=["Python", "Django"],
        tjm_range=(400, 600),
        remote=True
    )
    print(f"Success: {response.success}")
    if response.error:
        print(f"Error: {response.error.message}")
        if response.error.suggestion:
            print(f"Suggestion: {response.error.suggestion}")

    # Example 2: User adds Gemini key (switches to Gemini)
    print("\n=== User adds Gemini key ===")
    orchestrator.set_user_gemini_key("user1", "user-gemini-key-456")
    response = await freelance_agent.search_missions(
        user_id="user1",
        skills=["Python", "Django"],
        tjm_range=(400, 600),
        remote=True
    )
    print(f"Success: {response.success}")
    print(f"Provider: {response.metadata.get('provider')}")
    print(f"Quality: {response.metadata.get('quality', 'standard')}")

    # Example 3: Worker search
    print("\n=== Worker search ===")
    response = await worker_agent.search_workers(
        user_id="user1",
        job_description="Senior Python developer with cloud experience",
        required_skills=["Python", "AWS", "Docker"],
        contract_type="CDI",
        location="Paris"
    )
    print(f"Success: {response.success}")
    print(f"Matches found: {len(response.data.get('matches', []))}")

    # Example 4: Cache invalidation
    print("\n=== Cache invalidation ===")
    freelance_agent.invalidate_search_cache(
        user_id="user1",
        skills=["Python", "Django"],
        tjm_range=(400, 600),
        remote=True
    )
    print("Cache invalidated for freelance mission search")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())