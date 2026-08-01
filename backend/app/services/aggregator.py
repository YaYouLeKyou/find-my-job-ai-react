"""
Async Aggregator Service
Orchestrates parallel job searches and generates SSE (Server-Sent Events) in real-time
"""

import asyncio
import hashlib
import inspect
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
    Uses asyncio tasks for concurrent execution with per-source timeouts.
    Streams results progressively as each source completes.
    Continues until all sources are exhausted.
    """
    
    def __init__(self, max_workers: int = 30, timeout_per_source: float = 90.0):
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
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(len(sources), 8))) as executor:
            future_to_source = {}
            
            for source_name, source_fn in sources.items():
                try:
                    source_start_times[source_name] = time.time()
                    logger.info(f"[SOURCE: {source_name}] ⏱️ Start search for query: \"{query}\"")
                    
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
            
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                start_time = source_start_times.get(source_name, time.time())
                
                try:
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
        limit: int,
        target_jobs: int = 0,
        source_timeouts: Optional[Dict[str, float]] = None,
    ):
        """Search multiple sources in parallel and stream results progressively.

        Launches all sources in a single pass using asyncio.to_thread +
        asyncio.wait(FIRST_COMPLETED) so the event loop is never blocked and
        SSE events can be flushed progressively as each source finishes.

        When target_jobs is reached, remaining tasks are cancelled and the
        stream closes cleanly. Sources that fail or return 0 jobs are ignored
        transparently without blocking the flow.

        Args:
            source_timeouts: Optional dict of {source_name: timeout_seconds} for
                             per-source timeout overrides. Falls back to
                             self.timeout_per_source when not specified.
        """
        all_jobs: List[dict] = []
        source_results: Dict[str, SourceResult] = {}
        source_start_times: Dict[str, float] = {}
        completed_sources: set = set()

        logger.info(
            f"Starting progressive streaming parallel search with {len(sources)} sources, target={target_jobs or limit}"
        )

        # Launch all sources in parallel (single pass)
        pending_tasks: Dict[asyncio.Task, str] = {}

        for source_name, source_fn in sources.items():
            start_time = time.time()
            source_start_times[source_name] = start_time
            remaining = max(1, (target_jobs - len(all_jobs)) if target_jobs > 0 else limit)

            logger.info(
                f"[SOURCE: {source_name}] start search, remaining target={remaining}"
            )

            source_timeout = (source_timeouts or {}).get(source_name, self.timeout_per_source)
            if inspect.iscoroutinefunction(source_fn):
                coro = source_fn(query, location, remaining)
                task = asyncio.create_task(
                    asyncio.wait_for(coro, timeout=source_timeout)
                )
            else:
                task = asyncio.create_task(
                    asyncio.wait_for(
                        asyncio.to_thread(source_fn, query, location, remaining),
                        timeout=source_timeout,
                    )
                )
            pending_tasks[task] = source_name

        if not pending_tasks:
            logger.info("[STREAM] No sources to search")
            return

        # Process results as they complete
        while pending_tasks:
            done, pending = await asyncio.wait(
                pending_tasks.keys(),
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                source_name = pending_tasks.pop(task)
                start_time = source_start_times.get(source_name, time.time())
                completed_sources.add(source_name)

                try:
                    jobs = task.result()
                    duration = time.time() - start_time

                    result = SourceResult(
                        source_name=source_name,
                        jobs=jobs if jobs else [],
                        success=True,
                        execution_time=round(duration, 2),
                    )

                    source_results[source_name] = result

                    if jobs:
                        all_jobs.extend(jobs)
                        logger.info(
                            f"[SOURCE: {source_name}] success: {len(jobs)} jobs found in {duration:.2f}s"
                        )
                    else:
                        logger.info(f"[SOURCE: {source_name}] returned 0 jobs after {duration:.2f}s")

                    yield result
                    await asyncio.sleep(0)

                except asyncio.TimeoutError:
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
                    await asyncio.sleep(0)

                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = str(e)

                    if "401" in error_msg or "403" in error_msg:
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
                    await asyncio.sleep(0)

                # Check if target is reached — cancel remaining tasks
                if target_jobs > 0 and len(all_jobs) >= target_jobs:
                    logger.info(
                        f"[STREAM] Target reached: {len(all_jobs)} jobs, cancelling remaining tasks"
                    )
                    for remaining_task in list(pending):
                        remaining_task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    break

        logger.info(
            f"Streaming search complete: {len(all_jobs)} jobs from {len(source_results)} sources"
        )


def normalize_jobs_for_frontend(jobs: List[dict], search_location: str = "") -> List[dict]:
    """
    Normalize a list of jobs for the frontend.
    Uses the same normalization logic as bypass_strategies.py for consistency.
    """
    from app.scrapers.bypass_strategies import normalize_and_deduplicate
    
    # Use the centralized normalization function
    normalized = normalize_and_deduplicate(jobs)
    
    # Add frontend-specific fields
    for job in normalized:
        # pertinence_ai
        match_score = job.get("match_score")
        if match_score is None:
            match_score = job.get("ml_score", 0)
        try:
            score = float(match_score)
        except (TypeError, ValueError):
            score = 0.0
        job["pertinence_ai"] = max(0.0, min(100.0, score))
        
        # posted_date
        posted = job.get("date", "")
        if posted:
            date_str = str(posted).strip()
            if date_str:
                try:
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S",
                                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            job["posted_date"] = dt.isoformat()
                            break
                        except ValueError:
                            continue
                    else:
                        job["posted_date"] = date_str
                except Exception:
                    job["posted_date"] = date_str
            else:
                job["posted_date"] = ""
        else:
            job["posted_date"] = ""
        
        # distance_score
        search_loc = (search_location or "").lower().strip()
        job_loc = (job.get("location") or "").lower().strip()
        if not search_loc or not job_loc:
            job["distance_score"] = 50.0
        elif search_loc in job_loc or job_loc in search_loc:
            job["distance_score"] = 100.0
        else:
            job["distance_score"] = 20.0
        
        # Generate stable ID based on title + company + link
        id_str = f"{job.get('titre', '')}|{job.get('entreprise', '')}|{job.get('lien', '')}"
        job["id"] = hashlib.md5(id_str.encode()).hexdigest()[:12]
    
    return normalized
