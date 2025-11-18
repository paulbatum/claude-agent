# Backend Implementation

## Overview

The backend is a single-file FastAPI application (`backend/main.py`) that implements an OpenAI Responses API-compatible endpoint powered by the Claude Agent SDK.

## File Structure

```
backend/
├── .gitignore          # Python-specific ignores
├── .python-version     # Python 3.12
├── pyproject.toml      # Dependencies (fastapi, claude-agent-sdk, etc.)
├── uv.lock             # Locked dependency versions
└── main.py             # Complete FastAPI application (~586 lines)
```

## Core Components

### 1. FastAPI Application Setup

**Location**: `backend/main.py:26-35`

```python
app = FastAPI(title="Claude Agent API", version="0.1.0")

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Key Points**:
- CORS enabled for local development on ports 5173 (Vite) and 3000
- All methods and headers allowed (should be restricted in production)
- Credentials support enabled for cookie-based auth (if added later)

### 2. Pydantic Models

#### OpenAI Responses API Models

**Location**: `backend/main.py:38-82`

Core request/response models:

```python
class CreateResponseRequest(BaseModel):
    model: str
    input: str
    stream: bool = False
    store: bool = True
    previous_response_id: Optional[str] = None
    temperature: Optional[float] = 1.0
    max_output_tokens: Optional[int] = None

class ResponseObject(BaseModel):
    id: str
    object: Literal["response"] = "response"
    created_at: int
    status: Literal["completed", "failed", "in_progress"] = "completed"
    model: str
    output: List[MessageOutput]
    usage: UsageInfo
    store: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Design Choices**:
- Strict type safety using Pydantic and `Literal` types
- `store` defaults to `True` for automatic conversation persistence
- `stream` defaults to `False` for simpler testing
- `temperature` and `max_output_tokens` accepted but not currently used

#### Streaming Event Models

**Location**: `backend/main.py:84-160`

13 different SSE event types for streaming:

```python
class ResponseCreatedEvent(StreamEventBase):
    type: Literal["response.created"] = "response.created"
    response: ResponseObject

class ResponseOutputTextDeltaEvent(StreamEventBase):
    type: Literal["response.output_text.delta"] = "response.output_text.delta"
    item_id: str
    output_index: int
    content_index: int
    delta: str

# ... 11 more event types
```

**Event Flow**:
1. `response.created` - Response initiated
2. `response.in_progress` - Processing started
3. `response.output_item.added` - Message container added
4. `response.content_part.added` - Text content part added
5. `response.output_text.delta` - Text chunks (multiple)
6. `response.output_text.done` - Text complete
7. `response.content_part.done` - Content part complete
8. `response.output_item.done` - Message complete
9. `response.completed` - Full response complete

### 3. State Management

**Location**: `backend/main.py:163-171`

```python
# Store session IDs for conversation continuity
session_ids: Dict[str, str] = {}

# Store response metadata
conversations: Dict[str, Dict[str, Any]] = {}
```

**Data Structures**:

```python
# session_ids example:
{
  "resp_abc123": "session_xyz789"
}

# conversations example:
{
  "resp_abc123": {
    "request": {
      "model": "claude-haiku-4-5-20251001",
      "input": "Hello!",
      "previous_response_id": None
    },
    "response": {
      "id": "resp_abc123",
      "output": [...],
      "usage": {...}
    }
  }
}
```

**Lifecycle**:
- New response → store `session_id` and full request/response
- Follow-up request → lookup `session_id` to resume conversation
- Server restart → all state lost (in-memory only)

### 4. Claude SDK Client Creation

**Location**: `backend/main.py:177-209`

```python
async def create_client(
    model: str,
    previous_response_id: Optional[str] = None,
    enable_streaming: bool = False
) -> ClaudeSDKClient:
    # Check if we're continuing a conversation
    resume_session_id = None
    if previous_response_id and previous_response_id in session_ids:
        resume_session_id = session_ids[previous_response_id]

    # Create new client for this request
    options = ClaudeAgentOptions(
        model=model,
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        setting_sources=["project"],  # Load CLAUDE.md
        include_partial_messages=enable_streaming,
        resume=resume_session_id,
    )
    client = ClaudeSDKClient(options=options)
    await client.connect()
    return client
```

**Key Configuration**:
- `allowed_tools`: Enables file operations and shell commands
- `permission_mode="acceptEdits"`: Auto-approve file edits (no user prompts)
- `setting_sources=["project"]`: Load `CLAUDE.md` from project root
- `include_partial_messages`: Enable streaming events from Claude API
- `resume`: Continue previous conversation using session ID

**Important**: A **new client is created for each request**, not reused. The SDK handles session state internally.

### 5. Non-Streaming Response Handler

**Location**: `backend/main.py:212-253`

```python
async def call_claude_agent(
    user_input: str,
    model: str,
    previous_response_id: Optional[str] = None
) -> Dict[str, Any]:
    client = await create_client(model, previous_response_id, enable_streaming=False)

    # Send query to Claude
    await client.query(user_input)

    # Collect response
    response_text = ""
    input_tokens = 0
    output_tokens = 0
    session_id = None

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text
        elif isinstance(message, ResultMessage):
            if message.usage:
                input_tokens = message.usage.get("input_tokens", 0)
                output_tokens = message.usage.get("output_tokens", 0)
            session_id = message.session_id

    await client.disconnect()

    return {
        "text": response_text or "No response generated",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "session_id": session_id,
    }
```

**Message Types from SDK**:
- `AssistantMessage`: Contains text response in `TextBlock` content
- `ResultMessage`: Contains usage stats and session ID
- `SystemMessage`: Not used in this implementation

**Flow**:
1. Create client (optionally resume session)
2. Send query
3. Iterate over `receive_response()` async generator
4. Accumulate text from `AssistantMessage` blocks
5. Extract usage from `ResultMessage`
6. Disconnect and return

### 6. Streaming Response Handler

**Location**: `backend/main.py:256-472`

This is the most complex function - it transforms Claude SDK streaming events into OpenAI SSE format.

#### Key Sections

**a) Client Setup and Initial Events** (`256-314`)

```python
async def stream_claude_agent(...) -> AsyncIterator[str]:
    client = await create_client(model, previous_response_id, enable_streaming=True)
    await client.query(user_input)

    # Initialize tracking
    sequence_number = 0
    response_text = ""

    # Helper function to format SSE
    def format_sse(event_type: str, data: dict) -> str:
        json_data = json.dumps(data, separators=(',', ':'))
        return f"event: {event_type}\ndata: {json_data}\n\n"

    # Send initial events
    yield format_sse("response.created", {...})
    yield format_sse("response.in_progress", {...})
```

**b) Process Streaming Events** (`345-394`)

```python
async for message in client.receive_response():
    # Detect StreamEvent (duck typing)
    is_stream_event = (
        not isinstance(message, (AssistantMessage, ResultMessage, SystemMessage))
        and hasattr(message, 'event')
        and isinstance(getattr(message, 'event', None), dict)
    )

    if is_stream_event:
        event = message.event
        event_type = event.get("type")

        if event_type == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                delta_text = delta.get("text", "")
                if delta_text:
                    response_text += delta_text
                    yield format_sse("response.output_text.delta", {
                        "delta": delta_text,
                        ...
                    })
```

**Event Detection**: The SDK doesn't export a `StreamEvent` type, so we detect it by:
1. Not matching known message types
2. Having an `event` attribute
3. `event` being a dictionary

**Claude API Events**:
- `content_block_delta` with `text_delta` → mapped to `response.output_text.delta`
- Other event types are ignored

**c) Final Events** (`396-455`)

```python
# After iteration completes
yield format_sse("response.output_text.done", {"text": response_text, ...})
yield format_sse("response.content_part.done", {...})
yield format_sse("response.output_item.done", {...})
yield format_sse("response.completed", {...})

# Store conversation
if store:
    if session_id:
        session_ids[response_id] = session_id
    conversations[response_id] = {...}

await client.disconnect()
```

**Storage**: Only happens after streaming completes, not during.

### 7. API Endpoints

#### POST /v1/responses

**Location**: `backend/main.py:479-561`

```python
@app.post("/v1/responses")
async def create_response(request: CreateResponseRequest):
    # Generate unique IDs
    response_id = f"resp_{uuid.uuid4().hex}"
    message_id = f"msg_{uuid.uuid4().hex}"

    # Validate previous_response_id
    if request.previous_response_id:
        if request.previous_response_id not in conversations:
            raise HTTPException(status_code=404, detail="Previous response not found")

    # Handle streaming vs non-streaming
    if request.stream:
        return StreamingResponse(
            stream_claude_agent(...),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    else:
        result = await call_claude_agent(...)
        response = ResponseObject(...)

        # Store conversation
        if request.store:
            if result["session_id"]:
                session_ids[response_id] = result["session_id"]
            conversations[response_id] = {...}

        return response
```

**Headers for Streaming**:
- `text/event-stream`: SSE content type
- `Cache-Control: no-cache`: Prevent caching
- `Connection: keep-alive`: Keep connection open
- `X-Accel-Buffering: no`: Disable nginx buffering (important!)

#### GET /v1/responses/{response_id}

**Location**: `backend/main.py:564-573`

```python
@app.get("/v1/responses/{response_id}")
async def get_response(response_id: str) -> ResponseObject:
    if response_id not in conversations:
        raise HTTPException(status_code=404, detail="Response not found")

    stored = conversations[response_id]["response"]
    return ResponseObject(**stored)
```

Simple lookup from in-memory storage.

#### GET /health

**Location**: `backend/main.py:576-579`

```python
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "claude-agent-api"}
```

Basic health check for monitoring.

## Environment Configuration

**Location**: `backend/main.py:23-24`

```python
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")
```

Loads `.env` from project root. Required variables:
- `ANTHROPIC_API_KEY`: Claude API key (required by SDK)

Optional variables (read in `__main__`):
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## Running the Server

**Location**: `backend/main.py:582-585`

```python
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

Run with:
```bash
cd backend
python main.py
# or
uvicorn main:app --reload
```

## Error Handling

### Current Implementation

- `HTTPException(404)` for missing `previous_response_id`
- `HTTPException(500)` for Claude SDK errors (non-streaming only)
- Streaming errors: Connection closed, no explicit error event

### Missing Error Handling

- No timeout handling for long-running requests
- No retry logic for transient Claude API failures
- No validation of `model` parameter
- No handling of tool execution failures (delegated to SDK)

## Performance Considerations

### Async/Await

- All SDK operations are async (`await client.connect()`, `async for message`)
- FastAPI handles concurrent requests efficiently
- No blocking I/O operations

### Connection Management

- Each request creates a new client
- Clients are properly disconnected after use
- No connection pooling (SDK handles this internally)

### Memory Usage

- Full conversation history stored in memory
- Could grow unbounded without cleanup
- Consider LRU cache or TTL-based eviction

## Testing

Test files in `backend/`:
- `test_request.json`: Sample single-turn request
- `test_followup.json`: Sample multi-turn request

Root-level test:
- `test_multi_turn.py`: Integration test for streaming multi-turn conversations

Run integration test:
```bash
python test_multi_turn.py
```

## Dependencies

**From `backend/pyproject.toml`**:

```toml
dependencies = [
    "claude-agent-sdk>=0.1.6",
    "fastapi>=0.115.12",
    "python-dotenv>=1.0.0",
    "uvicorn>=0.34.0",
]
```

Key versions:
- `claude-agent-sdk>=0.1.6`: Includes streaming fixes
- `fastapi>=0.115.12`: Latest stable FastAPI
- `uvicorn>=0.34.0`: ASGI server with WebSocket support

## Common Issues and Solutions

### 1. Streaming Hangs on Follow-up Requests

**Symptom**: First streaming request works, second hangs indefinitely

**Cause**: Bug in SDK versions <0.1.6 where `receive_response()` doesn't stop

**Solution**: Ensure `claude-agent-sdk>=0.1.6` is installed

### 2. CORS Errors in Frontend

**Symptom**: Browser blocks requests with CORS policy error

**Solution**: Ensure frontend origin is in `allow_origins` list (line 31)

### 3. "Previous response not found" Error

**Symptom**: Multi-turn requests fail with 404

**Cause**: Server restarted (in-memory state lost) or invalid `response_id`

**Solution**:
- Don't restart server during conversations
- Implement persistent storage for production

### 4. No Response Text

**Symptom**: `usage` shows tokens but `output` text is empty

**Cause**: Tool execution without final text response

**Solution**: This is expected behavior - agent used tools but didn't provide text explanation

## Future Improvements

1. **Persistent Storage**: PostgreSQL for conversations and sessions
2. **Error Events**: Send `response.failed` events in streaming mode
3. **Timeout Handling**: Add configurable timeouts for SDK operations
4. **Request Validation**: Validate model names, token limits
5. **Rate Limiting**: Prevent abuse with per-IP or per-user limits
6. **Metrics**: Prometheus metrics for request/response tracking
7. **Logging**: Structured logging with request IDs
8. **Authentication**: API key or OAuth-based auth
9. **Conversation Pruning**: Automatic cleanup of old conversations
10. **Model Configuration**: Support `temperature` and `max_output_tokens` parameters
