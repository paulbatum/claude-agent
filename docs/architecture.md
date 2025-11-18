# Architecture Overview

## High-Level Design

This project implements a Claude-powered AI agent with a **three-tier architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  - TypeScript + React 19                                │
│  - Chat UI with streaming support                       │
│  - SSE event handling                                   │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP (OpenAI Responses API format)
                  │ POST /v1/responses
                  ▼
┌─────────────────────────────────────────────────────────┐
│                Backend (FastAPI + Python)                │
│  - OpenAI API compatibility layer                       │
│  - Request/response transformation                      │
│  - Session management                                   │
│  - SSE streaming orchestration                          │
└─────────────────┬───────────────────────────────────────┘
                  │ Python SDK
                  │ ClaudeSDKClient
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Claude Agent SDK                            │
│  - Anthropic Claude API wrapper                         │
│  - Tool execution (Read, Write, Bash)                   │
│  - Conversation state management                        │
│  - Streaming support                                    │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Frontend Layer (`frontend/`)

**Technology**: React 19 + TypeScript + Vite

**Responsibilities**:
- Render chat interface with message history
- Send user input to backend via OpenAI Responses API format
- Handle SSE streaming events for real-time response display
- Manage conversation continuity using `previous_response_id`

**Key Files**:
- `frontend/src/App.tsx` - Main chat component with SSE streaming logic
- `frontend/src/main.tsx` - Application entry point

### 2. Backend Layer (`backend/`)

**Technology**: FastAPI + Python 3.12+ + uvicorn

**Responsibilities**:
- Expose OpenAI-compatible `/v1/responses` endpoint
- Transform OpenAI API requests to Claude SDK format
- Transform Claude SDK responses back to OpenAI format
- Manage conversation sessions and response IDs
- Handle both streaming (SSE) and non-streaming modes
- Store conversation history for multi-turn support

**Key Files**:
- `backend/main.py` - FastAPI application with all endpoints and logic

### 3. Claude Agent SDK Layer

**Technology**: `claude-agent-sdk` Python package (>=0.1.6)

**Responsibilities**:
- Connect to Anthropic's Claude API
- Execute queries with conversation context
- Provide tool execution capabilities (Read, Write, Bash)
- Maintain session state for multi-turn conversations
- Stream partial responses when requested

## Data Flow

### Single-Turn Request (Non-Streaming)

```
1. User types message in frontend
2. Frontend sends POST /v1/responses
   {
     "model": "claude-haiku-4-5-20251001",
     "input": "Hello!",
     "stream": false
   }
3. Backend creates ClaudeSDKClient
4. Backend calls client.query("Hello!")
5. Backend collects full response from client.receive_response()
6. Backend transforms to OpenAI format
7. Backend returns complete response
   {
     "id": "resp_abc123",
     "output": [{"content": [{"text": "Hello! How can I help?"}]}],
     "usage": {"input_tokens": 10, "output_tokens": 20}
   }
8. Frontend displays assistant message
```

### Multi-Turn Request (Streaming)

```
1. User sends first message → gets response_id "resp_abc123"
2. User sends follow-up message with previous_response_id="resp_abc123"
3. Backend looks up session_id from session_ids["resp_abc123"]
4. Backend creates new ClaudeSDKClient with resume=session_id
5. ClaudeSDKClient loads previous conversation context
6. Backend streams response events via SSE:
   - response.created
   - response.in_progress
   - response.output_item.added
   - response.content_part.added
   - response.output_text.delta (multiple times)
   - response.output_text.done
   - response.content_part.done
   - response.output_item.done
   - response.completed
7. Frontend updates UI in real-time as deltas arrive
8. Backend stores new session_id for next turn
```

## Design Principles

### 1. **API Compatibility First**

The backend strictly adheres to OpenAI's Responses API specification to enable easy integration with existing tools and frontend libraries.

### 2. **Stateless Backend, Stateful SDK**

The FastAPI backend itself is stateless - it doesn't maintain persistent connections. Instead:
- Each request creates a **new** `ClaudeSDKClient` instance
- Session continuity is achieved via `resume=session_id` parameter
- The Claude SDK maintains conversation state internally via session IDs
- Backend stores `session_id` mappings in memory (`session_ids` dict)

### 3. **Streaming for Responsiveness**

Streaming mode provides immediate feedback:
- Frontend sees response text appear in real-time
- Backend proxies streaming events from Claude SDK to OpenAI SSE format
- Each text delta is sent as a separate `response.output_text.delta` event

### 4. **Tool Execution Transparency**

The Claude Agent SDK can execute tools (`Read`, `Write`, `Bash`) during responses:
- Backend enables tools via `allowed_tools=["Read", "Write", "Bash"]`
- Tool execution happens transparently within Claude SDK
- Final response includes any results from tool usage
- Frontend only sees the final text output

### 5. **Project-Aware Configuration**

The SDK loads `CLAUDE.md` via `setting_sources=["project"]`:
- Provides project context to the agent
- Agent understands codebase structure and conventions
- Enables accurate, context-aware responses

## Storage and State

### In-Memory Storage

Two dictionaries maintain conversation state:

```python
# Maps response_id → session_id
session_ids: Dict[str, str] = {}

# Maps response_id → {request, response}
conversations: Dict[str, Dict[str, Any]] = {}
```

**Implications**:
- State is lost on server restart
- Not suitable for production without persistent storage
- Consider Redis/database for production deployments

### Session Management

- Each conversation turn gets a unique `response_id` (e.g., `resp_abc123`)
- Backend stores the Claude SDK `session_id` associated with each response
- Follow-up requests use `previous_response_id` to look up the session
- Claude SDK resumes session with full conversation history

## Error Handling

### Request Validation

- `previous_response_id` is validated against stored conversations
- Returns 404 if referenced response doesn't exist
- Model name is passed through without validation (Claude SDK handles this)

### Streaming Error Handling

- Client-side disconnects are handled gracefully by FastAPI
- Backend ensures `client.disconnect()` is called in all code paths
- Timeouts can occur if Claude SDK hangs (rare, but possible)

### Tool Execution Errors

- Tool execution errors are captured by Claude SDK
- Error messages are included in the response text
- Backend doesn't need to handle tool errors explicitly

## Scalability Considerations

### Current Limitations

- **In-memory state**: Lost on restart, not shared across instances
- **No rate limiting**: Could be overwhelmed by concurrent requests
- **No authentication**: Anyone can access the API
- **No conversation limits**: Could accumulate unbounded state

### Future Improvements

1. **Persistent Storage**: Use PostgreSQL/Redis for conversations and sessions
2. **Horizontal Scaling**: Session affinity or distributed session storage
3. **Authentication**: Add API keys or OAuth
4. **Rate Limiting**: Per-user or per-IP rate limits
5. **Conversation Pruning**: Limit conversation history length/age
6. **Metrics and Monitoring**: Track usage, errors, response times

## Technology Choices

### Why FastAPI?

- Native async/await support for concurrent requests
- Built-in SSE support via `StreamingResponse`
- Excellent type safety with Pydantic models
- Auto-generated API documentation (OpenAPI)

### Why React 19?

- Latest stable version with improved concurrent rendering
- TypeScript for type safety
- Vite for fast development and builds

### Why OpenAI Responses API Format?

- Industry-standard format for AI applications
- Compatible with existing tools and libraries
- Well-documented and widely understood
- Supports both streaming and non-streaming modes

### Why Claude Agent SDK?

- Official SDK from Anthropic
- Built-in tool execution support
- Automatic conversation state management
- Streaming support out of the box
- Project-aware configuration via `CLAUDE.md`

## Security Considerations

### Current Security Posture

- **API Key Security**: `ANTHROPIC_API_KEY` must be kept secret
- **CORS**: Currently allows `localhost:5173` and `localhost:3000`
- **No Input Validation**: User input is passed directly to Claude SDK
- **No Output Sanitization**: Agent output is displayed as-is

### Recommendations

1. **Environment Variables**: Never commit `.env` to version control
2. **Input Sanitization**: Validate/sanitize user input before processing
3. **Output Filtering**: Consider filtering sensitive data from responses
4. **CORS Configuration**: Restrict origins in production
5. **HTTPS**: Use TLS in production environments
6. **Tool Restrictions**: Limit `allowed_tools` based on use case
