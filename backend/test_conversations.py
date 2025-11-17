"""
Test script for conversation persistence functionality.
"""
import asyncio
import json
from storage import FileConversationStorage


async def test_conversation_storage():
    """Test the file-based conversation storage."""
    print("Testing FileConversationStorage...")

    # Initialize storage
    storage = FileConversationStorage(storage_dir="test_conversations")

    # Test 1: Create a conversation
    print("\n1. Creating conversation...")
    conversation = await storage.create_conversation(
        conversation_id="conv_test123",
        metadata={"topic": "testing", "user": "test_user"},
        items=[]
    )
    print(f"Created: {json.dumps(conversation, indent=2)}")
    assert conversation["id"] == "conv_test123"
    assert conversation["object"] == "conversation"
    assert conversation["metadata"]["topic"] == "testing"

    # Test 2: Get conversation
    print("\n2. Retrieving conversation...")
    retrieved = await storage.get_conversation("conv_test123")
    print(f"Retrieved: {json.dumps(retrieved, indent=2)}")
    assert retrieved is not None
    assert retrieved["id"] == "conv_test123"

    # Test 3: Add items to conversation
    print("\n3. Adding items to conversation...")
    items = [
        {
            "id": "msg_001",
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hello!"}]
        },
        {
            "id": "msg_002",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hi! How can I help?"}]
        }
    ]
    added = await storage.add_items("conv_test123", items)
    print(f"Added {len(added)} items")
    assert len(added) == 2

    # Test 4: List items
    print("\n4. Listing items...")
    result = await storage.list_items("conv_test123", limit=10)
    print(f"Found {len(result['data'])} items")
    assert len(result["data"]) == 2
    assert result["data"][0]["id"] == "msg_001"

    # Test 5: Get specific item
    print("\n5. Getting specific item...")
    item = await storage.get_item("conv_test123", "msg_001")
    print(f"Item: {json.dumps(item, indent=2)}")
    assert item is not None
    assert item["role"] == "user"

    # Test 6: Update conversation metadata
    print("\n6. Updating conversation metadata...")
    updated = await storage.update_conversation(
        "conv_test123",
        {"topic": "updated", "status": "active"}
    )
    print(f"Updated: {json.dumps(updated, indent=2)}")
    assert updated["metadata"]["topic"] == "updated"

    # Test 7: Delete an item
    print("\n7. Deleting an item...")
    conv_after_delete = await storage.delete_item("conv_test123", "msg_001")
    print(f"Conversation after delete: {json.dumps(conv_after_delete, indent=2)}")
    items_after = await storage.list_items("conv_test123")
    assert len(items_after["data"]) == 1

    # Test 8: Delete conversation
    print("\n8. Deleting conversation...")
    deleted = await storage.delete_conversation("conv_test123")
    print(f"Deleted: {deleted}")
    assert deleted is True

    # Verify it's gone
    retrieved_after_delete = await storage.get_conversation("conv_test123")
    assert retrieved_after_delete is None

    print("\n✅ All tests passed!")

    # Clean up test directory
    import shutil
    import os
    if os.path.exists("test_conversations"):
        shutil.rmtree("test_conversations")


if __name__ == "__main__":
    asyncio.run(test_conversation_storage())
