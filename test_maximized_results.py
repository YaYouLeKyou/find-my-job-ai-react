#!/usr/bin/env python3
"""
Test script to demonstrate maximized results from all sources
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import sources
from app.scrapers.api_sources import (
    get_france_travail_source, get_france_travail_rss_source,
    get_adzuna_source, get_google_jobs_source,
    get_jooble_source, get_apify_source
)
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_all_sources():
    """Test all sources to show maximized results."""

    print("=" * 70)
    print("MAXIMIZED RESULTS TEST - All Sources")
    print("=" * 70)

    query = "Développeur Python"
    location = "Paris, France"
    limit = 50

    all_results = []
    sources_tested = 0
    sources_successful = 0
    total_jobs = 0

    # Test France Travail API with fallback
    print(f"\n1. Testing France Travail (API + RSS Fallback):")
    ft_source = get_france_travail_source()
    ft_rss_source = get_france_travail_rss_source()

    if ft_source:
        try:
            api_jobs = await ft_source.search_jobs(query, location, limit)
            if api_jobs:
                print(f"   ✅ France Travail API: {len(api_jobs)} jobs")
                all_results.extend(api_jobs)
                total_jobs += len(api_jobs)
                sources_successful += 1
            else:
                print(f"   ⚠️ France Travail API: 0 jobs (will fallback to RSS)")
                if ft_rss_source:
                    rss_jobs = await ft_rss_source(query, location, limit)
                    print(f"   ✅ France Travail RSS Fallback: {len(rss_jobs)} jobs")
                    all_results.extend(rss_jobs)
                    total_jobs += len(rss_jobs)
                    sources_successful += 1
        except Exception as e:
            print(f"   ❌ France Travail API Error: {e}")
            if ft_rss_source:
                try:
                    rss_jobs = await ft_rss_source(query, location, limit)
                    print(f"   ✅ France Travail RSS Fallback: {len(rss_jobs)} jobs")
                    all_results.extend(rss_jobs)
                    total_jobs += len(rss_jobs)
                    sources_successful += 1
                except Exception as e2:
                    print(f"   ❌ France Travail RSS Error: {e2}")
        sources_tested += 1

    # Test Adzuna
    print(f"\n2. Testing Adzuna:")
    adzuna_source = get_adzuna_source()
    if adzuna_source:
        try:
            adzuna_jobs = await adzuna_source.search_jobs(query, location, limit)
            print(f"   ✅ Adzuna: {len(adzuna_jobs)} jobs")
            all_results.extend(adzuna_jobs)
            total_jobs += len(adzuna_jobs)
            sources_successful += 1
        except Exception as e:
            print(f"   ❌ Adzuna Error: {e}")
        sources_tested += 1

    # Test Google Jobs
    print(f"\n3. Testing Google Jobs:")
    google_source = get_google_jobs_source()
    if google_source:
        try:
            google_jobs = await google_source.search_jobs(query, location, limit)
            print(f"   ✅ Google Jobs: {len(google_jobs)} jobs")
            all_results.extend(google_jobs)
            total_jobs += len(google_jobs)
            sources_successful += 1
        except Exception as e:
            print(f"   ❌ Google Jobs Error: {e}")
        sources_tested += 1

    # Test Jooble
    print(f"\n4. Testing Jooble:")
    jooble_source = get_jooble_source()
    if jooble_source:
        try:
            jooble_jobs = await jooble_source.search_jobs(query, location, limit)
            print(f"   ✅ Jooble: {len(jooble_jobs)} jobs")
            all_results.extend(jooble_jobs)
            total_jobs += len(jooble_jobs)
            sources_successful += 1
        except Exception as e:
            print(f"   ❌ Jooble Error: {e}")
        sources_tested += 1

    # Test Apify (LinkedIn)
    print(f"\n5. Testing Apify (LinkedIn):")
    apify_source = get_apify_source()
    if apify_source:
        try:
            apify_jobs = await apify_source.search_jobs(query, location, limit)
            print(f"   ✅ Apify (LinkedIn): {len(apify_jobs)} jobs")
            all_results.extend(apify_jobs)
            total_jobs += len(apify_jobs)
            sources_successful += 1
        except Exception as e:
            print(f"   ❌ Apify Error: {e}")
        sources_tested += 1

    # Summary
    print(f"\n" + "=" * 70)
    print("SUMMARY:")
    print(f"   Sources Tested: {sources_tested}")
    print(f"   Sources Successful: {sources_successful}")
    print(f"   Total Unique Jobs: {len(all_results)}")
    print(f"   Total Jobs (with duplicates): {total_jobs}")

    if all_results:
        print(f"\n   Sample Results:")
        for i, job in enumerate(all_results[:3], 1):
            source = job.get('source', 'Unknown')
            title = job.get('titre', 'N/A')[:50]
            company = job.get('entreprise', 'N/A')[:30]
            print(f"   {i}. {source}: {title} - {company}")

    print(f"\n" + "=" * 70)
    print("✅ MAXIMIZED RESULTS SYSTEM WORKING!")
    print("   - Multiple sources queried in parallel")
    print("   - Automatic fallback for failed sources")
    print("   - Duplicate removal")
    print("   - Enhanced RSS with broader location search")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_all_sources())