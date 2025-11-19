"""
Test multi-turn conversation streaming to reproduce the hang bug.
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default model from environment with fallback
DEFAULT_MODEL = os.getenv("MODEL_NAME", "claude-haiku-4-5-20251001")


async def read_sse_events(response, timeout_seconds=7):
    """Read SSE events from a streaming response with timeout."""
    import json
    events = []

    async def read_events():
        async for line in response.aiter_lines():
            if line.startswith('data: '):
                data = json.loads(line[6:])  # Remove 'data: ' prefix
                events.append(data)
                print(f"[DEBUG] Received event: {data.get('type')}")

                # Stop when we get response.completed
                if data.get('type') == 'response.completed':
                    break

    try:
        await asyncio.wait_for(read_events(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        print(f"[ERROR] Timeout after {timeout_seconds}s waiting for SSE events")
        print(f"[ERROR] Received {len(events)} events before timeout")
        raise AssertionError(f"Timeout after {timeout_seconds}s - only received {len(events)} events")

    return events


async def test_multi_turn_streaming():
    """Test that multi-turn conversations work with streaming."""
    print("[TEST] Starting test_multi_turn_streaming")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First request
        print("\n[TEST] Sending first request...")
        response1 = await client.post(
            'http://localhost:8000/v1/responses',
            json={
                'model': DEFAULT_MODEL,
                'input': 'Say hello in one word',
                'stream': True,
                'store': True,
            },
            headers={'Content-Type': 'application/json'}
        )

        assert response1.status_code == 200, f"First request failed: {response1.status_code}"

        # Read first response events
        print("[TEST] Reading first response events...")
        events1 = await read_sse_events(response1)

        assert len(events1) > 0, "First request received no events"

        # Find response.completed event and extract ID
        completed_events = [e for e in events1 if e.get('type') == 'response.completed']
        assert len(completed_events) == 1, f"Expected 1 completed event, got {len(completed_events)}"

        response_id = completed_events[0]['response']['id']
        print(f"[TEST] First response completed with ID: {response_id}")

        # Second request with previous_response_id
        print(f"\n[TEST] Sending second request with previous_response_id={response_id}...")
        response2 = await client.post(
            'http://localhost:8000/v1/responses',
            json={
                'model': DEFAULT_MODEL,
                'input': 'Now say goodbye in one word',
                'stream': True,
                'store': True,
                'previous_response_id': response_id,
            },
            headers={'Content-Type': 'application/json'}
        )

        assert response2.status_code == 200, f"Second request failed: {response2.status_code}"

        # Read second response events - this is where it hangs
        print("[TEST] Reading second response events (this should hang if bug is present)...")
        events2 = await read_sse_events(response2, timeout_seconds=7)

        assert len(events2) > 0, "Second request received no events (hung!)"

        # Verify we got a completed event
        completed_events2 = [e for e in events2 if e.get('type') == 'response.completed']
        assert len(completed_events2) == 1, f"Expected 1 completed event in second response, got {len(completed_events2)}"

        print("[TEST] ✓ Multi-turn streaming works correctly!")


if __name__ == '__main__':
    print("[TEST] Script starting...")
    asyncio.run(test_multi_turn_streaming())
