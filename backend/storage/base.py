"""
Abstract base class for conversation storage.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class ConversationStorage(ABC):
    """
    Abstract base class for conversation storage implementations.

    Implementations should handle persistence of conversations following
    the OpenAI Conversations API format.
    """

    @abstractmethod
    async def create_conversation(
        self,
        conversation_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation.

        Args:
            conversation_id: Unique identifier for the conversation
            metadata: Optional metadata key-value pairs
            items: Optional initial conversation items

        Returns:
            Conversation object with id, object, metadata, created_at
        """
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a conversation by ID.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            Conversation object or None if not found
        """
        pass

    @abstractmethod
    async def update_conversation(
        self,
        conversation_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update conversation metadata.

        Args:
            conversation_id: Unique identifier for the conversation
            metadata: New metadata to replace existing

        Returns:
            Updated conversation object or None if not found
        """
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def add_items(
        self,
        conversation_id: str,
        items: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Add items to a conversation.

        Args:
            conversation_id: Unique identifier for the conversation
            items: List of items to add

        Returns:
            List of added items or None if conversation not found
        """
        pass

    @abstractmethod
    async def list_items(
        self,
        conversation_id: str,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List items in a conversation.

        Args:
            conversation_id: Unique identifier for the conversation
            limit: Maximum number of items to return
            after: Cursor for pagination

        Returns:
            Object with data (list of items) and pagination info, or None if not found
        """
        pass

    @abstractmethod
    async def get_item(
        self,
        conversation_id: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific item from a conversation.

        Args:
            conversation_id: Unique identifier for the conversation
            item_id: Unique identifier for the item

        Returns:
            Item object or None if not found
        """
        pass

    @abstractmethod
    async def delete_item(
        self,
        conversation_id: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Delete an item from a conversation.

        Args:
            conversation_id: Unique identifier for the conversation
            item_id: Unique identifier for the item

        Returns:
            Updated conversation object or None if not found
        """
        pass
