"""Conversation memory management using SQLite."""
import json
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    metadata: Optional[dict] = None


@dataclass
class Conversation:
    """A conversation session with metadata."""
    id: str
    created_at: str
    updated_at: str
    messages: List[Message]
    metadata: Optional[dict] = None


class ConversationStore:
    """SQLite-backed conversation storage."""
    
    def __init__(self) -> None:
        settings = get_settings()
        self.db_path = Path(settings.conversation_db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            
            conn.commit()
        
        logger.info(f"Conversation database initialized at {self.db_path}")
    
    def create_conversation(self, metadata: Optional[dict] = None) -> str:
        """
        Create a new conversation session.
        
        Returns:
            The conversation ID
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (id, created_at, updated_at, metadata) VALUES (?, ?, ?, ?)",
                (conversation_id, now, now, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
        
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> None:
        """Add a message to a conversation."""
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Add message
            conn.execute(
                """INSERT INTO messages (conversation_id, role, content, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (conversation_id, role, content, now, json.dumps(metadata) if metadata else None)
            )
            
            # Update conversation timestamp
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
            
            conn.commit()
        
        logger.debug(f"Added {role} message to conversation {conversation_id}")
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation with all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get conversation metadata
            conv_row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,)
            ).fetchone()
            
            if not conv_row:
                return None
            
            # Get messages
            message_rows = conn.execute(
                """SELECT role, content, timestamp, metadata FROM messages
                   WHERE conversation_id = ? ORDER BY timestamp""",
                (conversation_id,)
            ).fetchall()
            
            messages = [
                Message(
                    role=row["role"],
                    content=row["content"],
                    timestamp=row["timestamp"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else None
                )
                for row in message_rows
            ]
            
            return Conversation(
                id=conv_row["id"],
                created_at=conv_row["created_at"],
                updated_at=conv_row["updated_at"],
                messages=messages,
                metadata=json.loads(conv_row["metadata"]) if conv_row["metadata"] else None
            )
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages from a conversation for context."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        # Return last N messages
        return conversation.messages[-limit:] if conversation.messages else []
    
    def list_conversations(self, limit: int = 20) -> List[dict]:
        """List recent conversations with metadata and a title preview."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """SELECT id, created_at, updated_at, metadata FROM conversations
                   ORDER BY updated_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()

            results = []
            for row in rows:
                title = None
                meta = json.loads(row["metadata"]) if row["metadata"] else None
                if isinstance(meta, dict):
                    title = meta.get("title") or meta.get("filename")
                if not title:
                    first = conn.execute(
                        """SELECT content FROM messages
                           WHERE conversation_id = ? AND role = 'user'
                           ORDER BY timestamp ASC LIMIT 1""",
                        (row["id"],),
                    ).fetchone()
                    if first and first["content"]:
                        content = first["content"]
                        title = content[:50] + ("..." if len(content) > 50 else "")
                results.append(
                    {
                        "id": row["id"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "title": title or "Conversation",
                        "metadata": meta,
                    }
                )
            return results
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted conversation: {conversation_id}")
            return deleted
    
    def get_context_for_query(self, conversation_id: str) -> str:
        """
        Get conversation context formatted for prompts.
        
        Returns a string with previous exchanges for context.
        """
        messages = self.get_conversation_history(conversation_id, limit=6)
        
        if not messages:
            return ""
        
        context_parts = ["PREVIOUS CONVERSATION:"]
        
        for msg in messages:
            if msg.role == "user":
                context_parts.append(f"User: {msg.content}")
            else:
                context_parts.append(f"Assistant: {msg.content}")
        
        context_parts.append("\n---")
        return "\n".join(context_parts)


class ConversationManager:
    """High-level conversation management with LLM integration."""
    
    def __init__(self) -> None:
        self.store = ConversationStore()
    
    def start_conversation(self, initial_text: str, metadata: Optional[dict] = None) -> str:
        """Start a new conversation with initial context."""
        conversation_id = self.store.create_conversation(metadata)
        
        self.store.add_message(
            conversation_id,
            "user",
            initial_text,
            {"type": "initial_input"}
        )
        
        return conversation_id
    
    def add_assistant_response(
        self,
        conversation_id: str,
        simplified_text: str,
        sources: Optional[List[dict]] = None
    ) -> None:
        """Add the assistant's simplification response."""
        self.store.add_message(
            conversation_id,
            "assistant",
            simplified_text,
            {"type": "simplification", "sources": sources}
        )
    
    def add_qa_pair(
        self,
        conversation_id: str,
        question: str,
        answer: str
    ) -> None:
        """Add a Q&A exchange to the conversation."""
        self.store.add_message(
            conversation_id,
            "user",
            question,
            {"type": "question"}
        )
        
        self.store.add_message(
            conversation_id,
            "assistant",
            answer,
            {"type": "answer"}
        )
    
    def get_conversation_context(self, conversation_id: str) -> str:
        """Get formatted conversation history for prompts."""
        return self.store.get_context_for_query(conversation_id)
