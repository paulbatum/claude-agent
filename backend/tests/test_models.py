"""Unit tests for Pydantic models."""
import pytest
from pydantic import ValidationError
from .test_config import DEFAULT_MODEL
from main import (
    OutputTextContent,
    MessageOutput,
    UsageInfo,
    ResponseObject,
    CreateResponseRequest,
    ResponseCreatedEvent,
    ResponseOutputTextDeltaEvent,
)


@pytest.mark.unit
class TestOutputTextContent:
    """Test OutputTextContent model."""

    def test_create_valid_content(self):
        """Test creating valid output text content."""
        content = OutputTextContent(text="Hello, world!")
        assert content.type == "output_text"
        assert content.text == "Hello, world!"
        assert content.annotations == []

    def test_default_annotations(self):
        """Test default empty annotations list."""
        content = OutputTextContent(text="Test")
        assert isinstance(content.annotations, list)
        assert len(content.annotations) == 0

    def test_with_annotations(self):
        """Test content with annotations."""
        content = OutputTextContent(
            text="Test",
            annotations=["annotation1", "annotation2"]
        )
        assert len(content.annotations) == 2


@pytest.mark.unit
class TestMessageOutput:
    """Test MessageOutput model."""

    def test_create_valid_message(self):
        """Test creating valid message output."""
        content = OutputTextContent(text="Hello!")
        message = MessageOutput(
            id="msg_123",
            content=[content]
        )
        assert message.type == "message"
        assert message.id == "msg_123"
        assert message.status == "completed"
        assert message.role == "assistant"
        assert len(message.content) == 1

    def test_multiple_content_blocks(self):
        """Test message with multiple content blocks."""
        message = MessageOutput(
            id="msg_123",
            content=[
                OutputTextContent(text="Part 1"),
                OutputTextContent(text="Part 2"),
            ]
        )
        assert len(message.content) == 2


@pytest.mark.unit
class TestUsageInfo:
    """Test UsageInfo model."""

    def test_create_valid_usage(self):
        """Test creating valid usage info."""
        usage = UsageInfo(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300
        )
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.total_tokens == 300

    def test_zero_tokens(self):
        """Test usage with zero tokens."""
        usage = UsageInfo(
            input_tokens=0,
            output_tokens=0,
            total_tokens=0
        )
        assert usage.input_tokens == 0
        assert usage.total_tokens == 0


@pytest.mark.unit
class TestResponseObject:
    """Test ResponseObject model."""

    def test_create_valid_response(self):
        """Test creating valid response object."""
        content = OutputTextContent(text="Hello!")
        message = MessageOutput(id="msg_123", content=[content])
        usage = UsageInfo(input_tokens=10, output_tokens=20, total_tokens=30)

        response = ResponseObject(
            id="resp_123",
            created_at=1234567890,
            status="completed",
            model=DEFAULT_MODEL,
            output=[message],
            usage=usage
        )

        assert response.id == "resp_123"
        assert response.object == "response"
        assert response.status == "completed"
        assert response.store is True
        assert len(response.output) == 1

    def test_default_metadata(self):
        """Test default empty metadata dict."""
        content = OutputTextContent(text="Test")
        message = MessageOutput(id="msg_123", content=[content])
        usage = UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2)

        response = ResponseObject(
            id="resp_123",
            created_at=1234567890,
            model=DEFAULT_MODEL,
            output=[message],
            usage=usage
        )

        assert isinstance(response.metadata, dict)
        assert len(response.metadata) == 0

    def test_with_metadata(self):
        """Test response with metadata."""
        content = OutputTextContent(text="Test")
        message = MessageOutput(id="msg_123", content=[content])
        usage = UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2)

        response = ResponseObject(
            id="resp_123",
            created_at=1234567890,
            model=DEFAULT_MODEL,
            output=[message],
            usage=usage,
            metadata={"test_key": "test_value"}
        )

        assert response.metadata["test_key"] == "test_value"


@pytest.mark.unit
class TestCreateResponseRequest:
    """Test CreateResponseRequest model."""

    def test_create_minimal_request(self):
        """Test creating request with minimal required fields."""
        request = CreateResponseRequest(
            model=DEFAULT_MODEL,
            input="Hello!"
        )
        assert request.model == DEFAULT_MODEL
        assert request.input == "Hello!"
        assert request.stream is False
        assert request.store is True
        assert request.previous_response_id is None
        assert request.temperature == 1.0
        assert request.max_output_tokens is None

    def test_create_full_request(self):
        """Test creating request with all fields."""
        request = CreateResponseRequest(
            model=DEFAULT_MODEL,
            input="Hello!",
            stream=True,
            store=False,
            previous_response_id="resp_abc123",
            temperature=0.7,
            max_output_tokens=1000
        )
        assert request.stream is True
        assert request.store is False
        assert request.previous_response_id == "resp_abc123"
        assert request.temperature == 0.7
        assert request.max_output_tokens == 1000

    def test_missing_required_fields(self):
        """Test that missing required fields raises validation error."""
        with pytest.raises(ValidationError):
            CreateResponseRequest(model=DEFAULT_MODEL)

        with pytest.raises(ValidationError):
            CreateResponseRequest(input="Hello!")


@pytest.mark.unit
class TestStreamingEvents:
    """Test streaming event models."""

    def test_response_created_event(self):
        """Test ResponseCreatedEvent model."""
        content = OutputTextContent(text="Test")
        message = MessageOutput(id="msg_123", content=[content])
        usage = UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2)
        response = ResponseObject(
            id="resp_123",
            created_at=1234567890,
            model=DEFAULT_MODEL,
            output=[message],
            usage=usage
        )

        event = ResponseCreatedEvent(
            response=response,
            sequence_number=0
        )

        assert event.type == "response.created"
        assert event.sequence_number == 0
        assert event.response.id == "resp_123"

    def test_output_text_delta_event(self):
        """Test ResponseOutputTextDeltaEvent model."""
        event = ResponseOutputTextDeltaEvent(
            item_id="msg_123",
            output_index=0,
            content_index=0,
            delta="Hello",
            sequence_number=5
        )

        assert event.type == "response.output_text.delta"
        assert event.item_id == "msg_123"
        assert event.delta == "Hello"
        assert event.sequence_number == 5
