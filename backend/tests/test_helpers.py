"""Unit tests for helper functions."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from main import (
    create_client,
    call_claude_agent,
    session_ids,
    conversations,
)
from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ResultMessage,
)


@pytest.mark.unit
class TestCreateClient:
    """Test create_client function."""

    @patch("main.ClaudeSDKClient")
    async def test_create_new_client(self, mock_client_class):
        """Test creating a new client without previous session."""
        mock_instance = AsyncMock()
        mock_instance.connect = AsyncMock()
        mock_client_class.return_value = mock_instance

        client = await create_client(
            model="claude-haiku-4-5-20251001",
            previous_response_id=None
        )

        assert client is not None
        mock_instance.connect.assert_called_once()
        mock_client_class.assert_called_once()

        # Verify options passed to client
        call_args = mock_client_class.call_args
        options = call_args.kwargs["options"]
        assert options.model == "claude-haiku-4-5-20251001"
        assert options.resume is None

    @patch("main.ClaudeSDKClient")
    async def test_create_client_with_resume(self, mock_client_class):
        """Test creating a client with previous session."""
        # Set up a previous session
        session_ids["resp_123"] = "session_abc"

        mock_instance = AsyncMock()
        mock_instance.connect = AsyncMock()
        mock_client_class.return_value = mock_instance

        client = await create_client(
            model="claude-haiku-4-5-20251001",
            previous_response_id="resp_123"
        )

        # Verify resume was passed
        call_args = mock_client_class.call_args
        options = call_args.kwargs["options"]
        assert options.resume == "session_abc"

        # Clean up
        session_ids.clear()

    @patch("main.ClaudeSDKClient")
    async def test_create_client_with_streaming(self, mock_client_class):
        """Test creating a client with streaming enabled."""
        mock_instance = AsyncMock()
        mock_instance.connect = AsyncMock()
        mock_client_class.return_value = mock_instance

        client = await create_client(
            model="claude-haiku-4-5-20251001",
            enable_streaming=True
        )

        # Verify streaming was enabled
        call_args = mock_client_class.call_args
        options = call_args.kwargs["options"]
        assert options.include_partial_messages is True


@pytest.mark.unit
class TestCallClaudeAgent:
    """Test call_claude_agent function."""

    @patch("main.create_client")
    async def test_successful_response(
        self,
        mock_create_client,
        mock_assistant_message,
        mock_result_message
    ):
        """Test successful agent call."""
        # Create mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Mock the response stream
        async def mock_receive():
            yield mock_assistant_message
            yield mock_result_message

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        # Call the function
        result = await call_claude_agent(
            user_input="Hello!",
            model="claude-haiku-4-5-20251001"
        )

        # Verify results
        assert result["text"] == "Hello! I'm Claude, an AI assistant."
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 20
        assert result["session_id"] == "test_session_123"

        # Verify client interactions
        mock_client.query.assert_called_once_with("Hello!")
        mock_client.disconnect.assert_called_once()

    @patch("main.create_client")
    async def test_no_text_response(self, mock_create_client):
        """Test handling when no text is returned."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Mock empty response
        async def mock_receive():
            msg = MagicMock(spec=ResultMessage)
            msg.usage = {"input_tokens": 5, "output_tokens": 0}
            msg.session_id = "test_session"
            yield msg

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        result = await call_claude_agent(
            user_input="Hello!",
            model="claude-haiku-4-5-20251001"
        )

        # Should return default message when no text
        assert result["text"] == "No response generated"
        assert result["input_tokens"] == 5
        assert result["output_tokens"] == 0

    @patch("main.create_client")
    async def test_with_previous_response_id(self, mock_create_client):
        """Test calling with previous response ID."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_receive():
            msg = MagicMock(spec=AssistantMessage)
            msg.content = [TextBlock(text="Continuing conversation")]
            yield msg

            result_msg = MagicMock(spec=ResultMessage)
            result_msg.usage = {"input_tokens": 15, "output_tokens": 25}
            result_msg.session_id = "session_continue"
            yield result_msg

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        result = await call_claude_agent(
            user_input="What did we discuss?",
            model="claude-haiku-4-5-20251001",
            previous_response_id="resp_abc123"
        )

        # Verify create_client was called with previous_response_id
        mock_create_client.assert_called_once()
        call_args = mock_create_client.call_args
        # Check if passed as positional or keyword argument
        if "previous_response_id" in call_args.kwargs:
            assert call_args.kwargs["previous_response_id"] == "resp_abc123"
        else:
            # Should be second positional argument
            assert call_args.args[1] == "resp_abc123"

        assert result["text"] == "Continuing conversation"

    @patch("main.create_client")
    async def test_multiple_text_blocks(self, mock_create_client):
        """Test handling multiple text blocks in response."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_receive():
            msg = MagicMock(spec=AssistantMessage)
            msg.content = [
                TextBlock(text="First part. "),
                TextBlock(text="Second part.")
            ]
            yield msg

            result_msg = MagicMock(spec=ResultMessage)
            result_msg.usage = {"input_tokens": 10, "output_tokens": 20}
            result_msg.session_id = "test_session"
            yield result_msg

        mock_client.receive_response = mock_receive
        mock_create_client.return_value = mock_client

        result = await call_claude_agent(
            user_input="Tell me something",
            model="claude-haiku-4-5-20251001"
        )

        # Text blocks should be concatenated
        assert result["text"] == "First part. Second part."


@pytest.mark.unit
class TestConversationStorage:
    """Test conversation storage functionality."""

    def test_session_ids_storage(self):
        """Test storing and retrieving session IDs."""
        session_ids.clear()

        session_ids["resp_123"] = "session_abc"
        session_ids["resp_456"] = "session_def"

        assert session_ids["resp_123"] == "session_abc"
        assert session_ids["resp_456"] == "session_def"
        assert len(session_ids) == 2

        session_ids.clear()

    def test_conversations_storage(self):
        """Test storing and retrieving conversations."""
        conversations.clear()

        conversations["resp_123"] = {
            "request": {"model": "claude-haiku-4-5-20251001", "input": "Hello"},
            "response": {"id": "resp_123", "output": []}
        }

        assert "resp_123" in conversations
        assert conversations["resp_123"]["request"]["input"] == "Hello"

        conversations.clear()
