#!/usr/bin/env python3
"""
Test API keys for job search sources
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

# Disable rate limiting for testing
os.environ["PYTEST_CURRENT_TEST"] = "1"

from fastapi.testclient import TestClient
from app.main import app

if hasattr(app.state, 'limiter'):
    app.state.limiter.enabled = False
client = TestClient(app)

SOURCES_TO_TEST = [
    "France Travail",
    "Adzuna",
    "SerpAPI",
    "Jooble",
    "Apify",
]

def test_source(source_name):
    print(f"\n[TEST] {source_name}...")
    url = "/api/jobs/stream"
    params = {
        "query": "python developer",
        "location": "Paris, France",
        "num_ads": 3,
        "selected_sources": source_name,
    }
    
    try:
        response = client.get(url, params=params, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            events = []
            current_event = {}
            for line in response.text.splitlines():
                line = line.strip()
                if line.startswith("event:"):
                    current_event["event"] = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        import json
                        data = json.loads(line[5:].strip())
                        if "event" in current_event:
                            data["event_type"] = current_event["event"]
                        events.append(data)
                    except Exception:
                        pass
                    current_event = {}
            
            for event in events:
                if event.get("source") == source_name or source_name.lower() in str(event).lower():
                    print(f"   Response: {event}")
                    if event.get("status") == "completed" and event.get("jobs"):
                        print(f"   [OK] {source_name}: {len(event['jobs'])} jobs found")
                        return True
                    elif event.get("status") == "error":
                        print(f"   [FAIL] {source_name}: Error - {event.get('error', 'Unknown')}")
                        return False
                    else:
                        print(f"   [WARN] {source_name}: No jobs or unclear status")
                        return False
            
            for event in events:
                if event.get("type") == "ERROR" or event.get("status") == "error":
                    print(f"   [FAIL] {source_name}: Error in stream - {event.get('message', event.get('error', 'Unknown'))}")
                    return False
            
            print(f"   [WARN] {source_name}: No specific event found in stream")
            return False
        else:
            print(f"   [FAIL] {source_name}: HTTP {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"   [FAIL] {source_name}: Exception - {e}")
        return False

if __name__ == "__main__":
    print("[START] Testing Source API Keys...")
    print("=" * 60)
    
    results = {}
    for source in SOURCES_TO_TEST:
        results[source] = test_source(source)
    
    print("\n" + "=" * 60)
    print("[RESULTS] Summary:")
    print("=" * 60)
    for source, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} - {source}")
    
    failed = [s for s, ok in results.items() if not ok]
    if failed:
        print(f"\n[WARN] Failed sources: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] All source APIs are working!")
        sys.exit(0)
