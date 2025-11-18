"""End-to-end tests for conversation flows."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from claude_agent_sdk import AssistantMessage, TextBlock, ResultMessage


@pytest.mark.e2e
class TestSimpleConversationFlow:
    """Test simple single-turn conversation."""

    @patch("main.call_claude_agent")
    async def test_complete_conversation_cycle(
        self,
        mock_call_agent,
        test_client,
        sample_request_data
    ):
        """Test a complete conversation cycle from request to response."""
        # Mock the agent response
        mock_call_agent.return_value = {
            "text": "Hello! I'm Claude, your AI assistant. How can I help you today?",
            "input_tokens": 15,
            "output_tokens": 25,
            "session_id": "session_e2e_123"
        }

        # Send request
        response = await test_client.post("/v1/responses", json=sample_request_data)

        # Verify successful response
        assert response.status_code == 200
        data = response.json()

        # Verify complete response structure
        assert data["status"] == "completed"
        assert data["object"] == "response"
        assert "id" in data
        assert "created_at" in data

        # Verify message content
        assert len(data["output"]) == 1
        message = data["output"][0]
        assert message["role"] == "assistant"
        assert message["status"] == "completed"
        assert len(message["content"]) == 1
        content = message["content"][0]
        assert content["type"] == "output_text"
        assert "Claude" in content["text"]

        # Verify usage tracking
        usage = data["usage"]
        assert usage["input_tokens"] == 15
        assert usage["output_tokens"] == 25
        assert usage["total_tokens"] == 40

        # Verify response can be retrieved
        response_id = data["id"]
        get_response = await test_client.get(f"/v1/responses/{response_id}")
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["id"] == response_id


@pytest.mark.e2e
class TestMultiTurnConversationFlow:
    """Test multi-turn conversation flow."""

    @patch("main.call_claude_agent")
    async def test_two_turn_conversation(
        self,
        mock_call_agent,
        test_client,
        sample_request_data
    ):
        """Test a two-turn conversation with context."""
        # First turn: User introduces themselves
        mock_call_agent.return_value = {
            "text": "Nice to meet you, Alice! How can I help you today?",
            "input_tokens": 20,
            "output_tokens": 15,
            "session_id": "session_turn1"
        }

        first_request = sample_request_data.copy()
        first_request["input"] = "Hi, my name is Alice"

        first_response = await test_client.post("/v1/responses", json=first_request)
        assert first_response.status_code == 200
        first_data = first_response.json()
        first_response_id = first_data["id"]

        # Verify first response
        assert "Alice" in first_data["output"][0]["content"][0]["text"]

        # Second turn: Ask a follow-up question
        mock_call_agent.return_value = {
            "text": "You said your name is Alice. Is there anything specific you'd like help with?",
            "input_tokens": 35,
            "output_tokens": 20,
            "session_id": "session_turn2"
        }

        second_request = sample_request_data.copy()
        second_request["input"] = "What's my name?"
        second_request["previous_response_id"] = first_response_id

        second_response = await test_client.post("/v1/responses", json=second_request)
        assert second_response.status_code == 200
        second_data = second_response.json()

        # Verify context was maintained
        assert "Alice" in second_data["output"][0]["content"][0]["text"]

        # Verify agent was called with previous_response_id
        assert mock_call_agent.call_count == 2
        second_call = mock_call_agent.call_args
        assert second_call.kwargs["previous_response_id"] == first_response_id

    @patch("main.call_claude_agent")
    async def test_three_turn_conversation(
        self,
        mock_call_agent,
        test_client,
        sample_request_data
    ):
        """Test a three-turn conversation maintaining context."""
        # Turn 1: Set context
        mock_call_agent.return_value = {
            "text": "Sure! I can help you learn Python.",
            "input_tokens": 10,
            "output_tokens": 10,
            "session_id": "session_py1"
        }

        turn1 = sample_request_data.copy()
        turn1["input"] = "I want to learn Python"
        response1 = await test_client.post("/v1/responses", json=turn1)
        assert response1.status_code == 200
        id1 = response1.json()["id"]

        # Turn 2: Ask specific question
        mock_call_agent.return_value = {
            "text": "A list in Python is a mutable, ordered collection of items.",
            "input_tokens": 25,
            "output_tokens": 15,
            "session_id": "session_py2"
        }

        turn2 = sample_request_data.copy()
        turn2["input"] = "What is a list?"
        turn2["previous_response_id"] = id1
        response2 = await test_client.post("/v1/responses", json=turn2)
        assert response2.status_code == 200
        id2 = response2.json()["id"]

        # Turn 3: Follow-up question
        mock_call_agent.return_value = {
            "text": "You create a list using square brackets: my_list = [1, 2, 3]",
            "input_tokens": 40,
            "output_tokens": 20,
            "session_id": "session_py3"
        }

        turn3 = sample_request_data.copy()
        turn3["input"] = "How do I create one?"
        turn3["previous_response_id"] = id2
        response3 = await test_client.post("/v1/responses", json=turn3)
        assert response3.status_code == 200
        data3 = response3.json()

        # Verify response contains relevant context
        assert "list" in data3["output"][0]["content"][0]["text"]
        assert mock_call_agent.call_count == 3


@pytest.mark.e2e
class TestStreamingConversationFlow:
    """Test streaming conversation flow."""

    @patch("main.create_client")
    async def test_streaming_conversation(
        self,
        mock_create_client,
        test_client,
        sample_request_data
    ):
        """Test a complete streaming conversation."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Mock streaming response with multiple deltas
        async def mock_receive():
            # Stream several text deltas
            for text in ["Hello", " ", "there", "!"]:
                event = MagicMock()
                event.event = {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": text}
                }
                type(event).__name__ = "StreamEvent"
                yield event

            # Final assistant message
            msg = MagicMock(spec=AssistantMessage)
            msg.content = [TextBlock(text="Hello there!")]
            yield msg

            # Result with usage
            result = MagicMock(spec=ResultMessage)
            result.usage = {"input_tokens": 5, "output_tokens": 3}
            result.session_id = "stream_session"
            yield result

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        # Enable streaming
        sample_request_data["stream"] = True

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 200
        content = response.text

        # Verify we got multiple delta events by counting event lines
        delta_count = content.count("event: response.output_text.delta")
        assert delta_count == 4  # One for each text chunk

        # Verify final text is assembled correctly
        assert "Hello there!" in content

        # Verify we got all expected event types
        assert "response.created" in content
        assert "response.completed" in content

    @patch("main.create_client")
    async def test_streaming_multi_turn(
        self,
        mock_create_client,
        test_client,
        sample_request_data
    ):
        """Test multi-turn conversation with streaming."""
        # First turn (streaming)
        mock_client1 = AsyncMock()
        mock_client1.query = AsyncMock()
        mock_client1.disconnect = AsyncMock()

        async def mock_receive1():
            event = MagicMock()
            event.event = {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "First response"}
            }
            type(event).__name__ = "StreamEvent"
            yield event

            msg = MagicMock(spec=AssistantMessage)
            msg.content = [TextBlock(text="First response")]
            yield msg

            result = MagicMock(spec=ResultMessage)
            result.usage = {"input_tokens": 10, "output_tokens": 5}
            result.session_id = "stream_multi_1"
            yield result

        mock_client1.receive_response = mock_receive1

        # Second turn (streaming)
        mock_client2 = AsyncMock()
        mock_client2.query = AsyncMock()
        mock_client2.disconnect = AsyncMock()

        async def mock_receive2():
            event = MagicMock()
            event.event = {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "Second response"}
            }
            type(event).__name__ = "StreamEvent"
            yield event

            msg = MagicMock(spec=AssistantMessage)
            msg.content = [TextBlock(text="Second response")]
            yield msg

            result = MagicMock(spec=ResultMessage)
            result.usage = {"input_tokens": 20, "output_tokens": 5}
            result.session_id = "stream_multi_2"
            yield result

        mock_client2.receive_response = mock_receive2

        # Configure mock to return different clients for each call
        mock_create_client.side_effect = [mock_client1, mock_client2]

        # First request
        sample_request_data["stream"] = True
        response1 = await test_client.post("/v1/responses", json=sample_request_data)
        assert response1.status_code == 200

        # Extract response ID from first response
        import json
        response_id = None
        for line in response1.text.split("\n"):
            if line.startswith("data:"):
                data = json.loads(line.replace("data: ", ""))
                if data.get("type") == "response.created":
                    response_id = data["response"]["id"]
                    break

        assert response_id is not None

        # Second request with previous_response_id
        second_request = sample_request_data.copy()
        second_request["previous_response_id"] = response_id
        response2 = await test_client.post("/v1/responses", json=second_request)

        assert response2.status_code == 200
        assert "Second response" in response2.text


@pytest.mark.e2e
class TestErrorHandlingFlow:
    """Test error handling in conversation flows."""

    async def test_conversation_with_invalid_previous_id(
        self,
        test_client,
        sample_request_data
    ):
        """Test that invalid previous_response_id is handled gracefully."""
        sample_request_data["previous_response_id"] = "resp_invalid_xyz"

        response = await test_client.post("/v1/responses", json=sample_request_data)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch("main.call_claude_agent")
    async def test_conversation_recovery_after_error(
        self,
        mock_call_agent,
        test_client,
        sample_request_data
    ):
        """Test that conversations can continue after an error."""
        # First request succeeds
        mock_call_agent.return_value = {
            "text": "First successful response",
            "input_tokens": 10,
            "output_tokens": 10,
            "session_id": "session_recovery1"
        }

        response1 = await test_client.post("/v1/responses", json=sample_request_data)
        assert response1.status_code == 200
        id1 = response1.json()["id"]

        # Second request fails
        mock_call_agent.side_effect = Exception("Temporary error")
        second_request = sample_request_data.copy()
        second_request["previous_response_id"] = id1

        response2 = await test_client.post("/v1/responses", json=second_request)
        assert response2.status_code == 500

        # Third request succeeds (can still use the first response ID)
        mock_call_agent.side_effect = None
        mock_call_agent.return_value = {
            "text": "Recovered successfully",
            "input_tokens": 15,
            "output_tokens": 10,
            "session_id": "session_recovery2"
        }

        third_request = sample_request_data.copy()
        third_request["previous_response_id"] = id1

        response3 = await test_client.post("/v1/responses", json=third_request)
        assert response3.status_code == 200
        data3 = response3.json()
        assert "Recovered" in data3["output"][0]["content"][0]["text"]
