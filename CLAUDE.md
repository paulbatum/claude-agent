# Claude Agent Project

## Overview

This project implements an AI agent powered by the Claude Agent SDK, exposed via an OpenAI-compatible HTTP API. The frontend is a React/TypeScript application that communicates with the backend using the OpenAI `/v1/responses` API format (the newer Responses API, not Chat Completions).

## Project Structure

```
/
├── .env                      # Environment variables (ANTHROPIC_API_KEY)
├── CLAUDE.md                 # This file - project documentation
├── README.md                 # Project readme
├── .gitignore                # Root gitignore (OS/IDE files)
├── reference/                # Reference documentation
│   ├── claude-agent-sdk.md   # Claude Agent SDK API reference
│   └── openapi.documented.yml # OpenAI API specification
├── frontend/                 # React + TypeScript frontend
│   ├── .gitignore            # Frontend-specific gitignore
│   ├── package.json          # Node dependencies (React 19, Vite)
│   ├── src/
│   │   ├── App.tsx           # Main React component
│   │   ├── main.tsx          # Entry point
│   │   └── ...
│   └── ...
└── backend/                  # Python FastAPI backend
    ├── .gitignore            # Python-specific gitignore
    ├── .venv/                # Python virtual environment
    ├── pyproject.toml        # Python dependencies (claude-agent-sdk, fastapi)
    └── ...                   # Source files (to be created)
```

## Technology Stack

### Frontend
- **Framework**: React 19
- **Language**: TypeScript
- **Build Tool**: Vite
- **Package Manager**: pnpm
- **API Communication**: OpenAI-compatible API format

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.12+
- **Package Manager**: uv
- **AI SDK**: Claude Agent SDK (>=0.1.6)
- **API Format**: OpenAI `/v1/chat/completions` compatible

## Configuration

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY`: Your Anthropic API key (required by Claude SDK)

**Optional:**
- `MODEL_NAME`: Claude model ID (default: `claude-haiku-4-5-20251001` during testing)
- `PORT`: Backend server port (default: 8000)
- `HOST`: Backend server host (default: 0.0.0.0)

### Model Configuration

The Claude Agent SDK accepts model names via the `model` parameter in `ClaudeAgentOptions`:

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    model="claude-haiku-4-5-20251001",  # Fast, cost-effective for testing
    # model="claude-sonnet-4-5-20250929",  # Production: more capable
    # model="claude-opus-4-5-20250514",    # Production: most capable
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode="acceptEdits"
)
```

**Available Models:**
- `claude-haiku-4-5-20251001` - Fastest, most cost-effective (recommended for testing)
- `claude-sonnet-4-5-20250929` - Balanced performance and capability
- `claude-opus-4-5-20250514` - Most capable

## API Design

### OpenAI Responses API Compatibility

The backend exposes an OpenAI-compatible Responses API endpoint:

**Endpoint:** `POST /v1/responses`

**Request Format:**
```json
{
  "model": "claude-haiku-4-5-20251001",
  "input": "Hello! How can you help me?",
  "stream": false,
  "store": true
}
```

**Response Format:**
```json
{
  "id": "resp_abc123",
  "object": "response",
  "created_at": 1741476542,
  "status": "completed",
  "model": "claude-haiku-4-5-20251001",
  "output": [
    {
      "type": "message",
      "id": "msg_abc123",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "Hello! I can help you with various tasks...",
          "annotations": []
        }
      ]
    }
  ],
  "usage": {
    "input_tokens": 36,
    "output_tokens": 87,
    "total_tokens": 123
  }
}
```

**Multi-turn Conversations:**
```json
{
  "model": "claude-haiku-4-5-20251001",
  "input": "What did we talk about?",
  "previous_response_id": "resp_abc123"
}
```

**With Conversation Persistence:**
```json
{
  "model": "claude-haiku-4-5-20251001",
  "input": "Hello!",
  "conversation_id": "conv_abc123"
}
```

### OpenAI Conversations API

The backend fully implements the OpenAI Conversations API for persistent conversation storage:

**Endpoints:**
- `POST /v1/conversations` - Create a new conversation
- `GET /v1/conversations/{conversation_id}` - Retrieve a conversation
- `PATCH /v1/conversations/{conversation_id}` - Update conversation metadata
- `DELETE /v1/conversations/{conversation_id}` - Delete a conversation
- `POST /v1/conversations/{conversation_id}/items` - Add items to conversation
- `GET /v1/conversations/{conversation_id}/items` - List conversation items
- `GET /v1/conversations/{conversation_id}/items/{item_id}` - Get specific item
- `DELETE /v1/conversations/{conversation_id}/items/{item_id}` - Delete an item

**Create Conversation Example:**
```json
{
  "metadata": {"topic": "project-x", "user": "alice"},
  "items": []
}
```

**Response:**
```json
{
  "id": "conv_abc123",
  "object": "conversation",
  "metadata": {"topic": "project-x", "user": "alice"},
  "created_at": 1741476542
}
```

### Conversation Storage

Conversations are persisted using a pluggable storage abstraction layer:

**Current Implementation:** File-based storage
- Location: `.conversations/` directory (gitignored)
- Format: JSON files, one per conversation
- Structure: `{conversation_id}.json`

**Abstraction Layer:** `storage/base.py`
- Abstract base class `ConversationStorage`
- Easy to add new implementations (database, cloud storage, etc.)

**File Storage:** `storage/file_storage.py`
- `FileConversationStorage` - stores conversations as JSON files
- Thread-safe async file I/O
- Automatic timestamping

### Implementation Strategy

1. **Backend receives OpenAI Responses API request** at `/v1/responses`
2. **Convert to Claude Agent SDK format** - Transform input to Claude SDK query
3. **Execute via Claude Agent SDK** - Use `ClaudeSDKClient` for stateful conversations
4. **Convert response back to Responses API format** - Map Claude messages to output items
5. **Return to frontend** - Send OpenAI-compatible JSON response

## Development Workflow

### Backend Setup

```bash
cd backend
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
uv pip install -e .         # Install in editable mode
```

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev                    # Start dev server (usually http://localhost:5173)
```

### Running Both

**Terminal 1 (Backend):**
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
pnpm dev
```

## Current Status

- [x] Project structure created with separate frontend/backend
- [x] .gitignore files configured for each context
- [x] Dependencies defined (claude-agent-sdk, React 19)
- [x] Reference documentation added
- [x] Backend API implementation
  - [x] OpenAI Responses API (`/v1/responses`)
  - [x] OpenAI Conversations API (`/v1/conversations`)
  - [x] Conversation persistence with file-based storage
  - [x] Abstraction layer for future storage implementations
- [ ] Frontend chat UI
- [ ] Basic conversation flow working end-to-end

## Next Steps

1. ~~Create FastAPI backend with `/v1/responses` endpoint~~ ✅
2. ~~Implement Claude Agent SDK integration~~ ✅
3. ~~Add request/response transformation logic~~ ✅
4. ~~Add conversation persistence~~ ✅
5. Build simple chat UI in frontend
6. Connect frontend to backend API
7. Test basic conversation flow end-to-end
8. Add streaming support
9. Add error handling improvements
10. Consider additional storage backends (PostgreSQL, Redis, etc.)

## Notes

- Using Haiku model during development for speed and cost efficiency
- The Claude Agent SDK doesn't use environment variables for model selection - pass it programmatically in `ClaudeAgentOptions`
- Frontend should use OpenAI client libraries or direct fetch calls to `/v1/chat/completions`
- Consider adding CORS middleware for local development
