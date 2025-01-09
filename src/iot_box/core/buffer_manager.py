"""
Buffer Manager for IoT Box

Handles offline mode buffering and synchronization with Odoo.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import threading
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class BufferStatus(Enum):
    """Buffer status enumeration"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass
class BufferEntry:
    """Buffer entry data structure"""
    id: str
    event_data: Dict[str, Any]
    timestamp: float
    status: BufferStatus
    retry_count: int = 0
    error_message: Optional[str] = None
    sync_timestamp: Optional[float] = None


class BufferManager:
    """Manages offline buffering and synchronization"""
    
    def __init__(self, 
                 buffer_size: int = 1000,
                 sync_interval: int = 60,
                 max_retries: int = 3,
                 db_path: str = "data/buffer.db"):
        self.buffer_size = buffer_size
        self.sync_interval = sync_interval
        self.max_retries = max_retries
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.sync_lock = threading.Lock()
        self.sync_handlers: List[callable] = []
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for buffering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create buffer table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS buffer_entries (
                        id TEXT PRIMARY KEY,
                        event_data TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        status TEXT NOT NULL,
                        retry_count INTEGER DEFAULT 0,
                        error_message TEXT,
                        sync_timestamp REAL
                    )
                """)
                
                # Create index for efficient querying
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status_timestamp 
                    ON buffer_entries(status, timestamp)
                """)
                
                conn.commit()
                logger.info("Initialized buffer database")
                
        except Exception as e:
            logger.error(f"Error initializing buffer database: {e}")
            raise
    
    async def start(self):
        """Start the buffer manager"""
        self.running = True
        logger.info("Starting buffer manager")
        
        # Start sync task
        asyncio.create_task(self._sync_loop())
    
    async def stop(self):
        """Stop the buffer manager"""
        self.running = False
        logger.info("Stopping buffer manager")
        
        # Perform final sync
        await self.sync_all()
    
    async def _sync_loop(self):
        """Main synchronization loop"""
        while self.running:
            try:
                await self.sync_pending()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    def add_sync_handler(self, handler: callable):
        """Add a synchronization handler"""
        self.sync_handlers.append(handler)
        logger.info("Added sync handler")
    
    async def buffer_event(self, event_data: Dict[str, Any]) -> str:
        """Add event to buffer"""
        try:
            entry_id = f"buf_{int(time.time() * 1000)}_{hash(str(event_data)) % 10000}"
            
            entry = BufferEntry(
                id=entry_id,
                event_data=event_data,
                timestamp=time.time(),
                status=BufferStatus.PENDING
            )
            
            # Check buffer size
            if await self._get_buffer_count() >= self.buffer_size:
                logger.warning("Buffer is full, removing oldest entries")
                await self._remove_oldest_entries(100)  # Remove 100 oldest entries
            
            # Store in database
            await self._store_entry(entry)
            
            logger.debug(f"Buffered event {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Error buffering event: {e}")
            raise
    
    async def _store_entry(self, entry: BufferEntry):
        """Store buffer entry in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO buffer_entries 
                    (id, event_data, timestamp, status, retry_count, error_message, sync_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    json.dumps(entry.event_data),
                    entry.timestamp,
                    entry.status.value,
                    entry.retry_count,
                    entry.error_message,
                    entry.sync_timestamp
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error storing buffer entry: {e}")
            raise
    
    async def _get_buffer_count(self) -> int:
        """Get current buffer count"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM buffer_entries WHERE status = ?", 
                             (BufferStatus.PENDING.value,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting buffer count: {e}")
            return 0
    
    async def _remove_oldest_entries(self, count: int):
        """Remove oldest buffer entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM buffer_entries 
                    WHERE id IN (
                        SELECT id FROM buffer_entries 
                        WHERE status = ? 
                        ORDER BY timestamp ASC 
                        LIMIT ?
                    )
                """, (BufferStatus.PENDING.value, count))
                
                conn.commit()
                logger.info(f"Removed {count} oldest buffer entries")
                
        except Exception as e:
            logger.error(f"Error removing oldest entries: {e}")
    
    async def sync_pending(self):
        """Synchronize pending entries"""
        if not self.sync_handlers:
            logger.warning("No sync handlers registered")
            return
        
        with self.sync_lock:
            try:
                # Get pending entries
                pending_entries = await self._get_pending_entries()
                
                if not pending_entries:
                    return
                
                logger.info(f"Syncing {len(pending_entries)} pending entries")
                
                # Process each entry
                for entry in pending_entries:
                    await self._sync_entry(entry)
                
            except Exception as e:
                logger.error(f"Error syncing pending entries: {e}")
    
    async def sync_all(self):
        """Synchronize all pending entries"""
        logger.info("Starting full synchronization")
        
        while True:
            pending_count = await self._get_buffer_count()
            if pending_count == 0:
                break
            
            await self.sync_pending()
            await asyncio.sleep(1)  # Brief pause between batches
        
        logger.info("Full synchronization completed")
    
    async def _get_pending_entries(self, limit: int = 100) -> List[BufferEntry]:
        """Get pending buffer entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, event_data, timestamp, status, retry_count, error_message, sync_timestamp
                    FROM buffer_entries 
                    WHERE status = ? 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                """, (BufferStatus.PENDING.value, limit))
                
                entries = []
                for row in cursor.fetchall():
                    entry = BufferEntry(
                        id=row[0],
                        event_data=json.loads(row[1]),
                        timestamp=row[2],
                        status=BufferStatus(row[3]),
                        retry_count=row[4],
                        error_message=row[5],
                        sync_timestamp=row[6]
                    )
                    entries.append(entry)
                
                return entries
                
        except Exception as e:
            logger.error(f"Error getting pending entries: {e}")
            return []
    
    async def _sync_entry(self, entry: BufferEntry):
        """Synchronize a single entry"""
        try:
            # Update status to syncing
            entry.status = BufferStatus.SYNCING
            await self._update_entry_status(entry)
            
            # Try to sync with all handlers
            sync_success = False
            error_messages = []
            
            for handler in self.sync_handlers:
                try:
                    await handler(entry.event_data)
                    sync_success = True
                    break
                except Exception as e:
                    error_messages.append(str(e))
                    logger.warning(f"Sync handler failed: {e}")
            
            if sync_success:
                # Mark as synced
                entry.status = BufferStatus.SYNCED
                entry.sync_timestamp = time.time()
                entry.error_message = None
                await self._update_entry_status(entry)
                logger.debug(f"Successfully synced entry {entry.id}")
            else:
                # Increment retry count
                entry.retry_count += 1
                entry.error_message = "; ".join(error_messages)
                
                if entry.retry_count >= self.max_retries:
                    entry.status = BufferStatus.FAILED
                    logger.error(f"Entry {entry.id} failed after {self.max_retries} retries")
                else:
                    entry.status = BufferStatus.PENDING
                    logger.warning(f"Entry {entry.id} will be retried ({entry.retry_count}/{self.max_retries})")
                
                await self._update_entry_status(entry)
                
        except Exception as e:
            logger.error(f"Error syncing entry {entry.id}: {e}")
            entry.status = BufferStatus.FAILED
            entry.error_message = str(e)
            await self._update_entry_status(entry)
    
    async def _update_entry_status(self, entry: BufferEntry):
        """Update entry status in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE buffer_entries 
                    SET status = ?, retry_count = ?, error_message = ?, sync_timestamp = ?
                    WHERE id = ?
                """, (
                    entry.status.value,
                    entry.retry_count,
                    entry.error_message,
                    entry.sync_timestamp,
                    entry.id
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating entry status: {e}")
    
    async def get_buffer_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get counts by status
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM buffer_entries 
                    GROUP BY status
                """)
                
                status_counts = dict(cursor.fetchall())
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM buffer_entries")
                total_count = cursor.fetchone()[0]
                
                # Get oldest pending entry
                cursor.execute("""
                    SELECT MIN(timestamp) 
                    FROM buffer_entries 
                    WHERE status = ?
                """, (BufferStatus.PENDING.value,))
                
                oldest_timestamp = cursor.fetchone()[0]
                
                return {
                    "total_entries": total_count,
                    "status_counts": status_counts,
                    "oldest_pending_timestamp": oldest_timestamp,
                    "buffer_size_limit": self.buffer_size,
                    "sync_interval": self.sync_interval,
                    "max_retries": self.max_retries
                }
                
        except Exception as e:
            logger.error(f"Error getting buffer statistics: {e}")
            return {}
    
    async def clear_synced_entries(self, older_than_hours: int = 24):
        """Clear synced entries older than specified hours"""
        try:
            cutoff_time = time.time() - (older_than_hours * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM buffer_entries 
                    WHERE status = ? AND sync_timestamp < ?
                """, (BufferStatus.SYNCED.value, cutoff_time))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleared {deleted_count} old synced entries")
                
        except Exception as e:
            logger.error(f"Error clearing synced entries: {e}")
    
    async def export_buffer_data(self, 
                                start_time: Optional[float] = None,
                                end_time: Optional[float] = None,
                                status: Optional[BufferStatus] = None) -> List[Dict[str, Any]]:
        """Export buffer data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM buffer_entries WHERE 1=1"
                params = []
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                query += " ORDER BY timestamp ASC"
                
                cursor.execute(query, params)
                
                entries = []
                for row in cursor.fetchall():
                    entry = {
                        "id": row[0],
                        "event_data": json.loads(row[1]),
                        "timestamp": row[2],
                        "status": row[3],
                        "retry_count": row[4],
                        "error_message": row[5],
                        "sync_timestamp": row[6]
                    }
                    entries.append(entry)
                
                return entries
                
        except Exception as e:
            logger.error(f"Error exporting buffer data: {e}")
            return []
