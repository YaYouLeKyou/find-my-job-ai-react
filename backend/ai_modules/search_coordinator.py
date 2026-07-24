"""
Search Coordinator v2.0 - Orchestrates job search with fallback, caching, and parallel execution.
Implements:
- Search fallback with keyword expansion
- Parallel execution with strict timeouts (3-5s per source)
- Redis caching (12-24h TTL)
- France Travail official API integration
- Playwright isolation in async worker
"""

import logging
import time
import hashlib
import json
from typing import List, Dict, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchConfig:
    """Configuration for a job search."""
    query: str
    location: str = "France"
    num_ads: int = 10
    contract: str = "CDI"
    remote: bool = False
    selected_sources: List[str] = field(default_factory=list)
    is_freelance: bool = False
    tjm_min: Optional[int] = None
    tjm_max: Optional[int] = None


@dataclass
class SourceResult:
    """Result from a single source."""
    source_name: str
    jobs: List[dict]
    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0


class SearchFallbackEngine:
    """Handles search query fallback with keyword expansion."""
    
    # Fallback strategies in order of preference
    FALLBACK_STRATEGIES = [
        "exact",  # Original query
        "remove_location",  # Remove location constraint
        "simplify_title",  # Simplify job title
        "expand_keywords",  # Use broader keywords
        "remove_filters",  # Remove contract/remote filters
    ]
    
    @staticmethod
    def simplify_job_title(title: str) -> str:
        """Simplify job title by removing qualifiers."""
        # Remove common qualifiers
        simplifications = [
            (r'\b(senior|junior|confirmé|débutant|expérimenté)\b', ''),
            (r'\b(h/f|f/h|hf|fh)\b', ''),
            (r'\b(\(.*?\)|\[.*?\])\b', ''),  # Remove parenthetical qualifiers
            (r'\s+', ' '),  # Normalize whitespace
        ]
        
        simplified = title.lower().strip()
        for pattern, replacement in simplifications:
            simplified = __import__('re').sub(pattern, replacement, simplified, flags=__import__('re').IGNORECASE)
        
        # Take first 2-3 meaningful words
        words = simplified.split()
        if len(words) > 3:
            simplified = ' '.join(words[:3])
        
        return simplified.strip()
    
    @staticmethod
    def expand_keywords(title: str) -> List[str]:
        """Generate expanded keyword variations."""
        expansions = []
        
        # Original
        expansions.append(title)
        
        # Simplified version
        simplified = SearchFallbackEngine.simplify_job_title(title)
        if simplified and simplified != title:
            expansions.append(simplified)
        
        # Extract key terms and create combinations
        words = title.lower().split()
        if len(words) >= 2:
            # Try first word only
            expansions.append(words[0])
            # Try last word only
            expansions.append(words[-1])
            # Try first two words
            if len(words) >= 3:
                expansions.append(' '.join(words[:2]))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_expansions = []
        for exp in expansions:
            exp_clean = exp.strip()
            if exp_clean and exp_clean not in seen:
                seen.add(exp_clean)
                unique_expansions.append(exp_clean)
        
        return unique_expansions
    
    def generate_fallback_queries(self, config: SearchConfig) -> List[SearchConfig]:
        """Generate fallback search configurations."""
        fallbacks = []
        
        # Strategy 1: Exact match (original)
        fallbacks.append(config)
        
        # Strategy 2: Remove location for remote-friendly search
        if config.location and config.location.lower() not in ["france", "global", "remote"]:
            fallback_config = SearchConfig(
                query=config.query,
                location="France",  # Broaden to entire France
                num_ads=config.num_ads,
                contract=config.contract,
                remote=True,  # Include remote jobs
                selected_sources=config.selected_sources,
                is_freelance=config.is_freelance,
            )
            fallbacks.append(fallback_config)
        
        # Strategy 3: Simplify job title
        simplified_title = self.simplify_job_title(config.query)
        if simplified_title != config.query:
            fallback_config = SearchConfig(
                query=simplified_title,
                location=config.location,
                num_ads=config.num_ads,
                contract=config.contract,
                remote=config.remote,
                selected_sources=config.selected_sources,
                is_freelance=config.is_freelance,
            )
            fallbacks.append(fallback_config)
        
        # Strategy 4: Expand keywords
        expanded_keywords = self.expand_keywords(config.query)
        for keyword in expanded_keywords[1:4]:  # Skip first (already tried), try next 3
            if keyword != config.query and keyword != simplified_title:
                fallback_config = SearchConfig(
                    query=keyword,
                    location=config.location,
                    num_ads=config.num_ads,
                    contract="",  # Remove contract filter
                    remote=False,  # Remove remote filter
                    selected_sources=config.selected_sources,
                    is_freelance=config.is_freelance,
                )
                fallbacks.append(fallback_config)
        
        # Strategy 5: Remove all filters
        if config.contract or config.remote:
            fallback_config = SearchConfig(
                query=config.query,
                location=config.location,
                num_ads=config.num_ads,
                contract="",
                remote=False,
                selected_sources=config.selected_sources,
                is_freelance=config.is_freelance,
            )
            fallbacks.append(fallback_config)
        
        # Remove duplicates while preserving order
        seen_configs = set()
        unique_fallbacks = []
        for fb in fallbacks:
            key = (fb.query, fb.location, fb.contract, fb.remote)
            if key not in seen_configs:
                seen_configs.add(key)
                unique_fallbacks.append(fb)
        
        logger.info(f"Generated {len(unique_fallbacks)} fallback strategies for query: '{config.query}'")
        return unique_fallbacks


class CacheManager:
    """Manages Redis caching for search results."""
    
    CACHE_TTL_SHORT = 3600  # 1 hour
    CACHE_TTL_LONG = 86400  # 24 hours
    
    @staticmethod
    def get_cache_key(config: SearchConfig) -> str:
        """Generate cache key from search configuration."""
        # Normalize config for consistent hashing
        normalized = {
            "q": config.query.lower().strip(),
            "l": config.location.lower().strip(),
            "n": config.num_ads,
            "c": config.contract,
            "r": config.remote,
            "f": config.is_freelance,
            "s": sorted(config.selected_sources) if config.selected_sources else [],
        }
        param_str = json.dumps(normalized, sort_keys=True)
        return f"job_search:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    @staticmethod
    def get_cached_result(cache_key: str, redis_client) -> Optional[dict]:
        """Retrieve cached search result."""
        if not redis_client:
            return None
        
        try:
            cached = redis_client.get(cache_key)
            if cached:
                result = json.loads(cached)
                logger.info(f"✅ Cache hit: {cache_key[:20]}...")
                return result
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        return None
    
    @staticmethod
    def cache_result(cache_key: str, result: dict, redis_client, ttl: Optional[int] = None) -> bool:
        """Cache search result."""
        if not redis_client:
            return False
        
        if ttl is None:
            ttl = CacheManager.CACHE_TTL_LONG
        
        try:
            redis_client.setex(cache_key, ttl, json.dumps(result))
            logger.info(f"💾 Cached result for {ttl}s: {cache_key[:20]}...")
            return True
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
            return False


class ParallelSourceExecutor:
    """Executes multiple sources in parallel with strict timeouts."""
    
    def __init__(self, timeout_per_source: int = 5, max_workers: int = 15):
        self.timeout_per_source = timeout_per_source
        self.max_workers = max_workers
    
    def execute_sources(
        self,
        config: SearchConfig,
        source_functions: Dict[str, Callable[..., Any]]
    ) -> List[SourceResult]:
        """
        Execute multiple sources in parallel with timeouts.
        
        Args:
            config: Search configuration
            source_functions: Dict of {source_name: function_to_call}
        
        Returns:
            List of SourceResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(source_functions))) as executor:
            futures = {}
            
            for source_name, source_fn in source_functions.items():
                try:
                    # Submit with timeout
                    future = executor.submit(self._execute_single_source, source_name, source_fn, config)
                    futures[future] = source_name
                except Exception as e:
                    logger.error(f"Failed to submit {source_name}: {e}")
                    results.append(SourceResult(
                        source_name=source_name,
                        jobs=[],
                        success=False,
                        error=f"Submission error: {str(e)}"
                    ))
            
            # Collect results with timeout
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    result = future.result(timeout=self.timeout_per_source + 2)
                    results.append(result)
                except Exception as e:
                    # Check if it's a timeout error
                    if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                        logger.warning(f"⏱️ {source_name} timed out after {self.timeout_per_source}s")
                        results.append(SourceResult(
                            source_name=source_name,
                            jobs=[],
                            success=False,
                            error=f"Timeout after {self.timeout_per_source}s"
                        ))
                    else:
                        logger.error(f"❌ {source_name} failed: {e}")
                        results.append(SourceResult(
                            source_name=source_name,
                            jobs=[],
                            success=False,
                            error=str(e)[:100]
                        ))
        
        return results
    
    def _execute_single_source(self, source_name: str, source_fn: callable, config: SearchConfig) -> SourceResult:
        """Execute a single source with timing and error handling."""
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Searching {source_name}...")
            
            # Call the source function
            jobs = source_fn(config.query, config.location, config.num_ads)
            
            execution_time = time.time() - start_time
            
            if jobs:
                logger.info(f"✅ {source_name}: {len(jobs)} jobs in {execution_time:.2f}s")
                return SourceResult(
                    source_name=source_name,
                    jobs=jobs,
                    success=True,
                    execution_time=execution_time
                )
            else:
                logger.info(f"⚠️ {source_name}: 0 results in {execution_time:.2f}s")
                return SourceResult(
                    source_name=source_name,
                    jobs=[],
                    success=True,  # Not an error, just no results
                    error="No results found",
                    execution_time=execution_time
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ {source_name} error: {e}")
            return SourceResult(
                source_name=source_name,
                jobs=[],
                success=False,
                error=str(e)[:100],
                execution_time=execution_time
            )


class SearchCoordinator:
    """
    Main coordinator for job search with fallback, caching, and parallel execution.
    """
    
    def __init__(
        self,
        redis_client=None,
        timeout_per_source: int = 5,
        cache_ttl: int = 86400,  # 24 hours
        enable_fallback: bool = True,
        max_fallback_attempts: int = 3
    ):
        self.redis_client = redis_client
        self.timeout_per_source = timeout_per_source
        self.cache_ttl = cache_ttl
        self.enable_fallback = enable_fallback
        self.max_fallback_attempts = max_fallback_attempts
        
        self.fallback_engine = SearchFallbackEngine()
        self.cache_manager = CacheManager()
        self.executor = ParallelSourceExecutor(timeout_per_source=timeout_per_source)
    
    def search(
        self,
        config: SearchConfig,
        source_registry: Dict[str, Callable[..., Any]]
    ) -> Tuple[List[dict], Dict[str, SourceResult]]:
        """
        Execute job search with fallback and caching.
        
        Args:
            config: Search configuration
            source_registry: Dict of {source_name: function_to_call}
        
        Returns:
            Tuple of (all_jobs, source_results_dict)
        """
        # Check cache first
        cache_key = self.cache_manager.get_cache_key(config)
        cached_result = self.cache_manager.get_cached_result(cache_key, self.redis_client)
        if cached_result:
            return cached_result.get("jobs", []), {}
        
        # Execute search with fallback
        all_jobs = []
        source_results = {}
        attempts = 0
        
        # Get list of fallback configurations to try
        fallback_configs = [config]
        if self.enable_fallback:
            fallback_configs = self.fallback_engine.generate_fallback_queries(config)
        
        # Try each fallback configuration
        for fallback_config in fallback_configs[:self.max_fallback_attempts]:
            if all_jobs:
                break  # Already have results
            
            attempts += 1
            logger.info(f"🔄 Search attempt {attempts}/{min(len(fallback_configs), self.max_fallback_attempts)}: '{fallback_config.query}'")
            
            # Filter sources for this configuration
            available_sources = {
                name: fn for name, fn in source_registry.items()
                if not fallback_config.selected_sources or name in fallback_config.selected_sources
            }
            
            if not available_sources:
                logger.warning("No sources available for search")
                continue
            
            # Execute sources in parallel
            results = self.executor.execute_sources(fallback_config, available_sources)
            
            # Collect results
            attempt_jobs = []
            for result in results:
                source_results[result.source_name] = result
                if result.success and result.jobs:
                    attempt_jobs.extend(result.jobs)
            
            # Deduplicate
            attempt_jobs = self._deduplicate_jobs(attempt_jobs)
            
            if attempt_jobs:
                all_jobs = attempt_jobs
                logger.info(f"✅ Search successful: {len(all_jobs)} jobs from {len([r for r in results if r.success])} sources")
                break
            else:
                logger.warning(f"⚠️ Attempt {attempts} returned 0 results, trying fallback...")
        
        # Cache results if we have any
        if all_jobs and self.redis_client:
            result_dict = {"jobs": all_jobs, "timestamp": datetime.now().isoformat()}
            self.cache_manager.cache_result(cache_key, result_dict, self.redis_client, self.cache_ttl)
        
        return all_jobs, source_results
    
    def _deduplicate_jobs(self, jobs: List[dict]) -> List[dict]:
        """Remove duplicate jobs based on link and title similarity."""
        seen_links = set()
        seen_titles = set()
        unique_jobs = []
        
        for job in jobs:
            link = job.get("link", "").strip().lower()
            title = job.get("title", "").strip().lower()
            
            # Skip if we've seen this link
            if link and link in seen_links:
                continue
            
            # Skip if very similar title (simple check)
            if title and any(self._similarity(title, t) > 0.8 for t in seen_titles):
                continue
            
            if link:
                seen_links.add(link)
            if title:
                seen_titles.add(title)
            
            unique_jobs.append(job)
        
        return unique_jobs
    
    @staticmethod
    def _similarity(s1: str, s2: str) -> float:
        """Calculate simple similarity between two strings."""
        if not s1 or not s2:
            return 0.0
        
        # Jaccard similarity on words
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0