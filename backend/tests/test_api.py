"""Integration tests for API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from .test_config import DEFAULT_MODEL
from main import session_ids, conversations
from claude_agent_sdk import AssistantMessage, TextBlock, ResultMessage


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    async def test_health_check(self, test_client):
        """Test health check returns OK."""
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "claude-agent-api"


@pytest.mark.integration
class TestCreateResponseEndpoint:
    """Test /v1/responses endpoint."""

    @patch("main.call_claude_agent")
    async def test_create_simple_response(
        self,
        mock_call_agent,
        test_client,
        sample_request_data,
        sample_response_data
    ):
        """Test creating a simple non-streaming response."""
        mock_call_agent.return_value = sample_response_data

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["object"] == "response"
        assert data["status"] == "completed"
        assert data["model"] == sample_request_data["model"]
        assert "id" in data
        assert data["id"].startswith("resp_")

        # Verify output structure
        assert len(data["output"]) == 1
        message = data["output"][0]
        assert message["type"] == "message"
        assert message["role"] == "assistant"
        assert message["status"] == "completed"
        assert len(message["content"]) == 1
        assert message["content"][0]["text"] == sample_response_data["text"]

        # Verify usage
        assert data["usage"]["input_tokens"] == 10
        assert data["usage"]["output_tokens"] == 20
        assert data["usage"]["total_tokens"] == 30

    @patch("main.call_claude_agent")
    async def test_create_response_stores_conversation(
        self,
        mock_call_agent,
        test_client,
        sample_request_data,
        sample_response_data
    ):
        """Test that conversation is stored when store=True."""
        mock_call_agent.return_value = sample_response_data

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 200
        data = response.json()
        response_id = data["id"]

        # Verify conversation was stored
        assert response_id in conversations
        assert response_id in session_ids
        assert session_ids[response_id] == "test_session_123"

    @patch("main.call_claude_agent")
    async def test_create_response_no_store(
        self,
        mock_call_agent,
        test_client,
        sample_request_data,
        sample_response_data
    ):
        """Test that conversation is not stored when store=False."""
        mock_call_agent.return_value = sample_response_data
        sample_request_data["store"] = False

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 200
        data = response.json()
        response_id = data["id"]

        # Verify conversation was NOT stored
        assert response_id not in conversations
        assert response_id not in session_ids

    @patch("main.call_claude_agent")
    async def test_create_response_with_previous_id(
        self,
        mock_call_agent,
        test_client,
        sample_request_data,
        sample_response_data
    ):
        """Test creating response with previous_response_id."""
        # First, create an initial response
        mock_call_agent.return_value = sample_response_data
        first_response = await test_client.post("/v1/responses", json=sample_request_data)
        first_data = first_response.json()
        first_id = first_data["id"]

        # Now create a follow-up response
        followup_data = sample_response_data.copy()
        followup_data["text"] = "This is a follow-up response."
        mock_call_agent.return_value = followup_data

        followup_request = sample_request_data.copy()
        followup_request["input"] = "What did we talk about?"
        followup_request["previous_response_id"] = first_id

        response = await test_client.post("/v1/responses", json=followup_request)

        assert response.status_code == 200
        data = response.json()
        assert data["output"][0]["content"][0]["text"] == "This is a follow-up response."

        # Verify call_claude_agent was called with previous_response_id
        mock_call_agent.assert_called_with(
            user_input="What did we talk about?",
            model=sample_request_data["model"],
            previous_response_id=first_id
        )

    async def test_invalid_previous_response_id(self, test_client, sample_request_data):
        """Test error handling for invalid previous_response_id."""
        sample_request_data["previous_response_id"] = "resp_nonexistent"

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    async def test_missing_required_fields(self, test_client):
        """Test validation error for missing required fields."""
        # Missing 'input' field
        response = await test_client.post("/v1/responses", json={
            "model": DEFAULT_MODEL
        })
        assert response.status_code == 422

        # Missing 'model' field
        response = await test_client.post("/v1/responses", json={
            "input": "Hello!"
        })
        assert response.status_code == 422

    @patch("main.call_claude_agent")
    async def test_agent_error_handling(
        self,
        mock_call_agent,
        test_client,
        sample_request_data
    ):
        """Test error handling when Claude agent fails."""
        mock_call_agent.side_effect = Exception("Claude SDK error")

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 500
        data = response.json()
        assert "Claude Agent error" in data["detail"]


@pytest.mark.integration
class TestGetResponseEndpoint:
    """Test /v1/responses/{response_id} endpoint."""

    @patch("main.call_claude_agent")
    async def test_get_stored_response(
        self,
        mock_call_agent,
        test_client,
        sample_request_data,
        sample_response_data
    ):
        """Test retrieving a stored response."""
        mock_call_agent.return_value = sample_response_data

        # First create a response
        create_response = await test_client.post("/v1/responses", json=sample_request_data)
        created_data = create_response.json()
        response_id = created_data["id"]

        # Now retrieve it
        get_response = await test_client.get(f"/v1/responses/{response_id}")

        assert get_response.status_code == 200
        retrieved_data = get_response.json()

        # Verify it matches the created response
        assert retrieved_data["id"] == response_id
        assert retrieved_data["model"] == created_data["model"]
        assert retrieved_data["output"] == created_data["output"]

    async def test_get_nonexistent_response(self, test_client):
        """Test retrieving a non-existent response."""
        response = await test_client.get("/v1/responses/resp_nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


@pytest.mark.integration
class TestStreamingResponse:
    """Test streaming response endpoint."""

    @patch("main.create_client")
    async def test_streaming_response(
        self,
        mock_create_client,
        test_client,
        sample_request_data
    ):
        """Test streaming response returns SSE events."""
        # Create mock client with streaming
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Mock streaming response
        async def mock_receive():
            # Yield a stream event
            stream_event = MagicMock()
            stream_event.event = {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "Hello"}
            }
            type(stream_event).__name__ = "StreamEvent"
            yield stream_event

            # Yield assistant message
            msg = MagicMock(spec=AssistantMessage)
            msg.content = [TextBlock(text="Hello")]
            yield msg

            # Yield result message
            result_msg = MagicMock(spec=ResultMessage)
            result_msg.usage = {"input_tokens": 10, "output_tokens": 5}
            result_msg.session_id = "test_session"
            yield result_msg

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        # Enable streaming
        sample_request_data["stream"] = True

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        content = response.text
        events = []
        for line in content.split("\n\n"):
            if line.startswith("event:"):
                event_type = line.split("\n")[0].replace("event: ", "").strip()
                events.append(event_type)

        # Verify expected events
        assert "response.created" in events
        assert "response.in_progress" in events
        assert "response.output_item.added" in events
        assert "response.content_part.added" in events
        assert "response.output_text.delta" in events
        assert "response.output_text.done" in events
        assert "response.completed" in events

    @patch("main.create_client")
    async def test_streaming_stores_conversation(
        self,
        mock_create_client,
        test_client,
        sample_request_data
    ):
        """Test that streaming response stores conversation."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_receive():
            msg = MagicMock(spec=AssistantMessage)
            msg.content = [TextBlock(text="Streaming response")]
            yield msg

            result_msg = MagicMock(spec=ResultMessage)
            result_msg.usage = {"input_tokens": 10, "output_tokens": 15}
            result_msg.session_id = "stream_session_123"
            yield result_msg

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        sample_request_data["stream"] = True

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 200

        # Extract response ID from the SSE events
        content = response.text
        # Look for response.created event to get the response ID
        import json
        for line in content.split("\n"):
            if line.startswith("data:"):
                data = json.loads(line.replace("data: ", ""))
                if data.get("type") == "response.created":
                    response_id = data["response"]["id"]
                    # Verify it was stored
                    assert response_id in conversations
                    assert response_id in session_ids
                    break
