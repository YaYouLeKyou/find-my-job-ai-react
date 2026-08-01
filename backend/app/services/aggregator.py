"""
Async Aggregator Service
Orchestrates parallel job searches and generates SSE (Server-Sent Events) in real-time
"""

import asyncio
import hashlib
import inspect
import json
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

_SOURCE_CACHE: Dict[str, Tuple[float, List[dict]]] = {}
_SOURCE_CACHE_TTL = 180.0  # seconds


def _make_cache_key(source_name: str, query: str, location: str, limit: int) -> str:
    return f"{source_name}|{query}|{location}|{limit}"


def _get_cached_source(cache_key: str) -> Optional[List[dict]]:
    entry = _SOURCE_CACHE.get(cache_key)
    if not entry:
        return None
    timestamp, jobs = entry
    if time.time() - timestamp > _SOURCE_CACHE_TTL:
        _SOURCE_CACHE.pop(cache_key, None)
        return None
    return jobs


def _set_cached_source(cache_key: str, jobs: List[dict]) -> None:
    _SOURCE_CACHE[cache_key] = (time.time(), jobs)


def _normalize_job_signature(job: dict) -> str:
    title = (job.get('title') or job.get('titre') or '').lower().strip()
    company = (job.get('company') or job.get('entreprise') or '').lower().strip()
    location = (job.get('location') or job.get('lieu') or '').lower().strip()
    link = (job.get('link') or job.get('lien') or job.get('url') or '').lower().strip()
    return f"{title}|{company}|{location}|{link}"


class SourceResult:
    """Result from a single source."""
    
    def __init__(
        self,
        source_name: str,
        jobs: List[dict],
        success: bool,
        error: str = "",
        execution_time: float = 0,
        is_partial: bool = False,
        done: bool = True,
        fallback: bool = False,
    ): 
        self.source_name = source_name
        self.jobs = jobs
        self.success = success
        self.error = error
        self.execution_time = execution_time
        self.is_partial = is_partial
        self.done = done
        self.fallback = fallback
    
    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "jobs": self.jobs,
            "success": self.success,
            "error": self.error,
            "execution_time": self.execution_time,
            "is_partial": self.is_partial,
            "done": self.done,
            "fallback": self.fallback,
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
        source_limits: Optional[Dict[str, int]] = None,
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

        # Use an internal queue to receive per-source batches (partial + final)
        queue: asyncio.Queue = asyncio.Queue()

        async def _run_source_paged(source_name: str, source_fn: Callable):
            """Run a source with progressive pagination and retries.

            Pseudocode:
            - Try to detect pagination params (page/offset) via signature.
            - Fetch first small page quickly (per_page_fast), yield partial result.
            - If batch == per_page_fast, attempt subsequent pages until limit reached or fewer results.
            - Apply retries with exponential backoff on transient errors.
            - Emit cached fallback quickly when available while the real source is still loading.
            """
            source_limit = (source_limits or {}).get(source_name, limit)
            per_page_fast = min(10, max(5, source_limit // 2))
            per_page = min(20, source_limit)
            fetched = 0
            page = 0
            sig = None
            try:
                sig = inspect.signature(source_fn)
            except Exception:
                sig = None

            def _call_source(page_arg, fetch_limit):
                kwargs = {}
                if sig and 'page' in sig.parameters:
                    kwargs['page'] = page_arg
                    kwargs['limit'] = fetch_limit
                elif sig and 'offset' in sig.parameters:
                    kwargs['offset'] = page_arg * fetch_limit
                    kwargs['limit'] = fetch_limit
                elif sig and 'limit' in sig.parameters:
                    kwargs['limit'] = fetch_limit
                else:
                    # Function doesn't accept 'limit' as keyword (e.g. uses 'n') - pass as positional
                    if inspect.iscoroutinefunction(source_fn):
                        return source_fn(query, location, fetch_limit)
                    else:
                        return asyncio.to_thread(source_fn, query, location, fetch_limit)
                if inspect.iscoroutinefunction(source_fn):
                    return source_fn(query, location, **kwargs)
                else:
                    return asyncio.to_thread(source_fn, query, location, **kwargs)

            cache_key = _make_cache_key(source_name, query, location, source_limit)
            cached_jobs = _get_cached_source(cache_key)
            accumulated_jobs: List[dict] = []
            start_time = time.time()
            fast_start_timeout = 1.5

            while fetched < source_limit:
                fetch_limit = per_page_fast if page == 0 else per_page
                attempt = 0
                max_attempts = 3
                backoff = 0.5
                last_exc = None
                while attempt < max_attempts:
                    try:
                        task = asyncio.create_task(_call_source(page, fetch_limit))
                        done, pending = await asyncio.wait({task}, timeout=fast_start_timeout)
                        if task not in done and cached_jobs and page == 0:
                            fallback_batch = cached_jobs[:fetch_limit]
                            await queue.put(SourceResult(
                                source_name,
                                fallback_batch,
                                True,
                                execution_time=0.0,
                                is_partial=True,
                                done=False,
                                fallback=True,
                            ))

                        timeout = (source_timeouts or {}).get(source_name, self.timeout_per_source)
                        jobs = await asyncio.wait_for(task, timeout=timeout)
                        duration = time.time() - start_time
                        if not jobs:
                            await queue.put(SourceResult(source_name, [], True, execution_time=round(duration, 2), is_partial=True, done=True))
                            return

                        batch = jobs if isinstance(jobs, list) else list(jobs)
                        batch_len = len(batch)
                        fetched += batch_len
                        accumulated_jobs.extend(batch)

                        is_partial = fetched < source_limit and batch_len >= fetch_limit
                        done = not is_partial

                        if done:
                            _set_cached_source(cache_key, accumulated_jobs)

                        await queue.put(SourceResult(
                            source_name,
                            batch,
                            True,
                            execution_time=round(duration, 2),
                            is_partial=is_partial,
                            done=done,
                            fallback=False,
                        ))

                        if not is_partial:
                            return

                        page += 1
                        break
                    except asyncio.TimeoutError as e:
                        last_exc = e
                        attempt += 1
                        logger.warning(f"[SOURCE: {source_name}] timeout attempt {attempt}/{max_attempts}")
                        await asyncio.sleep(backoff * attempt)
                    except Exception as e:
                        last_exc = e
                        attempt += 1
                        logger.warning(f"[SOURCE: {source_name}] transient error attempt {attempt}/{max_attempts}: {e}")
                        await asyncio.sleep(backoff * attempt)

                if last_exc is not None and attempt >= max_attempts:
                    try:
                        relaxed_q = ' '.join(query.split()[:5]) if isinstance(query, str) else query
                        logger.info(f"[SOURCE: {source_name}] performing relaxed fallback query: {relaxed_q!r}")
                        if inspect.iscoroutinefunction(source_fn):
                            coro = source_fn(relaxed_q, location, source_limit)
                        else:
                            coro = asyncio.to_thread(source_fn, relaxed_q, location, source_limit)
                        timeout = (source_timeouts or {}).get(source_name, self.timeout_per_source)
                        jobs = await asyncio.wait_for(coro, timeout=timeout)
                        duration = time.time() - start_time
                        if jobs:
                            batch = jobs if isinstance(jobs, list) else list(jobs)
                            accumulated_jobs.extend(batch)
                            _set_cached_source(cache_key, accumulated_jobs)
                            await queue.put(SourceResult(
                                source_name,
                                batch,
                                True,
                                execution_time=round(duration, 2),
                                is_partial=False,
                                done=True,
                                fallback=False,
                            ))
                            return
                    except Exception:
                        pass

                    duration = time.time() - start_time
                    await queue.put(SourceResult(
                        source_name,
                        [],
                        False,
                        error=str(last_exc)[:200],
                        execution_time=round(duration, 2),
                        is_partial=False,
                        done=True,
                        fallback=False,
                    ))
                    return

        # Launch one task per source that will push partial batches into queue
        tasks = [asyncio.create_task(_run_source_paged(sname, sfn)) for sname, sfn in sources.items()]

        total_sources = len(tasks)
        finished_sources = 0

        # Drain queue until all source tasks complete and queue is empty
        while finished_sources < total_sources or not queue.empty():
            try:
                result: SourceResult = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # allow checking if tasks finished
                if all(t.done() for t in tasks) and queue.empty():
                    break
                continue

            # If this result signals done for a source, increase finished_sources
            if result.done:
                finished_sources += 1

            yield result
            await asyncio.sleep(0)

        # Ensure all tasks complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
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
        # Map French-normalized fields to frontend-friendly keys
        job["title"] = job.get("title") or job.get("titre") or job.get("poste") or job.get("mission") or job.get("name") or ""
        job["company"] = job.get("company") or job.get("entreprise") or job.get("client") or job.get("employer") or ""
        job["link"] = job.get("link") or job.get("lien") or job.get("url") or job.get("job_url") or job.get("source_url") or "#"
        job["location"] = job.get("location") or job.get("lieu") or job.get("city") or job.get("region") or ""
        job["description"] = job.get("description") or job.get("resume") or job.get("summary") or job.get("desc") or ""
        job["source"] = job.get("source") or job.get("source_name") or job.get("origin") or ""

        # pertinence_ai - PRÉSERVER le score AI existant s'il est déjà présent
        existing_score = job.get("pertinence_ai")
        if existing_score is not None:
            try:
                job["pertinence_ai"] = max(0.0, min(100.0, float(existing_score)))
            except (TypeError, ValueError):
                job["pertinence_ai"] = 0.0
        else:
            # Fallback sur match_score ou ml_score
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
