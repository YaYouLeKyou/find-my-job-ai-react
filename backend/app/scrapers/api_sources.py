"""
API-based job sources
France Travail API v2 with async httpx (2 parallel pages)
Adzuna API with async httpx
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class FranceTravailSource:
    """
    France Travail Official API v2 Client
    Uses async httpx for concurrent page fetching
    """

    BASE_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2"
    AUTH_URL = "https://authentification-partenaire.francetravail.io/connexion/oauth2/access_token?realm=%2Fpartenaire"

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize France Travail API client.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._token_expiry = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get_access_token(self) -> Optional[str]:
        """
        Get OAuth2 access token with retry logic.

        Returns:
            Access token or None if authentication fails
        """
        # Return cached token if still valid
        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._access_token

        try:
            logger.info("🔑 Requesting France Travail access token...")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "api_offresdemploiv2 o2dsoffre"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )

                logger.info(f"   Auth response status: {response.status_code}")

                if response.status_code != 200:
                    logger.error(f"❌ France Travail auth failed: HTTP {response.status_code}")
                    logger.error(f"   Response: {response.text[:500]}")
                    return None

                token_data = response.json()
                self._access_token = token_data.get("access_token")

                if not self._access_token:
                    logger.error(f"❌ No access token in response: {token_data}")
                    return None

                # Calculate expiry (subtract 60 seconds for safety margin)
                expires_in = token_data.get("expires_in", 3600)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

                logger.info(f"✅ France Travail access token obtained (expires in {expires_in}s)")
                return self._access_token

        except Exception as e:
            logger.error(f"❌ France Travail auth error: {e}")
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def _fetch_page(self, params: dict, headers: dict) -> Optional[dict]:
        """
        Fetch a single page of results.

        Args:
            params: Query parameters
            headers: Request headers

        Returns:
            JSON response data or None
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/offres/search",
                params=params,
                headers=headers,
                timeout=10.0
            )

            logger.info(f"   Search response status: {response.status_code}")

            if response.status_code == 204:
                logger.info("⚠️ France Travail: No content (204)")
                return None

            # France Travail API returns 206 (Partial Content) when using range parameter
            if response.status_code not in (200, 206):
                logger.error(f"❌ France Travail API error: HTTP {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return None

            return response.json()

    async def search_jobs(
        self,
        query: str,
        location: str = "France",
        limit: int = 100,
        contract_type: str = "",
        remote_only: bool = False
    ) -> List[dict]:
        """
        Search for jobs using France Travail API with parallel page fetching.

        Args:
            query: Job search query
            location: Location (city, region, or "France")
            limit: Maximum number of results
            contract_type: Contract type filter (CDI, CDD, etc.)
            remote_only: Filter for remote jobs only

        Returns:
            List of job dictionaries
        """
        # Get access token
        token = await self._get_access_token()
        if not token:
            logger.warning("⚠️ No France Travail access token available")
            return []

        jobs = []

        try:
            logger.info(f"🔍 Searching France Travail API: query='{query}', location='{location}', limit={limit}")

            # Build search parameters
            params = {
                "motsCles": query,
                "range": f"0-{max(limit - 1, 149)}",  # Request up to 150 results
            }

            # Clean location
            clean_location = ""
            if location:
                clean_location = re.sub(r',?\s*France\s*$', '', location, flags=re.IGNORECASE)
                clean_location = clean_location.strip().strip(',').strip()

            if clean_location and clean_location.lower() not in ["france", "global", "remote", ""]:
                params["lieu"] = clean_location
            else:
                params["lieu"] = "France"

            # Extract first city only
            if params["lieu"] and "," in params["lieu"]:
                params["lieu"] = params["lieu"].split(",")[0].strip()
                logger.info(f"   Normalized location to: {params['lieu']}")

            # Add filters
            if contract_type:
                params["typeContrat"] = contract_type

            if remote_only:
                params["telework"] = "true"

            logger.info(f"   Full params: {params}")

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            # Fetch pages in parallel for speed
            page_tasks = []
            page_size = 50
            for page_start in range(0, limit, page_size):
                page_end = min(page_start + page_size - 1, limit - 1)
                page_params = params.copy()
                page_params["range"] = f"{page_start}-{page_end}"
                page_tasks.append(self._fetch_page(page_params, headers))
                if len(page_tasks) >= 5:
                    break

            # Execute all requests in parallel
            import asyncio
            results = await asyncio.gather(*page_tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"❌ France Travail page fetch error: {result}")
                    continue

                if not result:
                    continue

                data = result
                page_results = data.get("resultats", [])
                logger.info(f"✅ France Travail: {len(page_results)} results from page")

                for item in page_results:
                    try:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing France Travail job: {e}")
                        continue

            logger.info(f"✅ France Travail: {len(jobs)} total jobs collected")
            return jobs[:limit]

        except Exception as e:
            logger.error(f"❌ France Travail search error: {e}")
            return []

    def _parse_job(self, item: dict) -> Optional[dict]:
        """
        Parse a France Travail job posting.

        Args:
            item: Raw job data from API

        Returns:
            Standardized job dictionary or None
        """
        try:
            # Extract basic info
            title = item.get("intitule", "")
            company = item.get("entreprise", {}).get("nom", "Non précisé")

            # Build job URL
            job_id = item.get("id", "")
            job_url = f"https://candidat.francetravail.fr/offres/recherche/detail/{job_id}"

            # Extract location
            location_data = item.get("lieu", {})
            location = location_data.get("libelle", "")
            if not location:
                location = location_data.get("commune", "")

            # Extract contract type
            contract = item.get("typeContrat", "")
            if not contract:
                contract = item.get("natureContrat", "")

            # Extract description
            description = item.get("description", "")

            # Extract date
            date_publication = item.get("datePublication", "")
            if date_publication:
                try:
                    date_obj = datetime.fromisoformat(date_publication.replace('Z', '+00:00'))
                    date = date_obj.strftime("%Y-%m-%d")
                except Exception:
                    date = date_publication[:10]
            else:
                date = ""

            # Extract salary
            salary_info = item.get("salaire", {})
            salary_text = salary_info.get("libelle", "") or salary_info.get("commentaire", "")

            # Extract skills
            competences = []
            if "competences" in item:
                competences = [c.get("libelle", "") for c in item.get("competences", []) if c.get("libelle")]

            # Build standardized job
            job = {
                "titre": title,
                "entreprise": company,
                "lien": job_url,
                "location": location,
                "date": date,
                "source": "France Travail",
                "description": description[:2000] if description else "",
                "contrat": contract,
                "competences": competences,
            }

            return job

        except Exception as e:
            logger.debug(f"Error parsing France Travail job: {e}")
            return None


class AdzunaSource:
    """
    Adzuna API Client
    Uses async httpx for job search
    Returns [] gracefully on quota exceeded (HTTP 429/403)
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id: str, app_key: str):
        """
        Initialize Adzuna API client.

        Args:
            app_id: Adzuna application ID
            app_key: Adzuna application key
        """
        self.app_id = app_id
        self.app_key = app_key

    async def search_jobs(
        self,
        query: str,
        location: str = "France",
        limit: int = 100,
        contract_type: str = "",
        remote_only: bool = False
    ) -> List[dict]:
        """
        Search for jobs using Adzuna API.

        Args:
            query: Job search query
            location: Location (country or city)
            limit: Maximum number of results
            contract_type: Contract type filter
            remote_only: Filter for remote jobs only

        Returns:
            List of job dictionaries (empty list on error/quota)
        """
        # Determine country code from location
        country = self._resolve_country(location)

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": limit,
            "what": query,
            "content-type": "application/json",
        }

        # Add location filter if not global
        clean_loc = location.lower().strip()
        if clean_loc and clean_loc not in ["france", "global", "worldwide", ""]:
            params["where"] = location

        # Add contract type filter
        if contract_type:
            params["type"] = contract_type

        try:
            logger.info(f"🔍 Searching Adzuna API: query='{query}', location='{location}', country='{country}', limit={limit}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/{country}/search/1",
                    params=params,
                )

                # Handle quota / rate limiting gracefully
                if response.status_code in (429, 403):
                    logger.warning(f"⚠️ Adzuna quota/rate limit exceeded (HTTP {response.status_code}) - returning empty list")
                    return []

                if response.status_code != 200:
                    logger.error(f"❌ Adzuna API error: HTTP {response.status_code}")
                    return []

                data = response.json()
                results = data.get("results", [])
                logger.info(f"✅ Adzuna: {len(results)} results received")

                jobs = []
                for item in results[:limit]:
                    try:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing Adzuna job: {e}")
                        continue

                return jobs

        except httpx.TimeoutException:
            logger.warning("⚠️ Adzuna API timeout - returning empty list")
            return []
        except Exception as e:
            logger.error(f"❌ Adzuna search error: {e}")
            return []

    def _resolve_country(self, location: str) -> str:
        """Resolve a location string to an Adzuna country code."""
        loc_lower = location.lower().strip()
        country_map = {
            "france": "fr", "français": "fr", "paris": "fr",
            "usa": "us", "united states": "us", "new york": "us",
            "uk": "gb", "united kingdom": "gb", "london": "gb",
            "germany": "de", "allemagne": "de", "berlin": "de",
            "spain": "es", "espagne": "es", "madrid": "es",
            "canada": "ca", "toronto": "ca",
            "australia": "au", "sydney": "au",
        }
        for key, code in country_map.items():
            if key in loc_lower:
                return code
        return "fr"  # Default to France

    def _parse_job(self, item: dict) -> Optional[dict]:
        """
        Parse an Adzuna job posting.

        Args:
            item: Raw job data from API

        Returns:
            Standardized job dictionary or None
        """
        try:
            title = item.get("title", "")
            company = item.get("company", {}).get("display_name", "N/C")

            # Build job URL
            job_url = item.get("redirect_url", "#")

            # Extract location
            location = item.get("location", {}).get("display_name", "")

            # Extract date
            date_posted = item.get("created", "")
            date = date_posted[:10] if date_posted else ""

            # Extract description
            description = item.get("description", "")

            # Extract salary
            salary_info = item.get("salary_min", 0)
            salary_max = item.get("salary_max", 0)

            job = {
                "titre": title,
                "entreprise": company,
                "lien": job_url,
                "location": location,
                "date": date,
                "source": "Adzuna",
                "description": description[:2000] if description else "",
                "contrat": item.get("contract_type", ""),
                "salaire_min": salary_info,
                "salaire_max": salary_max,
            }

            return job

        except Exception as e:
            logger.debug(f"Error parsing Adzuna job: {e}")
            return None


# Singleton instances
_france_travail_source = None
_adzuna_source = None


def get_france_travail_source(client_id: Optional[str] = None, client_secret: Optional[str] = None) -> Optional[FranceTravailSource]:
    """
    Get or create France Travail API source singleton.

    Args:
        client_id: OAuth2 client ID (uses env var if not provided)
        client_secret: OAuth2 client secret (uses env var if not provided)

    Returns:
        FranceTravailSource instance or None
    """
    global _france_travail_source

    if _france_travail_source:
        return _france_travail_source

    client_id = client_id or os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "") or ""
    client_secret = client_secret or os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "") or ""

    if not client_id or not client_secret:
        logger.warning("⚠️ France Travail credentials not configured")
        return None

    _france_travail_source = FranceTravailSource(client_id, client_secret)
    return _france_travail_source


def get_adzuna_source(app_id: Optional[str] = None, app_key: Optional[str] = None) -> Optional[AdzunaSource]:
    """
    Get or create Adzuna API source singleton.

    Args:
        app_id: Adzuna application ID (uses env var if not provided)
        app_key: Adzuna application key (uses env var if not provided)

    Returns:
        AdzunaSource instance or None
    """
    global _adzuna_source

    if _adzuna_source:
        return _adzuna_source

    app_id = app_id or os.getenv("ADZUNA_APP_ID", "") or ""
    app_key = app_key or os.getenv("ADZUNA_APP_KEY", "") or ""

    if not app_id or not app_key:
        logger.warning("⚠️ Adzuna credentials not configured")
        return None

    _adzuna_source = AdzunaSource(app_id, app_key)
    return _adzuna_source


class GoogleJobsSource:
    """Google Jobs via SerpApi."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_jobs(
        self,
        query: str,
        location: str = "France",
        limit: int = 50,
        contract_type: str = "",
        remote_only: bool = False
    ) -> List[dict]:
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "hl": "fr",
            "api_key": self.api_key,
        }
        try:
            logger.info(f"[API:GoogleJobs] start query={query!r} location={location!r} limit={limit}")
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.BASE_URL, params=params)
            if response.status_code != 200:
                logger.error(f"[API:GoogleJobs] HTTP {response.status_code}: {response.text[:200]}")
                return []
            data = response.json()
            results = data.get("jobs_results", [])[:limit]
            logger.info(f"[API:GoogleJobs] done jobs={len(results)}")
            return [
                {
                    "titre": item.get("title", ""),
                    "entreprise": item.get("company_name", "N/C"),
                    "lien": item.get("related_links", [{}])[0].get("link") if item.get("related_links") else "#",
                    "location": item.get("location", location),
                    "date": item.get("detected_extensions", {}).get("posted_at", ""),
                    "source": "Google Jobs",
                    "description": item.get("description", ""),
                }
                for item in results
            ]
        except Exception as e:
            logger.error(f"[API:GoogleJobs] error: {e}")
            return []


_google_jobs_source = None


def get_google_jobs_source(api_key: Optional[str] = None) -> Optional[GoogleJobsSource]:
    global _google_jobs_source
    if _google_jobs_source:
        return _google_jobs_source
    api_key = api_key or os.getenv("SERPAPI_KEY", "") or ""
    if not api_key:
        logger.warning("⚠️ SerpApi key not configured")
        return None
    _google_jobs_source = GoogleJobsSource(api_key)
    return _google_jobs_source


class JoobleSource:
    BASE_URL = "https://jooble.org/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_jobs(
        self,
        query: str,
        location: str = "France",
        limit: int = 50,
        contract_type: str = "",
        remote_only: bool = False,
    ) -> List[dict]:
        try:
            logger.info(f"[API:Jooble] start query={query!r} location={location!r} limit={limit}")
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/{self.api_key}",
                    json={"keywords": query, "location": location},
                )
            if response.status_code != 200:
                logger.error(f"[API:Jooble] HTTP {response.status_code}: {response.text[:200]}")
                return []
            data = response.json()
            results = data.get("jobs", [])[:limit]
            logger.info(f"[API:Jooble] done jobs={len(results)}")
            return [
                {
                    "titre": item.get("title", ""),
                    "entreprise": item.get("company", "N/C"),
                    "lien": item.get("link", "#"),
                    "location": item.get("type", location),
                    "date": item.get("updated", ""),
                    "source": "Jooble",
                    "description": item.get("description", ""),
                }
                for item in results
            ]
        except Exception as e:
            logger.error(f"[API:Jooble] error: {e}")
            return []


class ApifySource:
    BASE_URL = "https://api.apify.com/v2/acts/apify~linkedin-jobs-scraper/run-sync-get-dataset-items"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_jobs(
        self,
        query: str,
        location: str = "France",
        limit: int = 50,
        contract_type: str = "",
        remote_only: bool = False,
    ) -> List[dict]:
        try:
            logger.info(f"[API:Apify] start query={query!r} location={location!r} limit={limit}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    params={"token": self.api_key},
                    json={"searchKeywords": query, "location": location, "maxItems": limit},
                )
            if response.status_code != 200:
                logger.error(f"[API:Apify] HTTP {response.status_code}: {response.text[:200]}")
                return []
            results = response.json()
            jobs = [
                {
                    "titre": item.get("title", ""),
                    "entreprise": item.get("companyName", "N/C"),
                    "lien": item.get("url", "#"),
                    "location": item.get("location", location),
                    "date": "",
                    "source": "LinkedIn (Apify)",
                    "description": item.get("description", ""),
                }
                for item in results[:limit]
            ]
            logger.info(f"[API:Apify] done jobs={len(jobs)}")
            return jobs
        except Exception as e:
            logger.error(f"[API:Apify] error: {e}")
            return []


_jooble_source = None
_apify_source = None


def get_jooble_source(api_key: Optional[str] = None) -> Optional[JoobleSource]:
    global _jooble_source
    if _jooble_source:
        return _jooble_source
    api_key = api_key or os.getenv("JOOBLE_API_KEY", "") or ""
    if not api_key:
        logger.warning("⚠️ Jooble API key not configured")
        return None
    _jooble_source = JoobleSource(api_key)
    return _jooble_source


def get_apify_source(api_key: Optional[str] = None) -> Optional[ApifySource]:
    global _apify_source
    if _apify_source:
        return _apify_source
    api_key = api_key or os.getenv("APIFY_API_KEY", "") or ""
    if not api_key:
        logger.warning("⚠️ Apify API key not configured")
        return None
    _apify_source = ApifySource(api_key)
    return _apify_source
