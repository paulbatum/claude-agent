"""Shared test fixtures and configuration."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from main import app, session_ids, conversations
from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ResultMessage,
)


@pytest.fixture
def mock_claude_client():
    """Mock Claude SDK client for testing."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def mock_assistant_message():
    """Create a mock AssistantMessage."""
    msg = MagicMock(spec=AssistantMessage)
    msg.content = [TextBlock(text="Hello! I'm Claude, an AI assistant.")]
    return msg


@pytest.fixture
def mock_result_message():
    """Create a mock ResultMessage."""
    msg = MagicMock(spec=ResultMessage)
    msg.usage = {"input_tokens": 10, "output_tokens": 20}
    msg.session_id = "test_session_123"
    return msg


@pytest.fixture
def mock_stream_event():
    """Create a mock streaming event."""
    event = MagicMock()
    event.event = {
        "type": "content_block_delta",
        "delta": {
            "type": "text_delta",
            "text": "Hello"
        }
    }
    # Make it not match known message types
    type(event).__name__ = "StreamEvent"
    return event


@pytest.fixture
async def test_client():
    """Create a test client for the FastAPI app."""
    # Clear conversation storage before each test
    session_ids.clear()
    conversations.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sample_request_data():
    """Sample request data for testing."""
    return {
        "model": "claude-haiku-4-5-20251001",
        "input": "Hello, how are you?",
        "stream": False,
        "store": True
    }


@pytest.fixture
def sample_response_data():
    """Sample response data for testing."""
    return {
        "text": "Hello! I'm Claude, an AI assistant.",
        "input_tokens": 10,
        "output_tokens": 20,
        "session_id": "test_session_123"
    }
