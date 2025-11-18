# Backend Test Suite

Comprehensive test suite for the Claude Agent backend API.

## Overview

This test suite includes:
- **Unit tests**: Testing individual components and functions
- **Integration tests**: Testing API endpoints with mocked dependencies
- **E2E tests**: Testing complete conversation flows

**Total Tests**: 43
**Execution Time**: ~0.2 seconds (well under 1 minute)

## Running Tests

### Install Dependencies

```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -v -m unit

# Integration tests only
pytest -v -m integration

# E2E tests only
pytest -v -m e2e
```

### Run Specific Test Files

```bash
# Test models only
pytest -v tests/test_models.py

# Test API endpoints only
pytest -v tests/test_api.py

# Test helper functions only
pytest -v tests/test_helpers.py

# Test E2E flows only
pytest -v tests/test_e2e.py
```

### Coverage Report

```bash
pytest --cov=. --cov-report=html
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and test configuration
├── test_models.py        # Unit tests for Pydantic models (13 tests)
├── test_helpers.py       # Unit tests for helper functions (9 tests)
├── test_api.py          # Integration tests for API endpoints (12 tests)
└── test_e2e.py          # E2E tests for conversation flows (9 tests)
```

## Test Coverage

### Unit Tests (test_models.py)
- ✅ OutputTextContent validation
- ✅ MessageOutput validation
- ✅ UsageInfo validation
- ✅ ResponseObject validation
- ✅ CreateResponseRequest validation
- ✅ Streaming event models

### Unit Tests (test_helpers.py)
- ✅ create_client with/without session resume
- ✅ create_client with streaming enabled
- ✅ call_claude_agent success scenarios
- ✅ call_claude_agent edge cases (no text, multiple blocks)
- ✅ Conversation storage functionality

### Integration Tests (test_api.py)
- ✅ Health check endpoint
- ✅ Create response (non-streaming)
- ✅ Create response (streaming with SSE)
- ✅ Conversation storage and retrieval
- ✅ Multi-turn conversations with previous_response_id
- ✅ Error handling (invalid IDs, missing fields, agent errors)
- ✅ Get stored response endpoint

### E2E Tests (test_e2e.py)
- ✅ Simple single-turn conversation
- ✅ Multi-turn conversations (2 and 3 turns)
- ✅ Streaming conversations
- ✅ Multi-turn streaming
- ✅ Error handling and recovery

## Fixtures

### Shared Fixtures (conftest.py)

- `mock_claude_client`: Mock Claude SDK client
- `mock_assistant_message`: Mock AssistantMessage
- `mock_result_message`: Mock ResultMessage with usage
- `mock_stream_event`: Mock streaming event
- `test_client`: AsyncClient for testing FastAPI app
- `sample_request_data`: Sample request payload
- `sample_response_data`: Sample response data

## Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests

## Mock Strategy

The test suite uses `unittest.mock` to mock external dependencies:

1. **Claude SDK Client**: Mocked to avoid actual API calls
2. **Network Requests**: All API calls use in-memory test client
3. **Conversation Storage**: Reset before each test to ensure isolation

## Performance

All tests use mocks and run in-memory, ensuring fast execution:
- No actual network calls
- No external service dependencies
- Sequential execution (no parallelization needed)
- Total runtime: ~0.2 seconds

## Continuous Integration

This test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    cd backend
    pytest -v
```

## Adding New Tests

1. Add test functions to appropriate file based on category
2. Use existing fixtures from `conftest.py`
3. Mark tests with appropriate markers (`@pytest.mark.unit`, etc.)
4. Follow naming convention: `test_<what_is_being_tested>`
5. Include docstrings describing the test scenario

## Troubleshooting

### Tests Fail to Import

Ensure you've installed the package in editable mode:
```bash
uv pip install -e ".[dev]"
```

### Async Tests Fail

The test suite uses `pytest-asyncio` with auto mode. Check that:
- `pytest.ini` has `asyncio_mode = auto`
- Test functions use `async def`
- Test client fixture is properly awaited

### Mocks Not Working

Verify the patch path matches the import path in `main.py`:
```python
@patch("main.call_claude_agent")  # Correct
# NOT @patch("backend.main.call_claude_agent")
```
