#!/usr/bin/env python3
"""
Test script for France Travail API integration
Run this to verify the API is working correctly
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import France Travail client
from ai_modules.france_travail_api import get_france_travail_client

def test_france_travail_api():
    """Test France Travail API integration."""
    
    print("=" * 60)
    print("France Travail API Test")
    print("=" * 60)
    
    # Check credentials
    client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "")
    client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "")
    
    print(f"\n1. Credentials Check:")
    print(f"   Client ID configured: {bool(client_id)}")
    print(f"   Client Secret configured: {bool(client_secret)}")
    
    if not client_id or not client_secret:
        print("\n❌ ERROR: France Travail credentials not configured in .env")
        return False
    
    # Get client
    print(f"\n2. Initializing Client:")
    client = get_france_travail_client()
    
    if not client:
        print("❌ ERROR: Failed to create France Travail client")
        return False
    
    print("✅ Client initialized successfully")
    
    # Test authentication
    print(f"\n3. Testing Authentication:")
    token = client._get_access_token()
    
    if not token:
        print("❌ ERROR: Failed to obtain access token")
        return False
    
    print(f"✅ Access token obtained successfully")
    print(f"   Token preview: {token[:20]}...")
    
    # Test job search
    print(f"\n4. Testing Job Search:")
    test_queries = [
        ("Cadreur/Monteur", "France"),
        ("Développeur Python", "Paris"),
        ("Chef de projet", "Lyon"),
    ]
    
    for query, location in test_queries:
        print(f"\n   Testing: query='{query}', location='{location}'")
        jobs = client.search_jobs(
            query=query,
            location=location,
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
    
    print("\n" + "=" * 60)
    print("✅ France Travail API test completed successfully!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_france_travail_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)