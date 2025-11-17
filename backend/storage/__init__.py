"""
Storage abstraction layer for conversation persistence.
"""
from .base import ConversationStorage
from .file_storage import FileConversationStorage

__all__ = ["ConversationStorage", "FileConversationStorage"]
