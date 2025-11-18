"""
FastAPI backend that exposes Claude Agent SDK via OpenAI Responses API format.
"""
import os
import time
import uuid
from typing import Optional, List, Dict, Any, Literal, AsyncIterator
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
    SystemMessage,
)

# Load environment variables
load_dotenv(dotenv_path="../.env")

app = FastAPI(title="Claude Agent API", version="0.1.0")

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# OpenAI Responses API Models
# ============================================================================

class OutputTextContent(BaseModel):
    type: Literal["output_text"] = "output_text"
    text: str
    annotations: List[Any] = Field(default_factory=list)


class MessageOutput(BaseModel):
    type: Literal["message"] = "message"
    id: str
    status: Literal["completed"] = "completed"
    role: Literal["assistant"] = "assistant"
    content: List[OutputTextContent]


class UsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


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


class CreateResponseRequest(BaseModel):
    model: str
    input: str
    stream: bool = False
    store: bool = True
    previous_response_id: Optional[str] = None
    temperature: Optional[float] = 1.0
    max_output_tokens: Optional[int] = None


# ============================================================================
# Streaming Event Models (OpenAI Responses API SSE format)
# ============================================================================

class StreamEventBase(BaseModel):
    """Base class for all streaming events."""
    type: str
    sequence_number: int = 0


class ResponseCreatedEvent(StreamEventBase):
    """Emitted when response is created."""
    type: Literal["response.created"] = "response.created"
    response: ResponseObject


class ResponseInProgressEvent(StreamEventBase):
    """Emitted when response is in progress."""
    type: Literal["response.in_progress"] = "response.in_progress"
    response: ResponseObject


class ResponseOutputItemAddedEvent(StreamEventBase):
    """Emitted when an output item is added."""
    type: Literal["response.output_item.added"] = "response.output_item.added"
    output_index: int
    item: MessageOutput


class ResponseContentPartAddedEvent(StreamEventBase):
    """Emitted when a content part is added."""
    type: Literal["response.content_part.added"] = "response.content_part.added"
    item_id: str
    output_index: int
    content_index: int
    part: OutputTextContent


class ResponseOutputTextDeltaEvent(StreamEventBase):
    """Emitted when text delta is streamed."""
    type: Literal["response.output_text.delta"] = "response.output_text.delta"
    item_id: str
    output_index: int
    content_index: int
    delta: str


class ResponseOutputTextDoneEvent(StreamEventBase):
    """Emitted when text output is complete."""
    type: Literal["response.output_text.done"] = "response.output_text.done"
    item_id: str
    output_index: int
    content_index: int
    text: str


class ResponseContentPartDoneEvent(StreamEventBase):
    """Emitted when a content part is done."""
    type: Literal["response.content_part.done"] = "response.content_part.done"
    item_id: str
    output_index: int
    content_index: int
    part: OutputTextContent


class ResponseOutputItemDoneEvent(StreamEventBase):
    """Emitted when an output item is done."""
    type: Literal["response.output_item.done"] = "response.output_item.done"
    output_index: int
    item: MessageOutput


class ResponseCompletedEvent(StreamEventBase):
    """Emitted when the response is completed."""
    type: Literal["response.completed"] = "response.completed"
    response: ResponseObject


# ============================================================================
# In-memory conversation storage (for previous_response_id support)
# ============================================================================

# Store session IDs for conversation continuity (instead of client instances)
session_ids: Dict[str, str] = {}

# Store response metadata
conversations: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Claude Agent SDK Integration
# ============================================================================

async def create_client(
    model: str,
    previous_response_id: Optional[str] = None,
    enable_streaming: bool = False
) -> ClaudeSDKClient:
    """
    Create a new Claude SDK client, optionally resuming a previous session.

    Args:
        model: Model name to use
        previous_response_id: Optional ID to continue existing conversation
        enable_streaming: Whether to enable partial message streaming

    Returns:
        ClaudeSDKClient instance
    """
    # Check if we're continuing a conversation
    resume_session_id = None
    if previous_response_id and previous_response_id in session_ids:
        resume_session_id = session_ids[previous_response_id]

    # Create new client for this request (always create fresh client)
    options = ClaudeAgentOptions(
        model=model,
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        setting_sources=["project"],  # Load CLAUDE.md
        include_partial_messages=enable_streaming,  # Enable streaming if requested
        resume=resume_session_id,  # Resume previous session if available
    )
    client = ClaudeSDKClient(options=options)
    await client.connect()
    return client


async def call_claude_agent(
    user_input: str,
    model: str,
    previous_response_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call Claude Agent SDK and return the complete response (non-streaming).

    Handles both new conversations and continuing existing ones.
    """
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
            # Extract usage information and session ID
            if message.usage:
                input_tokens = message.usage.get("input_tokens", 0)
                output_tokens = message.usage.get("output_tokens", 0)
            session_id = message.session_id

    # Disconnect client after response is complete
    await client.disconnect()

    return {
        "text": response_text or "No response generated",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "session_id": session_id,  # Return session ID for storage
    }


async def stream_claude_agent(
    user_input: str,
    model: str,
    response_id: str,
    message_id: str,
    previous_response_id: Optional[str] = None,
    store: bool = True
) -> AsyncIterator[str]:
    """
    Stream Claude Agent SDK response in OpenAI Responses API SSE format.

    Yields SSE-formatted events following the OpenAI Responses API spec.
    """
    client = await create_client(model, previous_response_id, enable_streaming=True)

    # Send query to Claude
    await client.query(user_input)

    # Initialize tracking variables
    sequence_number = 0
    response_text = ""
    input_tokens = 0
    output_tokens = 0
    session_id = None
    output_index = 0
    content_index = 0
    created_at = int(time.time())

    # Helper function to format SSE events
    def format_sse(event_type: str, data: dict) -> str:
        """Format data as SSE event."""
        json_data = json.dumps(data, separators=(',', ':'))
        return f"event: {event_type}\ndata: {json_data}\n\n"

    # Send response.created event
    initial_response = ResponseObject(
        id=response_id,
        created_at=created_at,
        status="in_progress",
        model=model,
        output=[],
        usage=UsageInfo(input_tokens=0, output_tokens=0, total_tokens=0),
        store=store
    )

    yield format_sse("response.created", {
        "type": "response.created",
        "response": initial_response.model_dump(),
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Send response.in_progress event
    yield format_sse("response.in_progress", {
        "type": "response.in_progress",
        "response": initial_response.model_dump(),
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Send response.output_item.added event
    message_output = MessageOutput(
        id=message_id,
        status="completed",
        content=[]
    )

    yield format_sse("response.output_item.added", {
        "type": "response.output_item.added",
        "output_index": output_index,
        "item": message_output.model_dump(),
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Send response.content_part.added event
    empty_content = OutputTextContent(text="")

    yield format_sse("response.content_part.added", {
        "type": "response.content_part.added",
        "item_id": message_id,
        "output_index": output_index,
        "content_index": content_index,
        "part": empty_content.model_dump(),
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Process streaming response from Claude SDK
    # Use receive_response() to get one complete response turn (including StreamEvents)
    # This will automatically stop after the response is complete
    async for message in client.receive_response():
        # Check if this is a StreamEvent by explicitly verifying it's not a known message type
        # and has an 'event' dict attribute (more robust than duck typing)
        is_stream_event = (
            not isinstance(message, (AssistantMessage, ResultMessage, SystemMessage))
            and hasattr(message, 'event')
            and isinstance(getattr(message, 'event', None), dict)
        )

        if is_stream_event:
            # Handle streaming events from the Claude API
            event = message.event
            event_type = event.get("type")

            if event_type == "content_block_delta":
                # Extract text delta from streaming event
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    delta_text = delta.get("text", "")
                    if delta_text:
                        response_text += delta_text

                        yield format_sse("response.output_text.delta", {
                            "type": "response.output_text.delta",
                            "item_id": message_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "delta": delta_text,
                            "sequence_number": sequence_number
                        })
                        sequence_number += 1

        elif isinstance(message, AssistantMessage):
            # Collect final text from AssistantMessage (fallback for non-streaming or final message)
            for block in message.content:
                if isinstance(block, TextBlock):
                    # Only use this if we haven't accumulated text from deltas
                    if not response_text:
                        response_text = block.text

        elif isinstance(message, ResultMessage):
            # Extract usage information and session ID
            if message.usage:
                input_tokens = message.usage.get("input_tokens", 0)
                output_tokens = message.usage.get("output_tokens", 0)
            session_id = message.session_id
            # Don't break yet - there might be more messages after tool execution
            # Only break when the iteration naturally completes

    # Send response.output_text.done event
    yield format_sse("response.output_text.done", {
        "type": "response.output_text.done",
        "item_id": message_id,
        "output_index": output_index,
        "content_index": content_index,
        "text": response_text,
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Send response.content_part.done event
    final_content = OutputTextContent(text=response_text)

    yield format_sse("response.content_part.done", {
        "type": "response.content_part.done",
        "item_id": message_id,
        "output_index": output_index,
        "content_index": content_index,
        "part": final_content.model_dump(),
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Send response.output_item.done event
    completed_message = MessageOutput(
        id=message_id,
        status="completed",
        content=[final_content]
    )

    yield format_sse("response.output_item.done", {
        "type": "response.output_item.done",
        "output_index": output_index,
        "item": completed_message.model_dump(),
        "sequence_number": sequence_number
    })
    sequence_number += 1

    # Send response.completed event with full response
    final_response = ResponseObject(
        id=response_id,
        created_at=created_at,
        status="completed",
        model=model,
        output=[completed_message],
        usage=UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        ),
        store=store
    )

    yield format_sse("response.completed", {
        "type": "response.completed",
        "response": final_response.model_dump(),
        "sequence_number": sequence_number
    })

    # Store conversation if requested
    if store:
        # Store session ID for conversation continuity (not the client instance)
        if session_id:
            session_ids[response_id] = session_id

        conversations[response_id] = {
            "request": {
                "model": model,
                "input": user_input,
                "previous_response_id": previous_response_id
            },
            "response": final_response.model_dump()
        }

    # Disconnect client after streaming is complete
    await client.disconnect()


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/v1/responses")
async def create_response(request: CreateResponseRequest):
    """
    Create a model response using Claude Agent SDK.
    Compatible with OpenAI's /v1/responses API.

    Supports both streaming (SSE) and non-streaming responses.
    """
    # Generate unique IDs
    response_id = f"resp_{uuid.uuid4().hex}"
    message_id = f"msg_{uuid.uuid4().hex}"

    # Validate previous_response_id if provided
    if request.previous_response_id:
        if request.previous_response_id not in conversations:
            raise HTTPException(status_code=404, detail="Previous response not found")

    # Handle streaming vs non-streaming
    if request.stream:
        # Return SSE streaming response
        return StreamingResponse(
            stream_claude_agent(
                user_input=request.input,
                model=request.model,
                response_id=response_id,
                message_id=message_id,
                previous_response_id=request.previous_response_id,
                store=request.store
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    else:
        # Non-streaming response
        try:
            result = await call_claude_agent(
                user_input=request.input,
                model=request.model,
                previous_response_id=request.previous_response_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Claude Agent error: {str(e)}")

        # Build response in OpenAI Responses API format
        response = ResponseObject(
            id=response_id,
            created_at=int(time.time()),
            status="completed",
            model=request.model,
            output=[
                MessageOutput(
                    id=message_id,
                    content=[
                        OutputTextContent(
                            text=result["text"]
                        )
                    ]
                )
            ],
            usage=UsageInfo(
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                total_tokens=result["input_tokens"] + result["output_tokens"]
            ),
            store=request.store
        )

        # Store conversation session ID and metadata
        if request.store:
            # Store the session ID for future conversation continuity
            if result["session_id"]:
                session_ids[response_id] = result["session_id"]

            conversations[response_id] = {
                "request": request.model_dump(),
                "response": response.model_dump()
            }

        return response


@app.get("/v1/responses/{response_id}")
async def get_response(response_id: str) -> ResponseObject:
    """
    Retrieve a stored response by ID.
    """
    if response_id not in conversations:
        raise HTTPException(status_code=404, detail="Response not found")

    stored = conversations[response_id]["response"]
    return ResponseObject(**stored)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "claude-agent-api"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
