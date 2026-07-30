"""
Async Aggregator Service
Orchestrates parallel job searches and generates SSE (Server-Sent Events) in real-time
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class SourceResult:
    """Result from a single source."""
    
    def __init__(self, source_name: str, jobs: List[dict], success: bool, error: str = "", execution_time: float = 0):
        self.source_name = source_name
        self.jobs = jobs
        self.success = success
        self.error = error
        self.execution_time = execution_time
    
    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "jobs": self.jobs,
            "success": self.success,
            "error": self.error,
            "execution_time": self.execution_time
        }


class SearchAggregator:
    """
    Orchestrates parallel job searches from multiple sources.
    Uses ThreadPoolExecutor for concurrent execution with timeout.
    """
    
    def __init__(self, max_workers: int = 30, timeout_per_source: float = 6.0):
        self.max_workers = max_workers
        self.timeout_per_source = timeout_per_source
    
    async def search_parallel(
        self,
        sources: Dict[str, Callable],
        query: str,
        location: str,
        limit: int
    ) -> tuple[List[dict], Dict[str, SourceResult]]:
        """
        Search multiple sources in parallel and return results as they complete.
        
        Returns:
            Tuple of (all_jobs, source_results_dict)
        """
        all_jobs = []
        source_results = {}
        source_start_times = {}
        
        logger.info(f"Starting parallel search with {len(sources)} sources")
        
        # Execute all sources in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(len(sources), 8))) as executor:
            future_to_source = {}
            
            for source_name, source_fn in sources.items():
                try:
                    source_start_times[source_name] = time.time()
                    logger.info(f"[SOURCE: {source_name}] ⏱️ Start search for query: \"{query}\"")
                    
                    # Submit task to thread pool
                    future = executor.submit(source_fn, query, location, limit)
                    future_to_source[future] = source_name
                    
                except Exception as e:
                    logger.error(f"[SOURCE: {source_name}] Erreur de soumission: {e}")
                    source_results[source_name] = SourceResult(
                        source_name=source_name,
                        jobs=[],
                        success=False,
                        error=f"Submission error: {str(e)}",
                        execution_time=0
                    )
            
            # Collect results as they complete (NON-BLOQUANT)
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                start_time = source_start_times.get(source_name, time.time())
                
                try:
                    # Wait for result with timeout
                    jobs = future.result(timeout=self.timeout_per_source)
                    duration = time.time() - start_time
                    
                    source_results[source_name] = SourceResult(
                        source_name=source_name,
                        jobs=jobs if jobs else [],
                        success=True,
                        execution_time=round(duration, 2)
                    )
                    
                    all_jobs.extend(jobs)
                    logger.info(f"[SOURCE: {source_name}] ✅ Success: {len(jobs)} jobs found in {duration:.2f}s")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = str(e)
                    
                    # Categorize error
                    if "timeout" in error_msg.lower():
                        logger.error(f"[SOURCE: {source_name}] Timeout (> {self.timeout_per_source}s)")
                    elif "401" in error_msg or "403" in error_msg:
                        logger.error(f"[SOURCE: {source_name}] Quota/Authentification: {error_msg[:100]}")
                    else:
                        logger.error(f"[SOURCE: {source_name}] Erreur: {error_msg[:100]}")
                    
                    logger.info(f"[SOURCE: {source_name}] ❌ Error after {duration:.2f}s: {error_msg[:100]}")
                    
                    source_results[source_name] = SourceResult(
                        source_name=source_name,
                        jobs=[],
                        success=False,
                        error=error_msg[:100],
                        execution_time=round(duration, 2)
                    )
        
        logger.info(f"Search complete: {len(all_jobs)} jobs from {len(source_results)} sources")
        return all_jobs, source_results
    
    async def search_parallel_streaming(
        self,
        sources: Dict[str, Callable],
        query: str,
        location: str,
        limit: int
    ):
        """Search multiple sources in parallel and stream results as they complete.

        Uses asyncio.to_thread + asyncio.wait_for + asyncio.wait(FIRST_COMPLETED)
        to release results the moment a source finishes, instead of waiting for
        every source to converge before emitting a single SSE event.
        """
        all_jobs = []
        source_results = {}
        source_start_times = {}

        logger.info(f"Starting streaming parallel search with {len(sources)} sources")

        pending: Dict[str, asyncio.Task] = {}

        for source_name, source_fn in sources.items():
            try:
                source_start_times[source_name] = time.time()
                logger.info(
                    f"[SOURCE: {source_name}] start search for query: \"{query}\""
                )

                task = asyncio.create_task(
                    asyncio.wait_for(
                        asyncio.to_thread(source_fn, query, location, limit),
                        timeout=self.timeout_per_source,
                    )
                )
                pending[source_name] = task

            except Exception as e:
                logger.error(f"[SOURCE: {source_name}] submission error: {e}")
                result = SourceResult(
                    source_name=source_name,
                    jobs=[],
                    success=False,
                    error=f"Submission error: {str(e)}",
                    execution_time=0,
                )
                source_results[source_name] = result
                yield result

        while pending:
            done, not_done = await asyncio.wait(
                pending.values(),
                timeout=self.timeout_per_source,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if done:
                for task in done:
                    source_name = next(
                        (name for name, t in pending.items() if t == task),
                        None,
                    )
                    if source_name is None:
                        continue

                    start_time = source_start_times.get(
                        source_name, time.time()
                    )

                    try:
                        jobs = await task
                        duration = time.time() - start_time

                        result = SourceResult(
                            source_name=source_name,
                            jobs=jobs if jobs else [],
                            success=True,
                            execution_time=round(duration, 2),
                        )

                        source_results[source_name] = result
                        all_jobs.extend(jobs)
                        logger.info(
                            f"[SOURCE: {source_name}] success: {len(jobs)} jobs found in {duration:.2f}s"
                        )
                        yield result

                    except Exception as e:
                        duration = time.time() - start_time
                        error_msg = str(e)

                        if "timeout" in error_msg.lower():
                            logger.error(
                                f"[SOURCE: {source_name}] timeout after {duration:.2f}s"
                            )
                        elif "401" in error_msg or "403" in error_msg:
                            logger.error(
                                f"[SOURCE: {source_name}] quota/auth: {error_msg[:100]}"
                            )
                        else:
                            logger.error(
                                f"[SOURCE: {source_name}] error: {error_msg[:100]}"
                            )

                        result = SourceResult(
                            source_name=source_name,
                            jobs=[],
                            success=False,
                            error=error_msg[:100],
                            execution_time=round(duration, 2),
                        )

                        source_results[source_name] = result
                        yield result

                    pending.pop(source_name, None)
            else:
                for source_name, task in list(pending.items()):
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                        pass

                    start_time = source_start_times.get(
                        source_name, time.time()
                    )
                    duration = time.time() - start_time
                    logger.error(
                        f"[SOURCE: {source_name}] timeout after {duration:.2f}s"
                    )

                    result = SourceResult(
                        source_name=source_name,
                        jobs=[],
                        success=False,
                        error=f"Timeout after {self.timeout_per_source}s",
                        execution_time=round(duration, 2),
                    )

                    source_results[source_name] = result
                    yield result

                pending.clear()

        logger.info(
            f"Streaming search complete: {len(all_jobs)} jobs from {len(source_results)} sources"
        )


def normalize_jobs_for_frontend(jobs: List[dict], search_location: str = "") -> List[dict]:
    """
    Normalize a list of jobs for the frontend.
    """
    normalized = []
    
    for job in jobs:
        if not isinstance(job, dict):
            continue
        
        norm = dict(job)  # shallow copy
        
        # Canonical field names
        norm["title"] = norm.get("title") or norm.get("titre") or norm.get("intitule") or ""
        norm["company"] = norm.get("company") or norm.get("entreprise") or norm.get("companyName") or "N/C"
        norm["link"] = norm.get("link") or norm.get("lien") or norm.get("job_url") or norm.get("url") or "#"
        norm["location"] = norm.get("location") or norm.get("localisation") or ""
        norm["source"] = norm.get("source") or norm.get("site") or norm.get("source_name") or "Inconnue"
        norm["date"] = norm.get("date") or norm.get("date_posted") or norm.get("created") or ""
        
        # pertinence_ai
        match_score = norm.get("match_score")
        if match_score is None:
            match_score = norm.get("ml_score", 0)
        try:
            score = float(match_score)
        except (TypeError, ValueError):
            score = 0.0
        norm["pertinence_ai"] = max(0.0, min(100.0, score))
        
        # posted_date
        posted = norm.get("date", "")
        if posted:
            date_str = str(posted).strip()
            if date_str:
                try:
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S",
                                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            norm["posted_date"] = dt.isoformat()
                            break
                        except ValueError:
                            continue
                    else:
                        norm["posted_date"] = date_str
                except Exception:
                    norm["posted_date"] = date_str
            else:
                norm["posted_date"] = ""
        else:
            norm["posted_date"] = ""
        
        # distance_score
        search_loc = (search_location or "").lower().strip()
        job_loc = (norm.get("location") or "").lower().strip()
        if not search_loc or not job_loc:
            norm["distance_score"] = 50.0
        elif search_loc in job_loc or job_loc in search_loc:
            norm["distance_score"] = 100.0
        else:
            norm["distance_score"] = 20.0
        
        normalized.append(norm)
    
    return normalized