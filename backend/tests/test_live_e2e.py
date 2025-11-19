"""
Live end-to-end tests that hit the real Claude API.
These tests are skipped if ANTHROPIC_API_KEY is not set.
"""
import os
import pytest
import json
from .test_config import DEFAULT_MODEL

# Skip all tests in this module if API key is missing
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set in environment"
    )
]


@pytest.mark.live
class TestLiveConversation:
    """Live tests against real Claude API."""

    async def test_simple_live_conversation(self, test_client, sample_request_data):
        """Test a simple conversation with the real API."""
        # Use model from environment
        sample_request_data["model"] = DEFAULT_MODEL
        sample_request_data["input"] = "Say 'hello world' and nothing else."
        
        # Ensure we are NOT mocking the client
        # The test_client fixture uses the app, which uses call_claude_agent
        # We just need to make sure we don't patch it
        
        response = await test_client.post("/v1/responses", json=sample_request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        assert len(data["output"]) > 0
        text = data["output"][0]["content"][0]["text"]
        assert "hello world" in text.lower()
        
        # Verify usage is real (non-zero)
        assert data["usage"]["input_tokens"] > 0
        assert data["usage"]["output_tokens"] > 0

    async def test_live_streaming_conversation(self, test_client, sample_request_data):
        """Test streaming conversation with real API."""
        sample_request_data["model"] = DEFAULT_MODEL
        sample_request_data["input"] = "Count from 1 to 3."
        sample_request_data["stream"] = True
        
        response = await test_client.post("/v1/responses", json=sample_request_data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        content = response.text
        events = []
        full_text = ""
        
        for line in content.split("\n"):
            if line.startswith("event: "):
                events.append(line.replace("event: ", "").strip())
            if line.startswith("data: "):
                data_str = line.replace("data: ", "")
                try:
                    data = json.loads(data_str)
                    if data.get("type") == "response.output_text.delta":
                        full_text += data.get("delta", "")
                except json.JSONDecodeError:
                    pass
        
        assert "response.created" in events
        assert "response.output_text.delta" in events
        assert "response.completed" in events
        
        assert "1" in full_text
        assert "2" in full_text
        assert "3" in full_text
