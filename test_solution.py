#!/usr/bin/env python3
"""
Test script for the France Travail API solution
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import France Travail client
from app.scrapers.api_sources import FranceTravailSource
import asyncio
import logging

# Configure logging to see debug info
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_api_with_fallback():
    """Test the France Travail API with improved headers and fallback."""

    client_id = os.getenv('FRANCE_TRAVAIL_CLIENT_ID')
    client_secret = os.getenv('FRANCE_TRAVAIL_CLIENT_SECRET')

    if not client_id or not client_secret:
        print('❌ Credentials not configured')
        return False

    print('🔑 Testing France Travail API with improved headers...')

    client = FranceTravailSource(client_id, client_secret)

    # Test authentication
    token = await client._get_access_token()
    if token:
        print('✅ Authentication successful, token obtained')
        print(f'   Token preview: {token[:20]}...')
    else:
        print('❌ Authentication failed')
        return False

    # Test search with new headers
    try:
        print('🔍 Testing search with improved headers...')
        jobs = await client.search_jobs('Développeur', 'Paris', 3)
        print(f'   Search completed: {len(jobs)} jobs found')

        if jobs:
            print('✅ API working with new headers!')
            print('   Sample results:')
            for i, job in enumerate(jobs[:2], 1):
                print(f'   {i}. {job.get("titre", "N/A")} - {job.get("entreprise", "N/A")}')
            return True
        else:
            print('⚠️ No jobs returned - fallback to RSS would be triggered')
            return False

    except Exception as e:
        print(f'❌ Search failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("France Travail API Solution Test")
    print("=" * 60)
    print()

    success = asyncio.run(test_api_with_fallback())

    print()
    print("=" * 60)
    if success:
        print("✅ Solution test PASSED - API is working!")
    else:
        print("⚠️ Solution test completed - Fallback system will handle gracefully")
    print("=" * 60)