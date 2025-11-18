# How to Query This Agent About Itself

## Overview

This agent has been designed with **self-awareness** - it can accurately explain its own architecture, implementation, and behavior. This document explains how to ask it questions about itself effectively.

## Quick Start

Simply clone this repository, start the agent, and ask it questions like:

- "How does streaming work in this application?"
- "Explain the multi-turn conversation implementation"
- "Show me the code that handles SSE events"
- "What tools are configured in the Claude SDK?"
- "How is the OpenAI API compatibility layer implemented?"

The agent will:
1. ✅ Search its documentation in `/docs`
2. ✅ Read relevant source code files
3. ✅ Provide accurate, up-to-date answers with code snippets
4. ✅ Reference specific file locations (e.g., `backend/main.py:123`)

## Documentation Structure

The agent has access to comprehensive documentation in the `/docs` folder:

```
docs/
├── architecture.md              # High-level system design
├── backend-implementation.md    # Detailed backend explanation
├── frontend-implementation.md   # Frontend code walkthrough
├── claude-sdk-integration.md    # Claude SDK usage details
├── api-compatibility.md         # OpenAI API format details
├── deployment.md                # How to run and deploy
└── querying-this-agent.md       # This file!
```

## How It Works

### The Agent's Self-Awareness System

**1. Documentation is Always Up-to-Date**

- All docs in `/docs` are **maintained alongside code changes**
- `CLAUDE.md` contains instructions to keep docs current
- Developers must update docs when changing implementation

**2. Agent Has Tool Access**

The agent can use these tools to answer your questions:

- **Read**: Read any source file or documentation
- **Grep**: Search for specific code patterns or text
- **Glob**: Find files by pattern (e.g., `*.py`, `*.tsx`)
- **Bash**: Run commands to explore the codebase

**3. Smart Query Routing**

When you ask about the agent:

```
User: "How does streaming work?"

Agent internally:
1. Recognizes this is about itself
2. Searches docs/backend-implementation.md for "streaming"
3. Reads backend/main.py to show actual code
4. Provides answer with both explanation and code snippets
```

### System Prompt Enhancement

**Location**: `CLAUDE.md` (loaded via `setting_sources=["project"]`)

The agent's system prompt includes:

- Awareness of the `/docs` folder
- Instructions to use docs for self-explanation
- Guidance on when to read code vs. documentation
- Requirement to provide code references with line numbers

## Example Queries

### Architecture Questions

**Good**:
- "What's the overall architecture of this application?"
- "How do the frontend and backend communicate?"
- "Why did you choose the OpenAI Responses API format?"
- "What's the data flow for a multi-turn conversation?"

**What You'll Get**:
- High-level architecture diagram (from `architecture.md`)
- Explanation of design decisions
- Links to relevant implementation details

### Implementation Questions

**Good**:
- "Show me the code that handles SSE streaming"
- "How is the `create_client` function implemented?"
- "What Pydantic models are used for the API?"
- "Explain the event parsing loop in the frontend"

**What You'll Get**:
- Actual code snippets from source files
- File and line number references (e.g., `backend/main.py:256-472`)
- Explanation of how the code works
- Context about why it's implemented that way

### Debugging Questions

**Good**:
- "Why might streaming hang on the second request?"
- "What could cause a 'Previous response not found' error?"
- "How do I enable debug logging?"
- "What happens if the Claude API key is invalid?"

**What You'll Get**:
- Known issues and solutions (from implementation docs)
- Debugging steps
- Relevant code sections to check
- Configuration changes to try

### Configuration Questions

**Good**:
- "What environment variables are required?"
- "How do I change the Claude model?"
- "What tools are enabled in the Claude SDK?"
- "How do I configure CORS for production?"

**What You'll Get**:
- Current configuration (read from code)
- How to change settings
- Security considerations
- Examples of valid values

### Deployment Questions

**Good**:
- "How do I deploy this to production?"
- "What's the Docker setup?"
- "How do I add database persistence?"
- "What's needed for HTTPS?"

**What You'll Get**:
- Step-by-step deployment instructions (from `deployment.md`)
- Example configurations
- Best practices
- Platform-specific guidance (Fly.io, Railway, etc.)

## Best Practices for Queries

### 1. Be Specific

**Less Effective**:
- "How does this work?"
- "Tell me about the code"

**More Effective**:
- "How does the backend transform Claude SDK responses to OpenAI format?"
- "Explain the SSE event parsing logic in App.tsx"

### 2. Ask for Code Examples

**Effective**:
- "Show me the code for handling text deltas"
- "What does the `stream_claude_agent` function do?"
- "Give me an example of a streaming request"

**Why**: The agent will read source files and show actual implementation.

### 3. Request File References

**Effective**:
- "Where is the CORS configuration?"
- "Which file handles session management?"
- "Show me the Pydantic models with line numbers"

**Why**: You get exact locations to look at in your editor.

### 4. Ask About Design Decisions

**Effective**:
- "Why create a new ClaudeSDKClient for each request?"
- "Why use the Responses API instead of Chat Completions?"
- "Why is state stored in memory instead of a database?"

**Why**: Documentation includes reasoning behind implementation choices.

### 5. Explore Dependencies

**Effective**:
- "What version of the Claude SDK is required and why?"
- "What are the frontend dependencies?"
- "Why is uv used instead of pip?"

**Why**: Documentation explains version requirements and tool choices.

## Advanced Usage

### Multi-Step Investigations

You can have conversations that build on previous questions:

```
User: "How does multi-turn conversation work?"
Agent: [Explains session_ids mapping and resume parameter]

User: "Show me the code where session_id is stored"
Agent: [Shows backend/main.py:551-554 with context]

User: "What happens if the server restarts?"
Agent: [Explains in-memory storage limitation]

User: "How would I add database persistence?"
Agent: [Provides implementation guide from deployment.md]
```

### Code Walkthroughs

Ask the agent to walk through code execution:

```
User: "Walk me through what happens when a user sends a streaming request"

Agent:
1. Frontend sends POST to /v1/responses with stream=true (App.tsx:33-44)
2. Backend creates response_id and message_id (main.py:488-489)
3. Backend calls stream_claude_agent() (main.py:500-507)
4. stream_claude_agent creates ClaudeSDKClient (main.py:269)
5. Client sends query to Claude (main.py:272)
6. Backend yields SSE events as they arrive (main.py:345-377)
7. Frontend parses SSE and updates UI (App.tsx:86-120)
8. Backend stores session_id on completion (main.py:458-460)
```

### Comparative Questions

Ask about differences or alternatives:

```
User: "What's the difference between streaming and non-streaming mode?"

Agent: [Compares code paths, explains trade-offs]

User: "Could we use WebSockets instead of SSE?"

Agent: [Discusses pros/cons, implementation changes needed]
```

## What the Agent Can and Cannot Do

### ✅ Can Do

- Explain any part of its own codebase
- Show exact code with line numbers
- Explain design decisions and trade-offs
- Provide deployment instructions
- Debug common issues
- Suggest improvements
- Walk through execution flows
- Compare implementation alternatives

### ❌ Cannot Do (Without Running Code)

- Show current runtime state (unless code is executed)
- Display actual API responses (can show examples from docs)
- Access external APIs
- Modify its own source code (unless explicitly requested)

### ⚠️ Limitations

- **Documentation Must Be Maintained**: If code changes but docs don't, answers may be inaccurate
- **Requires Tool Access**: Agent needs `Read`, `Grep`, and `Glob` tools enabled
- **Subject to Context Limits**: Very large codebases may exceed context window

## Ensuring Accurate Answers

### For Developers

When you modify the codebase, **update the relevant documentation**:

1. **Code Changes**: Update implementation docs (backend-implementation.md, frontend-implementation.md)
2. **Architecture Changes**: Update architecture.md
3. **API Changes**: Update api-compatibility.md
4. **Deployment Changes**: Update deployment.md
5. **New Features**: Document in appropriate file

**Checklist in `CLAUDE.md`** provides guidance.

### For Users

If you get an answer that seems wrong:

1. Check if code was recently changed (git log)
2. Check if documentation is out of date
3. Ask the agent to read the specific source file
4. Report inconsistencies so docs can be updated

## Example Conversation

Here's a realistic example of querying the agent:

```
User: I'm new to this project. How does it work?

Agent: This is a Claude-powered AI agent with a React frontend and FastAPI backend.
The architecture follows three layers... [provides overview from architecture.md]

User: How do I run it locally?

Agent: Here are the steps: [provides setup from deployment.md]

User: I'm getting a CORS error. Where's the CORS configuration?

Agent: The CORS configuration is in backend/main.py:28-35:

[shows code snippet]

Currently it allows localhost:5173 and localhost:3000. Make sure your frontend
is running on one of these ports, or add your port to the allow_origins list.

User: How do I add my port?

Agent: Edit backend/main.py line 31 and add your port to the list:

allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:YOUR_PORT"]

Then restart the backend server.

User: Thanks! Now I want to understand the streaming implementation.

Agent: The streaming implementation has two parts:

Backend (backend/main.py:256-472):
- Creates ClaudeSDKClient with include_partial_messages=True
- Iterates over receive_response() to get StreamEvents
- Transforms text deltas to OpenAI SSE format
- Yields SSE events via FastAPI StreamingResponse

Frontend (frontend/src/App.tsx:71-121):
- Reads response body as a stream
- Parses SSE events (split by \n\n)
- Extracts text deltas and updates UI in real-time

Would you like me to walk through either implementation in detail?
```

## Testing Your Questions

After setting up the agent, try these test questions:

**Basic**:
1. "What is this project?"
2. "How do I run it?"
3. "What files make up the backend?"

**Intermediate**:
1. "How does session management work?"
2. "Show me the API endpoint definitions"
3. "What Claude SDK tools are enabled?"

**Advanced**:
1. "Explain the streaming event flow from backend to frontend"
2. "How would I add database persistence?"
3. "Compare the non-streaming vs streaming code paths"

If the agent answers all these accurately with code references, the self-awareness system is working correctly!

## Maintaining Self-Awareness

### As the Project Evolves

To keep the agent's self-knowledge accurate:

**1. Update Docs with Code Changes**

Use this workflow:

```bash
# Make code changes
vim backend/main.py

# Update relevant documentation
vim docs/backend-implementation.md

# Ask the agent to verify
# (in your chat interface)
"Does the documentation for backend/main.py accurately reflect the current code?"
```

**2. Add New Documentation for New Features**

When adding significant features:

```bash
# Create new doc file
vim docs/new-feature.md

# Link from architecture.md
vim docs/architecture.md

# Test agent's knowledge
"Explain how [new feature] works"
```

**3. Use the Agent to Review Docs**

Before committing:

```
User: "Review the documentation for accuracy against the current code"

Agent: [Checks each doc file against source code and reports discrepancies]
```

### Documentation Quality Guidelines

For best results, documentation should:

- **Include code references**: Link to specific files and line numbers
- **Explain "why"**: Not just what the code does, but why it's done that way
- **Provide examples**: Show actual usage with real code snippets
- **Stay current**: Update alongside code changes
- **Be searchable**: Use clear headings and keywords

## Troubleshooting Agent Responses

### Agent Says "I don't know"

**Possible Causes**:
- Documentation doesn't exist for that topic
- Question is too vague
- Agent can't access the relevant files

**Solutions**:
- Be more specific
- Ask agent to search for relevant files
- Check if documentation exists for that topic

### Agent Provides Outdated Information

**Causes**:
- Documentation not updated after code changes
- Agent read cached/old version

**Solutions**:
- Update the relevant documentation
- Ask agent to re-read the source file
- Verify code hasn't changed since docs were written

### Agent Can't Find Code

**Causes**:
- Tool access restricted
- File path incorrect
- File doesn't exist

**Solutions**:
- Verify agent has Read, Grep, Glob tools enabled
- Check file exists: `ls backend/main.py`
- Provide exact file path

## Integration with Development Workflow

### Use the Agent as Documentation

Instead of maintaining separate docs:

1. Keep `/docs` updated
2. Let the agent answer questions
3. Agent becomes your interactive documentation system

### Use the Agent for Onboarding

New developers can:

1. Clone the repo
2. Start the agent
3. Ask questions to learn the codebase
4. Get instant, accurate answers

### Use the Agent for Code Review

Before committing:

```
User: "Review the changes I made to backend/main.py"

Agent: [Reads file, identifies changes, suggests improvements]
```

## Advanced: Teaching the Agent New Knowledge

If you add features not yet documented:

```
User: "I added a new rate limiting feature. Here's the code: [paste code]
Update your knowledge about this."

Agent: [You can then update the relevant doc files with the agent's help]
```

Then commit the documentation changes so future sessions know about it.

## Conclusion

This agent is designed to be **self-documenting** and **self-explaining**. By maintaining the `/docs` folder and keeping it in sync with code changes, you ensure that:

- New developers can learn the codebase by asking questions
- The agent can debug issues by understanding its own code
- Documentation never falls out of date
- Knowledge is accessible through natural conversation

**Next Steps**:

1. Start the agent locally
2. Try the example questions from this guide
3. Ask your own questions about specific code you're curious about
4. If you make changes, update the docs to keep the agent's knowledge current

**Remember**: The agent is only as knowledgeable as its documentation. Keep docs updated, and you'll have an always-accurate, interactive guide to the codebase!
