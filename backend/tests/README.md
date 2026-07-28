# Test Suite for FindMyJobAI Backend

## 📋 Overview

This test suite validates the new modular architecture with a focus on:
- **AI Scoring performance** (TF-IDF + Cosine Similarity)
- **SSE Streaming endpoint** (`/api/jobs/stream`)
- **Timeout handling** and error resilience
- **Job normalization** and data quality

## 🧪 Test Files

### `test_scorer.py`
Tests for the AI scoring service (`app/services/scorer.py`):

- ✅ **Score Range Validation**: Ensures scores are between 10-100
- ✅ **Performance Tests**: Validates < 50ms per job (batch of 50 and 100 jobs)
- ✅ **Sorting Tests**: Verifies descending order by score
- ✅ **Quality Tests**: Confirms relevant jobs score higher than irrelevant ones
- ✅ **Edge Cases**: Handles empty CV data, missing fields, etc.

### `test_stream.py`
Tests for the SSE streaming endpoint (`app/main.py`):

- ✅ **SSE Events**: Validates STARTED, PROGRESS, SCORES_UPDATED, COMPLETED events
- ✅ **Timeout Handling**: Ensures slow scrapers don't block others
- ✅ **Error Handling**: Verifies ERROR events on exceptions
- ✅ **Job Normalization**: Checks required fields and CV scoring integration
- ✅ **Integration Tests**: Full flow with multiple sources

## 🚀 Running the Tests

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
# Test scorer only
pytest tests/test_scorer.py -v

# Test streaming only
pytest tests/test_stream.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Performance Tests
```bash
# Run only performance tests
pytest tests/test_scorer.py::TestPerformance -v

# Run with timing output
pytest tests/test_scorer.py::TestPerformance -v -s
```

## 📊 Test Coverage

### Scorer Tests (15 tests)
- `TestScoreRange`: 3 tests
- `TestPerformance`: 3 tests (including 50-job and 100-job batches)
- `TestSorting`: 2 tests
- `TestScoreQuality`: 3 tests
- `TestEdgeCases`: 4 tests
- `TestConvenienceFunction`: 2 tests

### Stream Tests (10 tests)
- `TestHealthCheck`: 1 test
- `TestSSEEvents`: 4 tests
- `TestTimeoutHandling`: 2 tests
- `TestJobNormalization`: 2 tests
- `TestErrorHandling`: 1 test
- `TestIntegration`: 2 tests

**Total: 25 tests**

## 🎯 Key Assertions

### Scorer Performance
```python
# Single job: < 50ms
assert elapsed < 0.05, f"Took {elapsed*1000:.1f}ms (target: <50ms)"

# Batch: < 50ms per job on average
avg_time_ms = (elapsed / 50) * 1000
assert avg_time_ms < 50, f"Average {avg_time_ms:.1f}ms/job exceeds 50ms"
```

### SSE Events
```python
# STARTED event
assert event["type"] == "STARTED"
assert event["query"] == "developer"
assert event["total_sources"] == 2

# PROGRESS events
assert len(progress_events) == 2  # One per source

# COMPLETED event
assert completed["progress"] == 100
assert "jobs" in completed
assert "source_status" in completed
```

### Timeout Handling
```python
# Should complete despite timeout
assert len(completed_events) > 0

# Other sources should succeed
assert linkedin_events[0]["status"] == "completed"

# Timed out source should report error
assert indeed_events[0]["status"] == "error"
```

## 🔧 Configuration

### pytest.ini (optional)
Create a `pytest.ini` file in the `backend/` directory:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
asyncio_mode = auto
```

### Environment Variables
Tests use mocked scrapers, so no API keys are required. However, for integration tests:

```bash
# Optional: Set these for full integration testing
export FRANCE_TRAVAIL_CLIENT_ID="your_client_id"
export FRANCE_TRAVAIL_CLIENT_SECRET="your_client_secret"
```

## 📝 Notes

- **Pylance errors** in VS Code are expected if dependencies aren't installed. Run `pip install -r requirements.txt` to resolve.
- Tests use **mocks** for scrapers to avoid network calls and ensure fast execution.
- The timeout test (`test_timeout_doesnt_block_other_sources`) uses a 10-second sleep to simulate a slow scraper. The aggregator timeout is 6 seconds by default.
- All tests are **independent** and can run in any order.
- The test suite follows **TDD principles**: tests are written before implementation (or alongside it).

## 🐛 Troubleshooting

### Import Errors
If you get import errors, ensure the backend directory is in your Python path:
```bash
export PYTHONPATH=/path/to/ai-find-a-job/backend:$PYTHONPATH
```

### Timeout Test Failures
If the timeout test fails, increase the TestClient timeout:
```python
response = client.get(..., timeout=20)  # Increase from 15 to 20 seconds
```

### Scoring Performance Failures
If scoring tests fail on slow machines, adjust the threshold:
```python
# In test_scorer.py, change 50ms to 100ms for slower machines
assert avg_time_ms < 100, f"Average {avg_time_ms:.1f}ms/job exceeds 100ms threshold"
```

## 📈 Continuous Integration

Example GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3