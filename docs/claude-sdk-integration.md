# Claude Agent SDK Integration

## Overview

This document explains how the backend integrates with the official Claude Agent SDK from Anthropic.

## SDK Version

**Required**: `claude-agent-sdk>=0.1.6`

**Why 0.1.6+**: Earlier versions had a bug where `receive_response()` wouldn't stop iterating on multi-turn streaming conversations, causing hangs.

## Installation

```bash
cd backend
uv pip install claude-agent-sdk>=0.1.6
```

Or add to `pyproject.toml`:

```toml
dependencies = [
    "claude-agent-sdk>=0.1.6",
]
```

## Core SDK Components

### Imports

**Location**: `backend/main.py:14-21`

```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
    SystemMessage,
)
```

**Components**:
- `ClaudeSDKClient`: Main client class for interacting with Claude
- `ClaudeAgentOptions`: Configuration options for the client
- `AssistantMessage`: Response message from Claude with text content
- `TextBlock`: Text content block within a message
- `ResultMessage`: Final message with usage stats and session ID
- `SystemMessage`: System messages (not currently used)

### Configuration: ClaudeAgentOptions

**Location**: `backend/main.py:199-206`

```python
options = ClaudeAgentOptions(
    model=model,
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode="acceptEdits",
    setting_sources=["project"],
    include_partial_messages=enable_streaming,
    resume=resume_session_id,
)
```

#### model

**Type**: `str`

**Examples**:
- `"claude-haiku-4-5-20251001"` - Fast, cost-effective
- `"claude-sonnet-4-5-20250929"` - Balanced
- `"claude-opus-4-5-20250514"` - Most capable

**Note**: Model names must match Anthropic's API exactly. Invalid names will cause errors at runtime.

#### allowed_tools

**Type**: `List[str]`

**Available Tools**:
- `"Read"` - Read files from the filesystem
- `"Write"` - Create or overwrite files
- `"Edit"` - Edit existing files
- `"Bash"` - Execute shell commands
- `"Glob"` - Find files by pattern
- `"Grep"` - Search file contents

**Current Configuration**: `["Read", "Write", "Bash"]`

**Security Note**: Tools have full filesystem access within the working directory. In production, consider:
- Restricting to read-only tools
- Using containerization to limit filesystem access
- Implementing file path validation

#### permission_mode

**Type**: `str`

**Options**:
- `"acceptEdits"` - Automatically approve all file edits
- `"prompt"` - Prompt user before each edit (requires interactive terminal)

**Current Configuration**: `"acceptEdits"`

**Why acceptEdits?**: This is a web application without interactive terminal access. User approval would require implementing a custom approval UI.

#### setting_sources

**Type**: `List[str]`

**Options**:
- `"project"` - Load `CLAUDE.md` from project root
- `"user"` - Load user-level settings from `~/.config/claude/`
- `"system"` - Load system-level settings

**Current Configuration**: `["project"]`

**Effect**: The SDK automatically reads `/home/user/claude-agent/CLAUDE.md` and includes its content in the system prompt, giving Claude context about the project.

#### include_partial_messages

**Type**: `bool`

**Effect**:
- `True`: Emit streaming events during response generation
- `False`: Only emit complete messages after response finishes

**Current Configuration**: Dynamically set based on `stream` parameter in request

**Streaming Events**: When enabled, `receive_response()` yields `StreamEvent` objects with raw Claude API events like `content_block_delta`.

#### resume

**Type**: `Optional[str]`

**Effect**: Resume a previous conversation session using the provided session ID.

**How It Works**:
1. First request: `resume=None` → SDK creates new session
2. SDK returns `session_id` in `ResultMessage`
3. Backend stores `session_id` mapped to `response_id`
4. Follow-up request: `resume=session_id` → SDK loads conversation history

**Important**: Session IDs are SDK-internal. They're not the same as `response_id` shown to the user.

## Client Lifecycle

### 1. Create Client

```python
client = ClaudeSDKClient(options=options)
```

**Note**: Client is not connected yet - just initialized.

### 2. Connect

```python
await client.connect()
```

**What Happens**:
- Establishes connection to Claude API
- Loads conversation history if `resume` was provided
- Validates API key and configuration

**Errors**: Will raise exception if `ANTHROPIC_API_KEY` is invalid or missing.

### 3. Send Query

```python
await client.query(user_input)
```

**Effect**: Sends user message to Claude and triggers response generation.

**Note**: This doesn't return a response - use `receive_response()` to get it.

### 4. Receive Response

```python
async for message in client.receive_response():
    # Process messages
    pass
```

**What You Receive**:

The async generator yields different message types in sequence:

**a) StreamEvent** (only if `include_partial_messages=True`):

```python
# Not a documented type - detected by duck typing
is_stream_event = (
    not isinstance(message, (AssistantMessage, ResultMessage, SystemMessage))
    and hasattr(message, 'event')
    and isinstance(getattr(message, 'event', None), dict)
)

if is_stream_event:
    event = message.event
    if event["type"] == "content_block_delta":
        delta = event["delta"]
        if delta["type"] == "text_delta":
            text_chunk = delta["text"]
            # Accumulate text chunks
```

**b) AssistantMessage**:

```python
if isinstance(message, AssistantMessage):
    for block in message.content:
        if isinstance(block, TextBlock):
            full_text = block.text
```

**Contains**: Full or partial response text (depending on streaming mode)

**c) SystemMessage**:

Not currently used in this application.

**d) ResultMessage**:

```python
if isinstance(message, ResultMessage):
    usage = message.usage
    # {"input_tokens": 123, "output_tokens": 456}

    session_id = message.session_id
    # "session_xyz789" - store this for resume
```

**Contains**: Token usage statistics and session ID for conversation continuity.

### 5. Disconnect

```python
await client.disconnect()
```

**Effect**: Closes connection to Claude API and cleans up resources.

**Important**: Always call this, even on errors. Use try/finally:

```python
client = await create_client(...)
try:
    await client.query(...)
    async for message in client.receive_response():
        # Process
        pass
finally:
    await client.disconnect()
```

## Conversation Continuity

### Session ID Management

**Location**: `backend/main.py:167-170`

```python
# Maps user-facing response_id to SDK session_id
session_ids: Dict[str, str] = {}

# Example:
# session_ids["resp_abc123"] = "session_xyz789"
```

### Flow

**First Turn**:

```python
# 1. User sends message (no previous_response_id)
options = ClaudeAgentOptions(resume=None, ...)
client = ClaudeSDKClient(options=options)

# 2. Get response and extract session_id
async for message in client.receive_response():
    if isinstance(message, ResultMessage):
        session_id = message.session_id  # "session_xyz789"

# 3. Store mapping
response_id = "resp_abc123"
session_ids[response_id] = session_id
```

**Second Turn**:

```python
# 1. User sends message with previous_response_id="resp_abc123"
previous_response_id = "resp_abc123"
resume_session_id = session_ids[previous_response_id]  # "session_xyz789"

# 2. Create client with resume
options = ClaudeAgentOptions(resume=resume_session_id, ...)
client = ClaudeSDKClient(options=options)

# 3. SDK automatically loads previous conversation history
# User doesn't see it, but Claude has full context
```

### Why Not Reuse Clients?

**Question**: Why create a new `ClaudeSDKClient` for each request instead of keeping one per session?

**Answer**:

1. **HTTP is stateless**: Each request is independent, no persistent connection
2. **Concurrency**: Multiple users/conversations might be active simultaneously
3. **Resource management**: Ensures connections are properly closed
4. **Simplicity**: No need to manage client lifecycle across requests

**Trade-off**: Slight overhead of connecting on each request, but SDK handles this efficiently.

## Tool Execution

### How It Works

When Claude decides to use a tool, the SDK:

1. Detects tool use in Claude's response
2. Executes the tool (e.g., reads a file, runs a bash command)
3. Sends tool result back to Claude
4. Claude generates follow-up response incorporating the tool result

**All this happens transparently** within `receive_response()`.

### Example Flow

**User**: "What's in the README.md file?"

**Claude's Process** (internal to SDK):
1. "I need to read README.md"
2. SDK executes `Read` tool with path `/home/user/claude-agent/README.md`
3. SDK sends file contents back to Claude
4. Claude generates response: "The README contains..."

**What Backend Sees**:

```python
async for message in client.receive_response():
    if isinstance(message, AssistantMessage):
        # Only see final text:
        # "The README contains information about..."
```

**Tool execution details are hidden** - only the final text response is visible.

### Tool Execution Time

- Tool execution happens **during** `receive_response()` iteration
- The iteration **pauses** while tools execute
- With streaming, you might see deltas before and after tool execution
- Total response time includes tool execution time

### Multiple Tool Uses

Claude can use tools multiple times in a single response:

1. Read file A
2. Read file B
3. Generate response comparing them

All happens within one `receive_response()` call.

## Streaming Implementation Details

### Non-Streaming Mode

**Location**: `backend/main.py:212-253`

```python
options = ClaudeAgentOptions(..., include_partial_messages=False)

async for message in client.receive_response():
    if isinstance(message, AssistantMessage):
        # Full text available immediately
        full_text = message.content[0].text
```

**Behavior**:
- Waits for complete response before yielding `AssistantMessage`
- Only one `AssistantMessage` per response
- Simpler to handle, but no real-time feedback

### Streaming Mode

**Location**: `backend/main.py:256-472`

```python
options = ClaudeAgentOptions(..., include_partial_messages=True)

async for message in client.receive_response():
    if is_stream_event:
        # Partial text deltas
        if event["type"] == "content_block_delta":
            delta_text = event["delta"]["text"]
    elif isinstance(message, AssistantMessage):
        # Also receive final AssistantMessage at end
```

**Behavior**:
- Yields `StreamEvent` objects as text is generated
- Also yields final `AssistantMessage` with complete text
- Enables real-time UI updates

### Event Types in Streaming

**From Claude API** (via `StreamEvent.event`):

- `message_start` - Response started
- `content_block_start` - Content block started
- `content_block_delta` - Text delta (THIS IS WHAT WE USE)
- `content_block_stop` - Content block finished
- `message_delta` - Metadata update
- `message_stop` - Response complete

**We only handle**: `content_block_delta` with `text_delta` type.

## Error Handling

### SDK Errors

The SDK raises exceptions for:

- Invalid API key
- Network errors
- Rate limit exceeded
- Invalid model name
- Tool execution failures

**Current Handling**: `try/except` in non-streaming mode only (backend/main.py:517-524)

```python
try:
    result = await call_claude_agent(...)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Claude Agent error: {str(e)}")
```

**Streaming Mode**: No explicit error handling - connection just closes.

### Tool Execution Errors

If a tool fails (e.g., file not found), the SDK:

1. Captures the error
2. Sends error message to Claude
3. Claude generates response explaining the error

**Example**:

**User**: "Read nonexistent.txt"

**Claude's Response**: "I tried to read nonexistent.txt, but the file doesn't exist."

## Environment Variables

### Required

**ANTHROPIC_API_KEY**:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

**How SDK Uses It**: Automatically read from environment by the SDK.

### Optional

None - all configuration is done via `ClaudeAgentOptions`.

## Testing SDK Integration

### Unit Test (Mock SDK)

```python
from unittest.mock import AsyncMock, MagicMock

async def test_call_claude_agent():
    # Mock client
    mock_client = AsyncMock()
    mock_client.receive_response = AsyncMock()

    # Mock response
    mock_message = AssistantMessage(content=[TextBlock(text="Hello")])
    mock_result = ResultMessage(usage={"input_tokens": 10, "output_tokens": 5}, session_id="test")

    async def mock_receive():
        yield mock_message
        yield mock_result

    mock_client.receive_response.return_value = mock_receive()

    # Test
    result = await call_claude_agent("Hi", "claude-haiku-4-5-20251001")
    assert result["text"] == "Hello"
    assert result["input_tokens"] == 10
```

### Integration Test (Real SDK)

**Location**: `/test_multi_turn.py`

Tests real streaming multi-turn conversations:

```bash
python test_multi_turn.py
```

## Performance Considerations

### Connection Overhead

- Each request creates new client: ~100-200ms overhead
- Includes API handshake and optional session loading
- Acceptable for chat use case, but could be optimized

### Token Usage

- Multi-turn conversations send full history each time
- Token usage grows with conversation length
- Consider truncating old messages for long conversations

### Streaming Latency

- First token typically arrives within 200-500ms
- Subsequent tokens stream rapidly (20-50ms intervals)
- Overall response time depends on response length and tool execution

## Common Issues

### 1. "API key not found"

**Cause**: `ANTHROPIC_API_KEY` not set

**Solution**: Add to `.env` file in project root

### 2. Streaming Hangs on Second Request

**Cause**: SDK version <0.1.6

**Solution**: Upgrade to 0.1.6+

```bash
uv pip install --upgrade claude-agent-sdk
```

### 3. "Model not found"

**Cause**: Invalid model name

**Solution**: Use exact model names from Anthropic documentation

### 4. "Permission denied" During Tool Execution

**Cause**: File/directory permissions

**Solution**: Ensure backend has read/write access to working directory

### 5. Session Not Resuming

**Cause**: Server restarted (in-memory storage lost)

**Solution**: Implement persistent storage for `session_ids` mapping

## Future SDK Enhancements

Potential improvements for future SDK versions:

1. **Typed StreamEvent**: Export proper type instead of duck typing
2. **Connection Pooling**: Reuse connections across requests
3. **Conversation Truncation**: Built-in support for limiting history length
4. **Tool Result Visibility**: Option to expose tool execution details
5. **Retry Logic**: Automatic retry on transient failures
6. **Timeout Configuration**: Configurable timeouts for operations
7. **Usage Tracking**: Per-request usage tracking without parsing ResultMessage
8. **Custom Tools**: Define custom tools beyond built-in ones

## Additional Resources

- [Claude Agent SDK Documentation](reference/claude-agent-sdk.md) - Full SDK reference
- [Anthropic API Documentation](https://docs.anthropic.com/) - Claude API details
- [Backend Implementation](backend-implementation.md) - How backend uses SDK
