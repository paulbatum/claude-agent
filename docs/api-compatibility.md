# OpenAI API Compatibility

## Overview

This project implements OpenAI's **Responses API** format, not the older Chat Completions API. This document explains the differences and compatibility details.

## Responses API vs Chat Completions API

### Responses API (What We Use)

**Endpoint**: `POST /v1/responses`

**Key Features**:
- Conversation continuity via `previous_response_id`
- Built-in conversation storage
- Simpler streaming format (one output item)
- Designed for chat applications

**Request Example**:
```json
{
  "model": "claude-haiku-4-5-20251001",
  "input": "Hello!",
  "stream": false,
  "store": true,
  "previous_response_id": null
}
```

### Chat Completions API (Not Used)

**Endpoint**: `POST /v1/chat/completions`

**Key Features**:
- Full message history in each request
- Stateless (no built-in conversation storage)
- More verbose streaming format
- Widely supported by existing tools

**Request Example**:
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}
```

### Why Responses API?

1. **Simpler State Management**: `previous_response_id` instead of full message arrays
2. **Built-in Storage**: `store: true` handles conversation persistence
3. **Cleaner Streaming**: Single output item vs multiple message deltas
4. **Modern Design**: Newer API with lessons learned from Chat Completions

## API Specification

### POST /v1/responses

**Location**: `backend/main.py:479-561`

#### Request Body

```typescript
interface CreateResponseRequest {
  model: string                      // Required: Model identifier
  input: string                      // Required: User message
  stream?: boolean                   // Optional: Enable streaming (default: false)
  store?: boolean                    // Optional: Store conversation (default: true)
  previous_response_id?: string      // Optional: Continue conversation
  temperature?: number               // Optional: Sampling temperature (default: 1.0)
  max_output_tokens?: number         // Optional: Max tokens to generate
}
```

**Field Details**:

- **model**: Exact Claude model name (e.g., `"claude-haiku-4-5-20251001"`)
- **input**: User's message text (no role prefix needed)
- **stream**: If `true`, returns SSE stream; if `false`, returns complete JSON
- **store**: If `true`, saves conversation for follow-up requests
- **previous_response_id**: Reference to previous response (for multi-turn)
- **temperature**: Currently accepted but not used (Claude SDK default)
- **max_output_tokens**: Currently accepted but not used

#### Response Body (Non-Streaming)

```typescript
interface ResponseObject {
  id: string                        // "resp_abc123"
  object: "response"                // Always "response"
  created_at: number                // Unix timestamp
  status: "completed" | "failed" | "in_progress"
  model: string                     // Model used
  output: MessageOutput[]           // Array of output messages
  usage: UsageInfo                  // Token usage
  store: boolean                    // Whether stored
  metadata: Record<string, any>     // Additional metadata
}

interface MessageOutput {
  type: "message"
  id: string                        // "msg_xyz789"
  status: "completed"
  role: "assistant"
  content: OutputTextContent[]
}

interface OutputTextContent {
  type: "output_text"
  text: string                      // Full response text
  annotations: any[]                // Currently empty
}

interface UsageInfo {
  input_tokens: number
  output_tokens: number
  total_tokens: number
}
```

**Example**:

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
      "id": "msg_xyz789",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "Hello! How can I assist you today?",
          "annotations": []
        }
      ]
    }
  ],
  "usage": {
    "input_tokens": 36,
    "output_tokens": 12,
    "total_tokens": 48
  },
  "store": true,
  "metadata": {}
}
```

#### Response Body (Streaming)

**Content-Type**: `text/event-stream`

**Format**: Server-Sent Events (SSE)

**Event Sequence**:

1. `response.created` - Response initiated
2. `response.in_progress` - Processing started
3. `response.output_item.added` - Output message added
4. `response.content_part.added` - Content part added
5. `response.output_text.delta` - Text chunk (multiple events)
6. `response.output_text.done` - Text complete
7. `response.content_part.done` - Content complete
8. `response.output_item.done` - Output complete
9. `response.completed` - Response complete

**SSE Format**:

```
event: response.created
data: {"type":"response.created","response":{...},"sequence_number":0}

event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"Hello","sequence_number":5}

event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"!","sequence_number":6}

event: response.completed
data: {"type":"response.completed","response":{...},"sequence_number":9}

```

**Event Types**:

```typescript
// Base event
interface StreamEvent {
  type: string
  sequence_number: number
}

// Text delta (most important for UI)
interface ResponseOutputTextDeltaEvent extends StreamEvent {
  type: "response.output_text.delta"
  item_id: string
  output_index: number
  content_index: number
  delta: string              // Text chunk to display
}

// Completion event (contains response_id)
interface ResponseCompletedEvent extends StreamEvent {
  type: "response.completed"
  response: ResponseObject   // Full response with ID
}
```

### GET /v1/responses/{response_id}

**Purpose**: Retrieve a stored response

**Request**:
```
GET /v1/responses/resp_abc123
```

**Response**: Same `ResponseObject` as non-streaming POST

**Error**: `404 Not Found` if response doesn't exist

### GET /health

**Purpose**: Health check endpoint

**Request**:
```
GET /health
```

**Response**:
```json
{
  "status": "ok",
  "service": "claude-agent-api"
}
```

## Multi-Turn Conversations

### Flow

**Turn 1**:

```json
POST /v1/responses
{
  "model": "claude-haiku-4-5-20251001",
  "input": "What is 2+2?",
  "store": true
}

→ Response:
{
  "id": "resp_abc123",
  "output": [{"content": [{"text": "2+2 equals 4."}]}],
  ...
}
```

**Turn 2**:

```json
POST /v1/responses
{
  "model": "claude-haiku-4-5-20251001",
  "input": "What about 3+3?",
  "previous_response_id": "resp_abc123"
}

→ Response:
{
  "id": "resp_def456",
  "output": [{"content": [{"text": "3+3 equals 6."}]}],
  ...
}
```

Claude remembers the context from Turn 1, even though it's not explicitly included.

### Storage Behavior

**If `store: true`** (default):
- Response is saved in memory
- Can be referenced by `previous_response_id`
- Can be retrieved via GET endpoint

**If `store: false`**:
- Response not saved
- Cannot be used as `previous_response_id`
- Cannot be retrieved via GET endpoint

**Important**: Backend storage is in-memory only. Server restart loses all conversations.

## Differences from OpenAI

### Model Names

**OpenAI**: `gpt-4`, `gpt-3.5-turbo`, etc.

**Our Implementation**: Claude model names
- `claude-haiku-4-5-20251001`
- `claude-sonnet-4-5-20250929`
- `claude-opus-4-5-20250514`

**No Validation**: Backend passes model name to Claude SDK without checking. Invalid names fail at Claude API level.

### Parameters Not Implemented

These parameters are accepted but **not currently used**:

- `temperature` - Accepted in request, but not passed to SDK
- `max_output_tokens` - Accepted but not enforced
- `top_p` - Not accepted
- `frequency_penalty` - Not accepted
- `presence_penalty` - Not accepted

**Future**: Could be implemented by extending `ClaudeAgentOptions`.

### Annotations

`OutputTextContent.annotations` is always an empty array. OpenAI uses this for:
- Citations
- Tool calls
- File references

**Future**: Could be populated with tool execution details from Claude SDK.

### Metadata

`ResponseObject.metadata` is always an empty dict. Could be used for:
- Request timing
- Model version
- Custom tags

## Error Responses

### 404 Not Found

**Trigger**: `previous_response_id` references non-existent response

```json
{
  "detail": "Previous response not found"
}
```

### 500 Internal Server Error

**Trigger**: Claude SDK error (non-streaming mode only)

```json
{
  "detail": "Claude Agent error: [error message]"
}
```

**Note**: Streaming mode doesn't return explicit errors - connection just closes.

### 422 Validation Error

**Trigger**: Invalid request body (Pydantic validation)

```json
{
  "detail": [
    {
      "loc": ["body", "model"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## CORS Configuration

**Location**: `backend/main.py:28-35`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Allowed Origins**:
- `http://localhost:5173` - Vite dev server
- `http://localhost:3000` - Alternative React dev server

**Production**: Should be restricted to actual frontend domain.

## Content Types

### Request

**Required**: `Content-Type: application/json`

**Example**:
```bash
curl -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","input":"Hello"}'
```

### Response (Non-Streaming)

**Content-Type**: `application/json`

### Response (Streaming)

**Content-Type**: `text/event-stream`

**Headers**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

## Client Examples

### JavaScript (Fetch API)

**Non-Streaming**:

```javascript
const response = await fetch('http://localhost:8000/v1/responses', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'claude-haiku-4-5-20251001',
    input: 'Hello!',
    stream: false,
  }),
})

const data = await response.json()
console.log(data.output[0].content[0].text)
```

**Streaming**:

```javascript
const response = await fetch('http://localhost:8000/v1/responses', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'claude-haiku-4-5-20251001',
    input: 'Hello!',
    stream: true,
  }),
})

const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break

  const chunk = decoder.decode(value)
  const lines = chunk.split('\n')

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6))
      if (event.type === 'response.output_text.delta') {
        console.log(event.delta)
      }
    }
  }
}
```

### Python (httpx)

**Non-Streaming**:

```python
import httpx

response = httpx.post('http://localhost:8000/v1/responses', json={
    'model': 'claude-haiku-4-5-20251001',
    'input': 'Hello!',
    'stream': False,
})

data = response.json()
print(data['output'][0]['content'][0]['text'])
```

**Streaming**:

```python
import httpx
import json

with httpx.stream(
    'POST',
    'http://localhost:8000/v1/responses',
    json={
        'model': 'claude-haiku-4-5-20251001',
        'input': 'Hello!',
        'stream': True,
    }
) as response:
    for line in response.iter_lines():
        if line.startswith('data: '):
            event = json.loads(line[6:])
            if event['type'] == 'response.output_text.delta':
                print(event['delta'], end='', flush=True)
```

### cURL

**Non-Streaming**:

```bash
curl -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-haiku-4-5-20251001",
    "input": "Hello!",
    "stream": false
  }'
```

**Streaming**:

```bash
curl -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "model": "claude-haiku-4-5-20251001",
    "input": "Hello!",
    "stream": true
  }'
```

Note: `-N` disables buffering for real-time output.

## Future Enhancements

### 1. Function Calling

OpenAI's Responses API supports function calling. Could be implemented by:
- Exposing Claude's tool use
- Mapping to OpenAI function format
- Allowing client to execute functions

### 2. Multi-Modal Inputs

Support images and other media:

```json
{
  "input": [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image_url", "image_url": {"url": "..."}}
  ]
}
```

### 3. Context Management

- `max_context_length` parameter
- Automatic truncation of old messages
- Summary of truncated context

### 4. Rate Limiting

- Per-user rate limits
- Token bucket algorithm
- Return `429 Too Many Requests`

### 5. API Keys

- Authentication via `Authorization: Bearer <key>` header
- Per-key usage tracking
- Key management endpoints

## Testing API Compatibility

### Manual Testing

```bash
# Start backend
cd backend
uvicorn main:app --reload

# Test non-streaming
curl -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","input":"Say hi in one word"}'

# Test streaming
curl -N -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","input":"Count to 3","stream":true}'
```

### Integration Testing

**Location**: `/test_multi_turn.py`

Tests multi-turn streaming conversations:

```bash
python test_multi_turn.py
```

## Additional Resources

- [OpenAI Responses API Reference](https://platform.openai.com/docs/api-reference/responses)
- [Backend Implementation](backend-implementation.md)
- [Frontend Implementation](frontend-implementation.md)
