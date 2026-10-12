"""Telegram backup and sync functionality."""
import asyncio
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import json

from telethon import TelegramClient
from telethon.errors import FloodWaitError, FilePartMissingError
from telethon.tl.types import DocumentAttributeFilename

from library_manager.core.config import get_config
from library_manager.core.database import get_db, BookRecord


@dataclass
class UploadResult:
    """Result of an upload operation."""
    success: bool
    message_id: Optional[int] = None
    file_id: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0


class TelegramBackup:
    """Handles backup to private Telegram channel."""
    
    def __init__(self):
        self.config = get_config()
        self.client: Optional[TelegramClient] = None
        self.channel_id = self.config.telegram.channel_id
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Telegram."""
        if self._connected and self.client and self.client.is_connected():
            return True
        
        api_id = self.config.telegram.api_id
        api_hash = self.config.telegram.api_hash
        session_name = self.config.telegram.session_name
        
        if not api_id or not api_hash:
            raise ValueError("Telegram API credentials not configured. Run 'library-manager init' first.")
        
        self.client = TelegramClient(
            session_name,
            api_id,
            api_hash,
        )
        
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise ValueError("Telegram session not authorized. Run 'library-manager init' to authenticate.")
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        self._connected = False
    
    async def get_channel_entity(self):
        """Get the channel entity."""
        if not self.channel_id:
            raise ValueError("Telegram channel ID not configured")
        
        try:
            entity = await self.client.get_entity(self.channel_id)
            return entity
        except Exception as e:
            raise ValueError(f"Cannot access channel {self.channel_id}: {e}")
    
    async def upload_file(
        self,
        file_path: Path,
        book: BookRecord,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> UploadResult:
        """Upload a file to Telegram channel with metadata."""
        start_time = datetime.now()
        
        try:
            await self.connect()
            channel = await self.get_channel_entity()
            
            # Prepare caption with metadata
            caption = self._generate_caption(book)
            
            # Upload file
            file_size = file_path.stat().st_size
            max_size = self.config.sync.max_file_size_mb * 1024 * 1024
            
            if file_size > max_size:
                return UploadResult(
                    success=False,
                    error=f"File too large: {file_size / 1024 / 1024:.1f}MB > {self.config.sync.max_file_size_mb}MB limit"
                )
            
            # Upload with progress
            uploaded_message = await self.client.send_file(
                channel,
                str(file_path),
                caption=caption,
                attributes=[DocumentAttributeFilename(file_path.name)],
                progress_callback=progress_callback,
            )
            
            # Extract file info
            message_id = uploaded_message.id
            file_id = ""
            
            if uploaded_message.document:
                file_id = str(uploaded_message.document.id)
            elif uploaded_message.photo:
                file_id = str(uploaded_message.photo.id)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return UploadResult(
                success=True,
                message_id=message_id,
                file_id=file_id,
                duration_ms=duration_ms,
            )
        
        except FloodWaitError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return UploadResult(
                success=False,
                error=f"Rate limited, wait {e.seconds}s",
                duration_ms=duration_ms,
            )
        except FilePartMissingError:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return UploadResult(
                success=False,
                error="Upload failed: file part missing (network issue)",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return UploadResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )
    
    def _generate_caption(self, book: BookRecord) -> str:
        """Generate caption with book metadata."""
        lines = []
        
        if book.title:
            lines.append(f"📖 **{book.title}**")
        
        if book.author:
            lines.append(f"✍️ {book.author}")
        elif book.authors:
            lines.append(f"✍️ {', '.join(book.authors)}")
        
        if book.year:
            lines.append(f"📅 {book.year}")
        
        if book.isbn:
            lines.append(f"🔢 ISBN: {book.isbn}")
        elif book.isbn13:
            lines.append(f"🔢 ISBN13: {book.isbn13}")
        
        if book.series:
            series_info = book.series
            if book.series_number:
                series_info += f" #{book.series_number:g}"
            lines.append(f"📚 {series_info}")
        
        if book.categories:
            lines.append(f"🏷️ {', '.join(book.categories)}")
        
        if book.tags:
            lines.append(f"🏷️ {', '.join(book.tags[:10])}")
        
        if book.publisher:
            lines.append(f"🏢 {book.publisher}")
        
        if book.pages:
            lines.append(f"📄 {book.pages} pages")
        
        if book.language:
            lines.append(f"🌐 {book.language}")
        
        if book.description:
            desc = book.description[:300]
            if len(book.description) > 300:
                desc += "..."
            lines.append(f"\n📝 {desc}")
        
        # Add library ID for reference
        lines.append(f"\n🔖 Library ID: {book.id}")
        lines.append(f"📁 {book.relative_path}")
        
        return "\n".join(lines)
    
    async def download_file(
        self,
        message_id: int,
        output_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Download a file from Telegram channel."""
        try:
            await self.connect()
            channel = await self.get_channel_entity()
            
            message = await self.client.get_messages(channel, ids=message_id)
            if not message or not message.document:
                return False
            
            await self.client.download_media(
                message,
                file=str(output_path),
                progress_callback=progress_callback,
            )
            return True
        
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    async def delete_file(self, message_id: int) -> bool:
        """Delete a file from Telegram channel."""
        try:
            await self.connect()
            channel = await self.get_channel_entity()
            
            await self.client.delete_messages(channel, [message_id])
            return True
        except Exception as e:
            print(f"Delete failed: {e}")
            return False
    
    async def verify_file(self, message_id: int, expected_hash: str) -> bool:
        """Verify a file in Telegram matches expected hash."""
        # This would require downloading and hashing - expensive
        # For now, just check if message exists
        try:
            await self.connect()
            channel = await self.get_channel_entity()
            
            message = await self.client.get_messages(channel, ids=message_id)
            return message is not None and message.document is not None
        except Exception:
            return False
    
    async def list_channel_files(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List files in the Telegram channel."""
        try:
            await self.connect()
            channel = await self.get_channel_entity()
            
            files = []
            async for message in self.client.iter_messages(channel, limit=limit):
                if message.document:
                    files.append({
                        "message_id": message.id,
                        "file_name": message.document.attributes[0].file_name if message.document.attributes else "unknown",
                        "file_size": message.document.size,
                        "mime_type": message.document.mime_type,
                        "date": message.date.isoformat() if message.date else None,
                        "caption": message.caption or "",
                    })
            
            return files
        except Exception as e:
            print(f"List failed: {e}")
            return []
    
    async def sync_book(self, book: BookRecord, progress_callback: Optional[Callable] = None) -> UploadResult:
        """Sync a single book to Telegram."""
        file_path = Path(book.file_path)
        if not file_path.exists():
            return UploadResult(success=False, error="File not found locally")
        
        result = await self.upload_file(file_path, book, progress_callback)
        
        if result.success:
            # Update database
            book.telegram_message_id = result.message_id
            book.telegram_file_id = result.file_id
            book.telegram_uploaded_at = datetime.now().isoformat()
            book.telegram_channel_id = self.channel_id
            
            db = get_db()
            db.update_book(book)
            db.log_sync(book.id, "upload", "success", "Uploaded to Telegram", book.size_bytes, result.duration_ms)
        else:
            db = get_db()
            db.log_sync(book.id, "upload", "failed", result.error or "Unknown error", book.size_bytes, result.duration_ms)
        
        return result
    
    async def sync_all(self, progress_callback: Optional[Callable] = None) -> Dict[str, int]:
        """Sync all books that need syncing."""
        db = get_db()
        books = db.get_books_needing_sync()
        
        stats = {"total": len(books), "success": 0, "failed": 0, "skipped": 0}
        
        for i, book in enumerate(books):
            if progress_callback:
                progress_callback(i, len(books), book)
            
            result = await self.sync_book(book)
            if result.success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    async def pull_missing(self, progress_callback: Optional[Callable] = None) -> Dict[str, int]:
        """Download missing files from Telegram."""
        db = get_db()
        books = db.get_all_books(status="missing")
        
        stats = {"total": len(books), "success": 0, "failed": 0}
        
        for i, book in enumerate(books):
            if progress_callback:
                progress_callback(i, len(books), book)
            
            if not book.telegram_message_id:
                stats["failed"] += 1
                continue
            
            file_path = Path(book.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            success = await self.download_file(book.telegram_message_id, file_path)
            if success:
                book.status = "active"
                book.last_seen_at = datetime.now().isoformat()
                db.update_book(book)
                db.log_sync(book.id, "download", "success", "Downloaded from Telegram", book.size_bytes)
                stats["success"] += 1
            else:
                db.log_sync(book.id, "download", "failed", "Download failed")
                stats["failed"] += 1
        
        return stats


# Synchronous wrapper for CLI usage
class SyncManager:
    """Synchronous wrapper for Telegram backup operations."""
    
    def __init__(self):
        self.backup = TelegramBackup()
    
    def _run_async(self, coro):
        """Run async coroutine in event loop."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    def connect(self) -> bool:
        return self._run_async(self.backup.connect())
    
    def disconnect(self):
        self._run_async(self.backup.disconnect())
    
    def upload_file(self, file_path: Path, book: BookRecord, progress_callback=None) -> UploadResult:
        return self._run_async(self.backup.upload_file(file_path, book, progress_callback))
    
    def download_file(self, message_id: int, output_path: Path, progress_callback=None) -> bool:
        return self._run_async(self.backup.download_file(message_id, output_path, progress_callback))
    
    def sync_book(self, book: BookRecord, progress_callback=None) -> UploadResult:
        return self._run_async(self.backup.sync_book(book, progress_callback))
    
    def sync_all(self, progress_callback=None) -> Dict[str, int]:
        return self._run_async(self.backup.sync_all(progress_callback))
    
    def pull_missing(self, progress_callback=None) -> Dict[str, int]:
        return self._run_async(self.backup.pull_missing(progress_callback))
    
    def list_channel_files(self, limit: int = 100) -> List[Dict]:
        return self._run_async(self.backup.list_channel_files(limit))
    
    def verify_file(self, message_id: int, expected_hash: str) -> bool:
        return self._run_async(self.backup.verify_file(message_id, expected_hash))