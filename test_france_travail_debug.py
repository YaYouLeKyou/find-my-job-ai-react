#!/usr/bin/env python3
"""
Test script for France Travail API with detailed debugging
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import France Travail client
from app.scrapers.api_sources import FranceTravailSource
import asyncio


async def test_france_travail_api():
    """Test France Travail API integration with detailed logging."""

    print("=" * 60)
    print("France Travail API Debug Test")
    print("=" * 60)

    # Check credentials
    client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "")
    client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "")

    print("\n1. Credentials Check:")
    print(f"   Client ID configured: {bool(client_id)}")
    print(f"   Client Secret configured: {bool(client_secret)}")
    print(f"   Client ID preview: {client_id[:20]}...")
    print(f"   Client Secret preview: {client_secret[:20]}...")

    if not client_id or not client_secret:
        print("\n[ERROR] France Travail credentials not configured in .env")
        return False

    # Get client
    print("\n2. Initializing Client:")
    client = FranceTravailSource(client_id, client_secret)
    print("[OK] Client initialized successfully")

    # Test authentication
    print("\n3. Testing Authentication:")
    token = await client._get_access_token()

    if not token:
        print("[ERROR] Failed to obtain access token")
        return False

    print("[OK] Access token obtained successfully")
    print(f"   Token preview: {token[:20]}...")

    # Test job search with detailed logging
    print("\n4. Testing Job Search:")
    print("   Attempting search: query='Developpeur', location='Paris', limit=5")

    try:
        jobs = await client.search_jobs(
            query="Developpeur",
            location="Paris",
            limit=5
        )

        print(f"   Results: {len(jobs)} jobs found")

        if jobs:
            print(f"   Sample job:")
            sample = jobs[0]
            print(f"     - Title: {sample.get('titre', 'N/A')}")
            print(f"     - Company: {sample.get('entreprise', 'N/A')}")
            print(f"     - Location: {sample.get('location', 'N/A')}")
            print(f"     - Source: {sample.get('source', 'N/A')}")
        else:
            print("   [WARN] No jobs returned - this indicates a 403 Forbidden issue")

    except Exception as e:
        print(f"   [ERROR] Exception during search: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_france_travail_api())
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
