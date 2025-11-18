"""
File-based conversation storage implementation.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
from .base import ConversationStorage


class FileConversationStorage(ConversationStorage):
    """
    File-based implementation of conversation storage.

    Stores conversations as JSON files in a directory structure:
    .conversations/
        {conversation_id}.json
    """

    def __init__(self, storage_dir: str = ".conversations"):
        """
        Initialize file-based storage.

        Args:
            storage_dir: Directory to store conversation files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def _get_conversation_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation."""
        return self.storage_dir / f"{conversation_id}.json"

    async def _read_conversation_file(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Read a conversation file from disk."""
        file_path = self._get_conversation_path(conversation_id)
        if not file_path.exists():
            return None

        try:
            # Use asyncio to run file I/O in thread pool
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: json.loads(file_path.read_text())
            )
            return data
        except (json.JSONDecodeError, OSError):
            return None

    async def _write_conversation_file(
        self,
        conversation_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Write a conversation file to disk."""
        file_path = self._get_conversation_path(conversation_id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: file_path.write_text(json.dumps(data, indent=2))
        )

    async def create_conversation(
        self,
        conversation_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        conversation = {
            "id": conversation_id,
            "object": "conversation",
            "metadata": metadata or {},
            "created_at": int(datetime.now().timestamp()),
            "items": items or []
        }

        await self._write_conversation_file(conversation_id, conversation)
        return self._format_conversation_response(conversation)

    def _format_conversation_response(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Format conversation for API response (excluding items)."""
        return {
            "id": conversation["id"],
            "object": conversation["object"],
            "metadata": conversation["metadata"],
            "created_at": conversation["created_at"]
        }

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by ID."""
        data = await self._read_conversation_file(conversation_id)
        if data is None:
            return None
        return self._format_conversation_response(data)

    async def update_conversation(
        self,
        conversation_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update conversation metadata."""
        data = await self._read_conversation_file(conversation_id)
        if data is None:
            return None

        data["metadata"] = metadata
        await self._write_conversation_file(conversation_id, data)
        return self._format_conversation_response(data)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        file_path = self._get_conversation_path(conversation_id)
        if not file_path.exists():
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, file_path.unlink)
            return True
        except OSError:
            return False

    async def add_items(
        self,
        conversation_id: str,
        items: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Add items to a conversation."""
        data = await self._read_conversation_file(conversation_id)
        if data is None:
            return None

        # Add items with timestamps if not present
        for item in items:
            if "created_at" not in item:
                item["created_at"] = int(datetime.now().timestamp())

        data["items"].extend(items)
        await self._write_conversation_file(conversation_id, data)
        return items

    async def list_items(
        self,
        conversation_id: str,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """List items in a conversation."""
        data = await self._read_conversation_file(conversation_id)
        if data is None:
            return None

        items = data.get("items", [])

        # Simple pagination: find index of 'after' item
        start_index = 0
        if after:
            for i, item in enumerate(items):
                if item.get("id") == after:
                    start_index = i + 1
                    break

        # Get paginated items
        paginated_items = items[start_index:start_index + limit]

        # Determine if there are more items
        has_more = start_index + limit < len(items)
        last_id = paginated_items[-1].get("id") if paginated_items else None

        return {
            "object": "list",
            "data": paginated_items,
            "has_more": has_more,
            "first_id": paginated_items[0].get("id") if paginated_items else None,
            "last_id": last_id
        }

    async def get_item(
        self,
        conversation_id: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific item from a conversation."""
        data = await self._read_conversation_file(conversation_id)
        if data is None:
            return None

        items = data.get("items", [])
        for item in items:
            if item.get("id") == item_id:
                return item

        return None

    async def delete_item(
        self,
        conversation_id: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Delete an item from a conversation."""
        data = await self._read_conversation_file(conversation_id)
        if data is None:
            return None

        items = data.get("items", [])
        updated_items = [item for item in items if item.get("id") != item_id]

        if len(updated_items) == len(items):
            # Item not found
            return None

        data["items"] = updated_items
        await self._write_conversation_file(conversation_id, data)
        return self._format_conversation_response(data)
