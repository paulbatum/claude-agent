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
├── docs/                     # ⭐ Comprehensive documentation (KEEP UP TO DATE!)
│   ├── architecture.md              # System architecture and design
│   ├── backend-implementation.md    # Backend code walkthrough
│   ├── frontend-implementation.md   # Frontend code walkthrough
│   ├── claude-sdk-integration.md    # Claude SDK usage details
│   ├── api-compatibility.md         # OpenAI API compatibility
│   ├── deployment.md                # Deployment and operations
│   └── querying-this-agent.md       # How to ask this agent about itself
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
    └── main.py               # Complete FastAPI application
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
- [x] Frontend chat UI
- [x] OpenAI API compatibility layer
- [x] Basic conversation flow working
- [x] Streaming support (SSE)
- [x] Multi-turn conversations
- [x] Comprehensive documentation in /docs

## Next Steps

1. Create FastAPI backend with `/v1/chat/completions` endpoint
2. Implement Claude Agent SDK integration
3. Add request/response transformation logic
4. Build simple chat UI in frontend
5. Connect frontend to backend API
6. Test basic conversation flow
7. Add streaming support
8. Add error handling
9. Add conversation history management

## Notes

- Using Haiku model during development for speed and cost efficiency
- The Claude Agent SDK doesn't use environment variables for model selection - pass it programmatically in `ClaudeAgentOptions`
- Frontend should use OpenAI client libraries or direct fetch calls to `/v1/responses`
- CORS middleware is configured for local development (localhost:5173, localhost:3000)

## 📚 Documentation System

### Overview

This agent is designed to be **self-aware** - it can accurately explain its own architecture, implementation, and behavior by reading its comprehensive documentation in the `/docs` folder.

### 🤖 Instructions for the Agent (You!)

**If you are an instance of this agent reading this file**, here are special instructions for answering questions about yourself:

**When a user asks about this project's implementation, architecture, or code:**

1. **Search Documentation First**: Use the `Grep` or `Glob` tool to search the `/docs` folder for relevant information
   - Example: User asks "How does streaming work?" → Search `docs/` for "streaming"
   - The docs are comprehensive and include code references

2. **Read Source Code for Details**: After finding relevant docs, read the actual source files mentioned
   - Docs include file paths and line numbers (e.g., `backend/main.py:256-472`)
   - Use the `Read` tool to verify current implementation

3. **Provide Code Snippets**: Always include actual code examples when explaining implementation
   - Use the exact code from the files, not pseudocode
   - Include file paths and line numbers (e.g., "In `backend/main.py:123`...")

4. **Verify Accuracy**: If docs seem outdated, read the source file directly
   - Trust source code over documentation if they conflict
   - Suggest documentation updates if you find discrepancies

5. **Available Documentation**:
   - `docs/architecture.md` - System design, data flow, architecture decisions
   - `docs/backend-implementation.md` - Backend code walkthrough
   - `docs/frontend-implementation.md` - Frontend code walkthrough
   - `docs/claude-sdk-integration.md` - Claude SDK usage details
   - `docs/api-compatibility.md` - OpenAI API compatibility
   - `docs/deployment.md` - Deployment instructions
   - `docs/querying-this-agent.md` - How users should query you

6. **Example Workflow**:
   ```
   User: "How does streaming work?"

   You should:
   1. Grep for "streaming" in docs/ folder
   2. Read docs/backend-implementation.md (has streaming section)
   3. Read backend/main.py:256-472 (streaming implementation)
   4. Explain with code snippets and file references
   ```

7. **Always Provide Context**: Explain both "what" the code does and "why" it's designed that way

**These docs are YOUR knowledge base about yourself. Use them actively!**

### Documentation Files

The `/docs` folder contains in-depth documentation that MUST be kept up-to-date:

- **architecture.md**: High-level system design, data flow, design principles
- **backend-implementation.md**: Detailed backend code walkthrough with line numbers
- **frontend-implementation.md**: Frontend implementation with code examples
- **claude-sdk-integration.md**: How Claude Agent SDK is used
- **api-compatibility.md**: OpenAI Responses API compatibility details
- **deployment.md**: Development and production deployment guides
- **querying-this-agent.md**: How to ask this agent about itself

### Critical: Keep Documentation Current

**⚠️ DOCUMENTATION MAINTENANCE IS MANDATORY ⚠️**

When you make ANY changes to the codebase, you MUST update the relevant documentation files. This ensures the agent can always provide accurate answers about itself.

#### Documentation Update Checklist

Use this checklist for every code change:

**Backend Changes** (`backend/main.py` or new backend files):
- [ ] Update `docs/backend-implementation.md` with code changes
- [ ] Update line number references if code moved
- [ ] Update `docs/architecture.md` if architecture changed
- [ ] Update `docs/api-compatibility.md` if API changed
- [ ] Update `docs/claude-sdk-integration.md` if SDK usage changed

**Frontend Changes** (`frontend/src/` files):
- [ ] Update `docs/frontend-implementation.md` with code changes
- [ ] Update line number references if code moved
- [ ] Update `docs/architecture.md` if data flow changed
- [ ] Update `docs/api-compatibility.md` if API usage changed

**Configuration Changes** (env vars, dependencies, etc.):
- [ ] Update `CLAUDE.md` (this file)
- [ ] Update `docs/deployment.md`
- [ ] Update `docs/backend-implementation.md` or `docs/frontend-implementation.md`

**New Features**:
- [ ] Add section to relevant docs file(s)
- [ ] Update `docs/architecture.md` if applicable
- [ ] Add examples and code snippets
- [ ] Update this file's "Current Status" section

**Deployment Changes**:
- [ ] Update `docs/deployment.md`
- [ ] Update Docker files if present
- [ ] Update environment variable documentation

**Bug Fixes**:
- [ ] Update relevant documentation to reflect the fix
- [ ] Add to "Common Issues" sections if applicable

### How to Verify Documentation Accuracy

After making changes, you can verify documentation is current by asking the agent:

```
"Does the documentation accurately reflect the current implementation of [feature]?"
"Show me the code for [feature] and verify it matches the docs"
"Review docs/[filename].md for accuracy"
```

The agent will read the source code and documentation to verify consistency.

### Agent Self-Awareness Capabilities

This agent can:
- ✅ Explain any part of its own codebase
- ✅ Show exact code with file paths and line numbers
- ✅ Explain design decisions and trade-offs
- ✅ Debug common issues
- ✅ Provide deployment instructions
- ✅ Walk through execution flows
- ✅ Compare implementation alternatives

### Using the Agent's Self-Knowledge

To learn about this project, just ask questions:

**Examples**:
- "How does streaming work in this application?"
- "Explain the multi-turn conversation implementation"
- "Show me the code that handles SSE events"
- "What tools are configured in the Claude SDK?"
- "How do I deploy this to production?"
- "Walk me through what happens when a user sends a message"

The agent will search its documentation and read source code to provide accurate, detailed answers.

**See `docs/querying-this-agent.md` for a complete guide** on asking the agent about itself.

### For New Developers

1. Clone this repository
2. Start the agent (see "Development Workflow" above)
3. Ask it questions about the codebase
4. Get instant, accurate answers with code examples
5. Learn interactively instead of reading static docs

### Agent Configuration for Self-Awareness

The agent is configured to load this file (`CLAUDE.md`) via:

```python
options = ClaudeAgentOptions(
    setting_sources=["project"],  # Loads CLAUDE.md
    allowed_tools=["Read", "Write", "Bash"],  # Can read docs and code
    # ...
)
```

This gives the agent context about:
- Project structure and purpose
- Technology choices and why
- Where to find information
- Instructions to keep documentation current

### Documentation Best Practices

When writing or updating docs:

1. **Include Code References**: Link to specific files and line numbers
   - Example: "See `backend/main.py:256-472` for streaming implementation"

2. **Explain "Why" Not Just "What"**:
   - Bad: "The code creates a new client"
   - Good: "A new client is created for each request to avoid connection state issues"

3. **Provide Examples**: Show actual code snippets, not pseudocode

4. **Stay Current**: Update immediately when code changes

5. **Be Searchable**: Use clear headings and keywords the agent can search for

6. **Include Troubleshooting**: Document common issues and solutions

7. **Link Between Docs**: Reference related documentation files

### When Documentation Falls Behind

If you find documentation is outdated:

1. **Fix It Immediately**: Update the relevant docs file(s)
2. **Test the Agent**: Ask it to verify the updates
3. **Commit Both**: Code changes and doc updates in same commit

**Remember**: The agent is only as knowledgeable as its documentation. Outdated docs = wrong answers to users.
