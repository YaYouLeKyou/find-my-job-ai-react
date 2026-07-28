import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

# Neutraliser le rate limiter pour éviter les HTTP 429
app.state.limiter.enabled = False

def parse_sse_events(text: str):
    events = []
    current_event = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current_event["event"] = line[6:].strip()
        elif line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
                if "event" in current_event:
                    data["event_type"] = current_event["event"]
                events.append(data)
            except Exception:
                pass
            current_event = {}
    return events

class TestSSEEvents:
    def _parse_sse_events(self, text: str):
        return parse_sse_events(text)

class TestErrorHandling:
    def _parse_sse_events(self, text: str):
        return parse_sse_events(text)

class TestIntegration:
    def _parse_sse_events(self, text: str):
        return parse_sse_events(text)

def test_stream_started_event():
    client = TestClient(app)
    
    # Inspecter automatiquement les routes déclarées dans FastAPI
    stream_route = None
    for route in app.routes:
        if hasattr(route, "path") and "stream" in route.path:
            stream_route = route.path
            break
            
    # Route par défaut si non trouvée automatiquement
    target_url = stream_route or "/api/v1/jobs/stream"
    
    response = client.get(f"{target_url}?query=python")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"].lower()