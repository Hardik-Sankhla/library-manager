"""SQLite catalog database for Library Manager."""
import sqlite3
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from contextlib import contextmanager

from library_manager.core.config import get_config


@dataclass
class BookRecord:
    """Represents a book in the catalog."""
    id: Optional[int] = None
    file_path: str = ""
    relative_path: str = ""
    filename: str = ""
    original_filename: str = ""
    extension: str = ""
    size_bytes: int = 0
    sha256_hash: str = ""
    xxhash: str = ""
    
    # Metadata
    title: str = ""
    author: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    publisher: str = ""
    isbn: str = ""
    isbn13: str = ""
    language: str = ""
    pages: Optional[int] = None
    series: str = ""
    series_number: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    description: str = ""
    
    # Telegram backup
    telegram_message_id: Optional[int] = None
    telegram_file_id: str = ""
    telegram_uploaded_at: Optional[str] = None
    telegram_channel_id: Optional[int] = None
    
    # Status
    status: str = "active"  # active, duplicate, archived, missing
    is_duplicate_of: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # File metadata
    mime_type: str = ""
    page_count: Optional[int] = None
    creator_tool: str = ""
    producer: str = ""
    creation_date: str = ""
    modification_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "sha256_hash": self.sha256_hash,
            "xxhash": self.xxhash,
            "title": self.title,
            "author": self.author,
            "authors": json.dumps(self.authors),
            "year": self.year,
            "publisher": self.publisher,
            "isbn": self.isbn,
            "isbn13": self.isbn13,
            "language": self.language,
            "pages": self.pages,
            "series": self.series,
            "series_number": self.series_number,
            "tags": json.dumps(self.tags),
            "categories": json.dumps(self.categories),
            "description": self.description,
            "telegram_message_id": self.telegram_message_id,
            "telegram_file_id": self.telegram_file_id,
            "telegram_uploaded_at": self.telegram_uploaded_at,
            "telegram_channel_id": self.telegram_channel_id,
            "status": self.status,
            "is_duplicate_of": self.is_duplicate_of,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_seen_at": self.last_seen_at,
            "mime_type": self.mime_type,
            "page_count": self.page_count,
            "creator_tool": self.creator_tool,
            "producer": self.producer,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
        }
    
    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "BookRecord":
        data = dict(zip(columns, row))
        # Parse JSON fields
        for field_name in ["authors", "tags", "categories"]:
            if data.get(field_name):
                try:
                    data[field_name] = json.loads(data[field_name])
                except:
                    data[field_name] = []
            else:
                data[field_name] = []
        return cls(**data)


class CatalogDB:
    """Manages the SQLite catalog database."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL UNIQUE,
        relative_path TEXT NOT NULL,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        extension TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        sha256_hash TEXT NOT NULL,
        xxhash TEXT,
        
        title TEXT,
        author TEXT,
        authors TEXT,  -- JSON array
        year INTEGER,
        publisher TEXT,
        isbn TEXT,
        isbn13 TEXT,
        language TEXT,
        pages INTEGER,
        series TEXT,
        series_number REAL,
        tags TEXT,  -- JSON array
        categories TEXT,  -- JSON array
        description TEXT,
        
        telegram_message_id INTEGER,
        telegram_file_id TEXT,
        telegram_uploaded_at TEXT,
        telegram_channel_id INTEGER,
        
        status TEXT DEFAULT 'active',
        is_duplicate_of INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        
        mime_type TEXT,
        page_count INTEGER,
        creator_tool TEXT,
        producer TEXT,
        creation_date TEXT,
        modification_date TEXT,
        
        FOREIGN KEY (is_duplicate_of) REFERENCES books(id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_sha256 ON books(sha256_hash);
    CREATE INDEX IF NOT EXISTS idx_title ON books(title);
    CREATE INDEX IF NOT EXISTS idx_author ON books(author);
    CREATE INDEX IF NOT EXISTS idx_status ON books(status);
    CREATE INDEX IF NOT EXISTS idx_telegram_msg ON books(telegram_message_id);
    CREATE INDEX IF NOT EXISTS idx_relative_path ON books(relative_path);
    
    CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        operation TEXT NOT NULL,  -- upload, download, delete, verify
        status TEXT NOT NULL,  -- success, failed, skipped
        message TEXT,
        file_size INTEGER,
        duration_ms INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (book_id) REFERENCES books(id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_sync_log_book ON sync_log(book_id);
    CREATE INDEX IF NOT EXISTS idx_sync_log_created ON sync_log(created_at);
    
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_config().get_database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()
    
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor
    
    def _fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self._get_conn() as conn:
            return conn.execute(query, params).fetchone()
    
    def _fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        with self._get_conn() as conn:
            return conn.execute(query, params).fetchall()
    
    def add_book(self, book: BookRecord) -> int:
        """Add a new book to the catalog."""
        data = book.to_dict()
        data.pop("id", None)
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO books ({columns}) VALUES ({placeholders})"
        
        with self._get_conn() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            conn.commit()
            return cursor.lastrowid
    
    def update_book(self, book: BookRecord) -> bool:
        """Update an existing book record."""
        if book.id is None:
            return False
        
        data = book.to_dict()
        data.pop("id", None)
        data["updated_at"] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE books SET {set_clause} WHERE id = ?"
        params = tuple(data.values()) + (book.id,)
        
        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def get_book(self, book_id: int) -> Optional[BookRecord]:
        """Get a book by ID."""
        row = self._fetchone("SELECT * FROM books WHERE id = ?", (book_id,))
        if row:
            return BookRecord.from_row(row, list(row.keys()))
        return None
    
    def get_book_by_path(self, file_path: str) -> Optional[BookRecord]:
        """Get a book by file path."""
        row = self._fetchone("SELECT * FROM books WHERE file_path = ?", (file_path,))
        if row:
            return BookRecord.from_row(row, list(row.keys()))
        return None
    
    def get_book_by_hash(self, sha256_hash: str) -> Optional[BookRecord]:
        """Get a book by SHA256 hash."""
        row = self._fetchone("SELECT * FROM books WHERE sha256_hash = ?", (sha256_hash,))
        if row:
            return BookRecord.from_row(row, list(row.keys()))
        return None
    
    def find_duplicates(self) -> List[List[BookRecord]]:
        """Find all duplicate groups by hash."""
        rows = self._fetchall("""
            SELECT sha256_hash, COUNT(*) as count 
            FROM books 
            WHERE status = 'active' 
            GROUP BY sha256_hash 
            HAVING count > 1
        """)
        
        groups = []
        for row in rows:
            books = self._fetchall(
                "SELECT * FROM books WHERE sha256_hash = ? AND status = 'active' ORDER BY created_at",
                (row["sha256_hash"],)
            )
            groups.append([BookRecord.from_row(b, list(b.keys())) for b in books])
        return groups
    
    def search(self, query: str, limit: int = 50, offset: int = 0) -> List[BookRecord]:
        """Search books by title, author, or description."""
        search_term = f"%{query}%"
        rows = self._fetchall("""
            SELECT * FROM books 
            WHERE status = 'active' 
            AND (title LIKE ? OR author LIKE ? OR description LIKE ? OR filename LIKE ?)
            ORDER BY 
                CASE 
                    WHEN title LIKE ? THEN 0
                    WHEN author LIKE ? THEN 1
                    ELSE 2
                END,
                title
            LIMIT ? OFFSET ?
        """, (search_term, search_term, search_term, search_term, search_term, search_term, limit, offset))
        
        return [BookRecord.from_row(row, list(row.keys())) for row in rows]
    
    def get_all_books(self, status: str = "active", limit: int = 1000, offset: int = 0) -> List[BookRecord]:
        """Get all books with given status."""
        rows = self._fetchall(
            "SELECT * FROM books WHERE status = ? ORDER BY author, title LIMIT ? OFFSET ?",
            (status, limit, offset)
        )
        return [BookRecord.from_row(row, list(row.keys())) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        with self._get_conn() as conn:
            stats = {}
            stats["total_books"] = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'active'").fetchone()[0]
            stats["total_size"] = conn.execute("SELECT SUM(size_bytes) FROM books WHERE status = 'active'").fetchone()[0] or 0
            stats["duplicates"] = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'duplicate'").fetchone()[0]
            stats["archived"] = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'archived'").fetchone()[0]
            stats["missing"] = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'missing'").fetchone()[0]
            stats["with_telegram"] = conn.execute("SELECT COUNT(*) FROM books WHERE telegram_message_id IS NOT NULL AND status = 'active'").fetchone()[0]
            stats["categories"] = {}
            
            # Category breakdown
            cat_rows = conn.execute("""
                SELECT categories, COUNT(*) as count 
                FROM books 
                WHERE status = 'active' AND categories IS NOT NULL AND categories != '[]'
                GROUP BY categories
            """).fetchall()
            
            for row in cat_rows:
                try:
                    cats = json.loads(row["categories"])
                    for cat in cats:
                        stats["categories"][cat] = stats["categories"].get(cat, 0) + row["count"]
                except:
                    pass
            
            return stats
    
    def log_sync(self, book_id: Optional[int], operation: str, status: str, 
                 message: str = "", file_size: int = 0, duration_ms: int = 0):
        """Log a sync operation."""
        query = """
            INSERT INTO sync_log (book_id, operation, status, message, file_size, duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(query, (book_id, operation, status, message, file_size, duration_ms, datetime.now().isoformat()))
    
    def get_sync_history(self, book_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Get sync history."""
        if book_id:
            rows = self._fetchall(
                "SELECT * FROM sync_log WHERE book_id = ? ORDER BY created_at DESC LIMIT ?",
                (book_id, limit)
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM sync_log ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in rows]
    
    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        query = """
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
        """
        now = datetime.now().isoformat()
        self._execute(query, (key, value, now, value, now))
    
    def get_setting(self, key: str, default: str = "") -> str:
        """Get a setting value."""
        row = self._fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default
    
    def mark_missing(self, book_id: int):
        """Mark a book as missing."""
        self._execute(
            "UPDATE books SET status = 'missing', updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), book_id)
        )
    
    def mark_duplicate(self, book_id: int, duplicate_of_id: int):
        """Mark a book as duplicate of another."""
        self._execute(
            "UPDATE books SET status = 'duplicate', is_duplicate_of = ?, updated_at = ? WHERE id = ?",
            (duplicate_of_id, datetime.now().isoformat(), book_id)
        )
    
    def delete_book(self, book_id: int):
        """Delete a book record."""
        self._execute("DELETE FROM books WHERE id = ?", (book_id,))
    
    def update_last_seen(self, book_id: int):
        """Update last seen timestamp."""
        self._execute(
            "UPDATE books SET last_seen_at = ? WHERE id = ?",
            (datetime.now().isoformat(), book_id)
        )
    
    def get_books_needing_sync(self) -> List[BookRecord]:
        """Get books that need to be synced to Telegram."""
        rows = self._fetchall("""
            SELECT * FROM books 
            WHERE status = 'active' 
            AND (telegram_message_id IS NULL OR telegram_uploaded_at < last_seen_at)
            ORDER BY last_seen_at DESC
        """)
        return [BookRecord.from_row(row, list(row.keys())) for row in rows]


# Global database instance
_db: Optional[CatalogDB] = None

def get_db() -> CatalogDB:
    global _db
    if _db is None:
        _db = CatalogDB()
    return _db