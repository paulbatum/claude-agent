"""
FastAPI backend that exposes Claude Agent SDK via OpenAI Responses API format.
"""
import os
import time
import uuid
from typing import Optional, List, Dict, Any, Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
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
# In-memory conversation storage (for previous_response_id support)
# ============================================================================

# Store ClaudeSDKClient instances per conversation
active_clients: Dict[str, ClaudeSDKClient] = {}

# Store response metadata
conversations: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Claude Agent SDK Integration
# ============================================================================

async def call_claude_agent(
    user_input: str,
    model: str,
    previous_response_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call Claude Agent SDK and return the response.

    Handles both new conversations and continuing existing ones.
    """
    # Determine if we're continuing a conversation
    client = None
    if previous_response_id and previous_response_id in active_clients:
        # Reuse existing client for conversation continuity
        client = active_clients[previous_response_id]
    else:
        # Create new client for new conversation
        options = ClaudeAgentOptions(
            model=model,
            allowed_tools=["Read", "Write", "Bash"],
            permission_mode="acceptEdits",
            setting_sources=["project"],  # Load CLAUDE.md
        )
        client = ClaudeSDKClient(options=options)
        await client.connect()

    # Send query to Claude
    await client.query(user_input)

    # Collect response
    response_text = ""
    input_tokens = 0
    output_tokens = 0

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text
        elif isinstance(message, ResultMessage):
            # Extract usage information
            if message.usage:
                input_tokens = message.usage.get("input_tokens", 0)
                output_tokens = message.usage.get("output_tokens", 0)

    return {
        "text": response_text or "No response generated",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "client": client,  # Return client for storage
    }


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/v1/responses")
async def create_response(request: CreateResponseRequest) -> ResponseObject:
    """
    Create a model response using Claude Agent SDK.
    Compatible with OpenAI's /v1/responses API.
    """
    # Generate unique IDs
    response_id = f"resp_{uuid.uuid4().hex}"
    message_id = f"msg_{uuid.uuid4().hex}"

    # Validate previous_response_id if provided
    if request.previous_response_id:
        if request.previous_response_id not in conversations:
            raise HTTPException(status_code=404, detail="Previous response not found")

    # Call Claude Agent SDK
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

    # Store conversation client and metadata
    if request.store:
        # Store the client for future conversation continuity
        active_clients[response_id] = result["client"]

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
