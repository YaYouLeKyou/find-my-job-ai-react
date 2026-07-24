"""
France Travail Official API Client
Integrates with the official Pole Emploi / France Travail API
"""

import logging
import time
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FranceTravailAPI:
    """Client for France Travail (Pole Emploi) official API."""
    
    BASE_URL = "https://api.pole-emploi.io/partenaire/offresdemploi/v2"
    AUTH_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token"
    
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
    
    def _get_access_token(self) -> Optional[str]:
        """
        Get OAuth2 access token.
        
        Returns:
            Access token or None if authentication fails
        """
        # Return cached token if still valid
        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._access_token
        
        import requests
        
        try:
            logger.info("🔑 Requesting France Travail access token...")
            
            response = requests.post(
                self.AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "api_offresdemploiv2"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5
            )
            
            if response.status_code != 200:
                logger.error(f"❌ France Travail auth failed: HTTP {response.status_code}")
                return None
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            
            # Calculate expiry (subtract 60 seconds for safety margin)
            expires_in = token_data.get("expires_in", 3600)
            from datetime import timedelta
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            
            logger.info("✅ France Travail access token obtained")
            return self._access_token
            
        except Exception as e:
            logger.error(f"❌ France Travail auth error: {e}")
            return None
    
    def search_jobs(
        self,
        query: str,
        location: str = "France",
        limit: int = 10,
        contract_type: str = "",
        remote_only: bool = False
    ) -> List[dict]:
        """
        Search for jobs using France Travail API.
        
        Args:
            query: Job search query
            location: Location (city, region, or "France")
            limit: Maximum number of results
            contract_type: Contract type filter (CDI, CDD, etc.)
            remote_only: Filter for remote jobs only
        
        Returns:
            List of job dictionaries
        """
        import requests
        
        # Get access token
        token = self._get_access_token()
        if not token:
            logger.warning("⚠️ No France Travail access token available")
            return []
        
        jobs = []
        
        try:
            logger.info(f"🔍 Searching France Travail API: query='{query}', location='{location}'")
            
            # Build search parameters
            params = {
                "motsCles": query,
                "range": f"0-{limit-1}",
            }
            
            # Add location filter
            if location and location.lower() not in ["france", "global"]:
                params["lieu"] = location
            
            # Add contract type filter
            if contract_type:
                params["typeContrat"] = contract_type
            
            # Add remote filter
            if remote_only:
                params["telework"] = "true"
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            response = requests.get(
                f"{self.BASE_URL}/offres/search",
                params=params,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 204:
                logger.info("⚠️ France Travail: No content (204)")
                return []
            
            if response.status_code != 200:
                logger.error(f"❌ France Travail API error: HTTP {response.status_code}")
                return []
            
            data = response.json()
            results = data.get("resultats", [])
            
            logger.info(f"✅ France Travail: {len(results)} results")
            
            # Parse results
            for item in results:
                try:
                    job = self._parse_job(item)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing France Travail job: {e}")
                    continue
            
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
                    # Parse ISO format date
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(date_publication.replace('Z', '+00:00'))
                    date = date_obj.strftime("%Y-%m-%d")
                except:
                    date = date_publication[:10]
            else:
                date = ""
            
            # Extract salary
            salary_info = item.get("salaire", {})
            salary_text = salary_info.get("libelle", "") or salary_info.get("commentaire", "")
            
            # Extract skills/competences
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
    
    def get_job_details(self, job_id: str) -> Optional[dict]:
        """
        Get detailed information for a specific job.
        
        Args:
            job_id: France Travail job ID
        
        Returns:
            Detailed job dictionary or None
        """
        import requests
        
        token = self._get_access_token()
        if not token:
            return None
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/offres/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            
            if response.status_code != 200:
                return None
            
            return self._parse_job(response.json())
            
        except Exception as e:
            logger.error(f"Error fetching France Travail job details: {e}")
            return None


# Singleton instance
_france_travail_client = None


def get_france_travail_client(client_id: Optional[str] = None, client_secret: Optional[str] = None) -> Optional[FranceTravailAPI]:
    """
    Get or create France Travail API client singleton.
    
    Args:
        client_id: OAuth2 client ID (uses env var if not provided)
        client_secret: OAuth2 client secret (uses env var if not provided)
    
    Returns:
        FranceTravailAPI instance or None
    """
    global _france_travail_client
    
    if _france_travail_client:
        return _france_travail_client
    
    # Get credentials from parameters or environment
    import os
    client_id = client_id or os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "") or ""
    client_secret = client_secret or os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "") or ""
    
    if not client_id or not client_secret:
        logger.warning("⚠️ France Travail credentials not configured")
        return None
    
    _france_travail_client = FranceTravailAPI(client_id, client_secret)
    return _france_travail_client