"""
Playwright Worker - Isolates Playwright browser automation in async worker
Prevents blocking user requests and reduces CPU/RAM usage on Railway
"""

import logging
import asyncio
import time
from typing import List, Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlaywrightTask:
    """Task for Playwright worker."""
    task_id: str
    scraper_name: str
    query: str
    location: str
    limit: int
    future: Future


class PlaywrightWorker:
    """
    Isolates Playwright browser automation in a separate worker thread.
    Prevents blocking the main application and manages resource usage.
    """
    
    def __init__(self, max_concurrent: int = 2, queue_timeout: int = 30):
        """
        Initialize Playwright worker.
        
        Args:
            max_concurrent: Maximum concurrent Playwright instances
            queue_timeout: Maximum time to wait in queue (seconds)
        """
        self.max_concurrent = max_concurrent
        self.queue_timeout = queue_timeout
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.active_tasks: Dict[str, PlaywrightTask] = {}
        self.task_counter = 0
        self._lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
    
    def submit_task(
        self,
        scraper_name: str,
        scraper_func: Callable[..., Any],
        query: str,
        location: str,
        limit: int
    ) -> Optional[Future]:
        """
        Submit a Playwright scraping task.
        
        Args:
            scraper_name: Name of the scraper (for logging)
            scraper_func: Function to call (query, location, limit) -> List[dict]
            query: Job search query
            location: Location
            limit: Maximum results
        
        Returns:
            Future object or None if submission failed
        """
        self.task_counter += 1
        task_id = f"pw_{self.task_counter}_{int(time.time())}"
        
        try:
            logger.info(f"📋 Submitting Playwright task: {scraper_name} (query='{query}')")
            
            # Submit to thread pool
            future = self.executor.submit(
                self._execute_playwright_task,
                task_id,
                scraper_name,
                scraper_func,
                query,
                location,
                limit
            )
            
            # Track task
            task = PlaywrightTask(
                task_id=task_id,
                scraper_name=scraper_name,
                query=query,
                location=location,
                limit=limit,
                future=future
            )
            self.active_tasks[task_id] = task
            
            logger.info(f"✅ Playwright task submitted: {task_id}")
            return future
            
        except Exception as e:
            logger.error(f"❌ Failed to submit Playwright task: {e}")
            return None
    
    def _execute_playwright_task(
        self,
        task_id: str,
        scraper_name: str,
        scraper_func: Callable[..., Any],
        query: str,
        location: str,
        limit: int
    ) -> List[dict]:
        """
        Execute Playwright task in isolated thread.
        
        Args:
            task_id: Unique task ID
            scraper_name: Name of the scraper
            scraper_func: Scraper function to call
            query: Job search query
            location: Location
            limit: Maximum results
        
        Returns:
            List of job dictionaries
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Starting Playwright task {task_id}: {scraper_name}")
            
            # Execute the scraper function
            jobs = scraper_func(query, location, limit)
            
            execution_time = time.time() - start_time
            
            if jobs:
                logger.info(f"✅ Playwright task {task_id} completed: {len(jobs)} jobs in {execution_time:.2f}s")
            else:
                logger.info(f"⚠️ Playwright task {task_id} completed: 0 results in {execution_time:.2f}s")
            
            return jobs
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Playwright task {task_id} failed: {e}")
            return []
        
        finally:
            # Clean up task
            self.active_tasks.pop(task_id, None)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get status of a task.
        
        Args:
            task_id: Task ID to check
        
        Returns:
            Task status dictionary or None
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return None
        
        status = {
            "task_id": task_id,
            "scraper_name": task.scraper_name,
            "query": task.query,
            "location": task.location,
            "limit": task.limit,
            "running": not task.future.done(),
            "completed": task.future.done(),
        }
        
        if task.future.done():
            try:
                result = task.future.result(timeout=0)
                status["success"] = True
                status["result_count"] = len(result) if result else 0
            except Exception as e:
                status["success"] = False
                status["error"] = str(e)[:100]
        
        return status
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
        
        Returns:
            True if cancelled, False otherwise
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        
        try:
            cancelled = task.future.cancel()
            if cancelled:
                self.active_tasks.pop(task_id, None)
                logger.info(f"🚫 Cancelled Playwright task: {task_id}")
            return cancelled
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def get_active_count(self) -> int:
        """Get number of active tasks."""
        return len(self.active_tasks)
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the worker.
        
        Args:
            wait: Wait for tasks to complete
        """
        logger.info(f"Shutting down Playwright worker (active tasks: {len(self.active_tasks)})")
        
        # Cancel all active tasks
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)
        
        # Shutdown executor
        self.executor.shutdown(wait=wait)
        logger.info("✅ Playwright worker shutdown complete")


# Singleton instance
_playwright_worker = None


def get_playwright_worker(max_concurrent: int = 2) -> PlaywrightWorker:
    """
    Get or create Playwright worker singleton.
    
    Args:
        max_concurrent: Maximum concurrent Playwright instances
    
    Returns:
        PlaywrightWorker instance
    """
    global _playwright_worker
    
    if _playwright_worker is None:
        _playwright_worker = PlaywrightWorker(max_concurrent=max_concurrent)
        logger.info(f"✅ Playwright worker initialized (max_concurrent={max_concurrent})")
    
    return _playwright_worker


def submit_playwright_task(
    scraper_name: str,
    scraper_func: callable,
    query: str,
    location: str,
    limit: int
) -> Optional[Future]:
    """
    Convenience function to submit a Playwright task.
    
    Args:
        scraper_name: Name of the scraper
        scraper_func: Scraper function
        query: Job search query
        location: Location
        limit: Maximum results
    
    Returns:
        Future object or None
    """
    worker = get_playwright_worker()
    return worker.submit_task(scraper_name, scraper_func, query, location, limit)