"""File organization and renaming logic."""
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from library_manager.core.config import get_config
from library_manager.core.database import get_db, BookRecord
from library_manager.core.files import (
    compute_sha256, compute_xxhash, extract_metadata, 
    generate_clean_name, sanitize_filename, detect_series,
    categorize_book, is_ebook_file, get_file_info
)


@dataclass
class OrganizeResult:
    """Result of an organize operation."""
    moved: int = 0
    renamed: int = 0
    duplicates_found: int = 0
    errors: List[str] = None
    skipped: int = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class LibraryOrganizer:
    """Organizes library files into structured folders."""
    
    def __init__(self, dry_run: bool = False):
        self.config = get_config()
        self.db = get_db()
        self.dry_run = dry_run
        self.library_root = self.config.get_library_root()
        self.books_dir = self.config.get_books_dir()
        self.inbox_dir = self.config.get_inbox_dir()
        self.duplicates_dir = self.config.get_duplicates_dir()
        self.metadata_dir = self.config.get_metadata_dir()
        
        # Ensure directories exist
        for d in [self.books_dir, self.inbox_dir, self.duplicates_dir, self.metadata_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def scan_inbox(self) -> List[Path]:
        """Scan inbox for ebook files."""
        files = []
        for ext in [".pdf", ".epub", ".mobi", ".azw3", ".azw"]:
            files.extend(self.inbox_dir.rglob(f"*{ext}"))
        return sorted(files)
    
    def scan_library(self) -> List[Path]:
        """Scan entire library for ebook files."""
        files = []
        for ext in [".pdf", ".epub", ".mobi", ".azw3", ".azw"]:
            files.extend(self.library_root.rglob(f"*{ext}"))
        # Exclude system directories
        exclude_dirs = {".library-manager", "_inbox", "_duplicates", "_metadata", "__pycache__"}
        files = [f for f in files if not any(part in exclude_dirs for part in f.parts)]
        return sorted(files)
    
    def _sanitize_author(self, author: str) -> str:
        """Sanitize author name for directory use."""
        # Remove problematic characters
        author = author.replace(",", "").replace(".", "").replace(";", "")
        author = re.sub(r"\s+", " ", author).strip()
        return sanitize_filename(author)
    
    def _sanitize_category(self, category: str) -> str:
        """Sanitize category name for directory use."""
        return sanitize_filename(category)
    
    def _sanitize_series(self, series: str) -> str:
        """Sanitize series name for directory use."""
        return sanitize_filename(series)
    
    def _get_unique_target_path(self, base_path: Path) -> Path:
        """Get a unique target path by adding counter if needed."""
        if not base_path.exists():
            return base_path
        
        stem = base_path.stem
        ext = base_path.suffix
        parent = base_path.parent
        counter = 1
        
        while True:
            new_name = f"{stem}_{counter}{ext}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
            if counter > 1000:  # Safety limit
                break
        
        return base_path
    
    def process_file(self, file_path: Path, relative_to: Path = None) -> Optional[BookRecord]:
        """Process a single file: extract metadata, compute hash, create record."""
        if relative_to is None:
            relative_to = self.library_root
        
        try:
            # Get file info
            file_info = get_file_info(file_path)
            
            # Compute hashes
            sha256_hash = compute_sha256(file_path)
            xxhash_val = compute_xxhash(file_path)
            
            # Check if already in database
            existing = self.db.get_book_by_hash(sha256_hash)
            if existing and existing.status == "active":
                # File already cataloged
                return existing
            
            # Extract metadata
            metadata = extract_metadata(file_path)
            
            # Detect series
            series, series_num = detect_series(metadata, file_path.name)
            if series:
                metadata["series"] = series
                metadata["series_number"] = series_num
            
            # Categorize
            categories = categorize_book(metadata, file_path.name, self.config.categories)
            metadata["categories"] = categories
            
            # Generate clean name
            clean_name = generate_clean_name(metadata, file_path.name)
            clean_name = sanitize_filename(clean_name)
            
            # Determine target path
            target_path = self._get_target_path(metadata, clean_name, categories)
            target_path = self._get_unique_target_path(target_path)
            relative_path = target_path.relative_to(self.library_root)
            
            # Parse authors
            author = metadata.get("author", "")
            authors = metadata.get("authors", [])
            if not authors and author:
                from library_manager.core.files import parse_authors
                authors = parse_authors(author)
            
            # Create book record
            book = BookRecord(
                file_path=str(target_path),
                relative_path=str(relative_path),
                filename=clean_name,
                original_filename=file_path.name,
                extension=file_path.suffix.lower(),
                size_bytes=file_info["size_bytes"],
                sha256_hash=sha256_hash,
                xxhash=xxhash_val,
                title=metadata.get("title", ""),
                author=author,
                authors=authors,
                year=metadata.get("year"),
                publisher=metadata.get("publisher", ""),
                isbn=metadata.get("isbn", ""),
                isbn13=metadata.get("isbn13", ""),
                language=metadata.get("language", ""),
                pages=metadata.get("page_count"),
                series=metadata.get("series", ""),
                series_number=metadata.get("series_number"),
                tags=metadata.get("tags", []),
                categories=categories,
                description=metadata.get("description", ""),
                mime_type=file_info["mime_type"],
                page_count=metadata.get("page_count"),
                creator_tool=metadata.get("creator", ""),
                producer=metadata.get("producer", ""),
                creation_date=metadata.get("creation_date", ""),
                modification_date=metadata.get("modification_date", ""),
            )
            
            return book
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None
    
    def _get_target_path(self, metadata: Dict, clean_name: str, categories: List[str]) -> Path:
        """Determine target path for a book."""
        author = metadata.get("author", "Unknown Author").strip()
        if not author and metadata.get("authors"):
            author = metadata["authors"][0]
        
        author = self._sanitize_author(author)
        
        # Primary category
        primary_cat = categories[0] if categories else "Uncategorized"
        primary_cat = self._sanitize_category(primary_cat)
        
        # Build path based on organization config
        parts = []
        
        if self.config.organization.by_category:
            parts.append(primary_cat)
        
        if self.config.organization.by_author:
            parts.append(author)
        
        # Series folder
        series = metadata.get("series", "").strip()
        if self.config.organization.create_series_folders and series:
            series = self._sanitize_series(series)
            parts.append(series)
        
        target_dir = self.books_dir.joinpath(*parts)
        return target_dir / clean_name
    
    def organize_inbox(self, progress_callback=None) -> OrganizeResult:
        """Organize files from inbox into library."""
        result = OrganizeResult()
        files = self.scan_inbox()
        
        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i, len(files), file_path)
            
            try:
                book = self.process_file(file_path, self.inbox_dir)
                if not book:
                    result.errors.append(f"Failed to process: {file_path}")
                    continue
                
                # Check for duplicates
                existing = self.db.get_book_by_hash(book.sha256_hash)
                if existing and existing.status == "active":
                    # Move to duplicates
                    self._move_to_duplicates(file_path, existing)
                    result.duplicates_found += 1
                    continue
                
                # Move file to organized location
                target_path = Path(book.file_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                if not self.dry_run:
                    shutil.move(str(file_path), str(target_path))
                
                # Add to database
                book_id = self.db.add_book(book)
                book.id = book_id
                
                # Save metadata
                self._save_metadata(book)
                
                if file_path != target_path:
                    result.moved += 1
                if file_path.name != book.filename:
                    result.renamed += 1
                
            except Exception as e:
                result.errors.append(f"Error organizing {file_path}: {e}")
        
        return result
    
    def reorganize_library(self, progress_callback=None) -> OrganizeResult:
        """Reorganize entire library - rename and move files to correct locations."""
        result = OrganizeResult()
        files = self.scan_library()
        
        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i, len(files), file_path)
            
            try:
                # Get existing record
                existing = self.db.get_book_by_path(str(file_path))
                if not existing:
                    # New file, process it
                    book = self.process_file(file_path)
                    if not book:
                        result.errors.append(f"Failed to process: {file_path}")
                        continue
                    
                    # Check for duplicates
                    dup = self.db.get_book_by_hash(book.sha256_hash)
                    if dup and dup.id != (existing.id if existing else -1):
                        self._move_to_duplicates(file_path, dup)
                        result.duplicates_found += 1
                        continue
                    
                    target_path = Path(book.file_path)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if not self.dry_run:
                        if file_path != target_path:
                            shutil.move(str(file_path), str(target_path))
                            result.moved += 1
                    
                    if file_path.name != book.filename:
                        result.renamed += 1
                    
                    if not existing:
                        book_id = self.db.add_book(book)
                        book.id = book_id
                    else:
                        book.id = existing.id
                        self.db.update_book(book)
                    
                    self._save_metadata(book)
                else:
                    # Existing record, check if rename/move needed
                    target_path = Path(existing.file_path)
                    clean_name = generate_clean_name({
                        "title": existing.title,
                        "author": existing.author,
                        "authors": existing.authors,
                        "year": existing.year,
                        "series": existing.series,
                        "series_number": existing.series_number,
                    }, existing.original_filename)
                    clean_name = sanitize_filename(clean_name)
                    
                    target_path = self._get_target_path({
                        "author": existing.author,
                        "authors": existing.authors,
                        "series": existing.series,
                        "series_number": existing.series_number,
                    }, clean_name, existing.categories)
                    target_path = self._get_unique_target_path(target_path)
                    
                    # Update record
                    existing.filename = clean_name
                    existing.file_path = str(target_path)
                    existing.relative_path = str(target_path.relative_to(self.library_root))
                    
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if not self.dry_run:
                        if file_path != target_path:
                            shutil.move(str(file_path), str(target_path))
                            result.moved += 1
                    
                    if file_path.name != clean_name:
                        result.renamed += 1
                    
                    self.db.update_book(existing)
                    self._save_metadata(existing)
            
            except Exception as e:
                result.errors.append(f"Error reorganizing {file_path}: {e}")
        
        return result
    
    def find_duplicates(self, progress_callback=None) -> OrganizeResult:
        """Find and handle duplicate files."""
        result = OrganizeResult()
        duplicate_groups = self.db.find_duplicates()
        
        for i, group in enumerate(duplicate_groups):
            if progress_callback:
                progress_callback(i, len(duplicate_groups), group)
            
            # Keep the first (oldest) file, move others to duplicates
            keeper = group[0]
            for dup_book in group[1:]:
                if dup_book.status != "duplicate":
                    dup_path = Path(dup_book.file_path)
                    if dup_path.exists():
                        self._move_to_duplicates(dup_path, keeper)
                    self.db.mark_duplicate(dup_book.id, keeper.id)
                    result.duplicates_found += 1
        
        return result
    
    def _move_to_duplicates(self, file_path: Path, keeper: BookRecord):
        """Move a duplicate file to the duplicates folder."""
        dup_dir = self.duplicates_dir / f"dup_of_{keeper.id}"
        dup_dir.mkdir(parents=True, exist_ok=True)
        
        target = dup_dir / file_path.name
        # Handle name collisions
        counter = 1
        while target.exists():
            stem = file_path.stem
            ext = file_path.suffix
            target = dup_dir / f"{stem}_{counter}{ext}"
            counter += 1
        
        if not self.dry_run:
            shutil.move(str(file_path), str(target))
    
    def _save_metadata(self, book: BookRecord):
        """Save book metadata to JSON file."""
        meta_file = self.metadata_dir / f"{book.id}.json"
        import json
        meta_file.write_text(json.dumps(book.to_dict(), indent=2))
    
    def cleanup_empty_dirs(self, root: Path = None) -> int:
        """Remove empty directories."""
        if root is None:
            root = self.library_root
        
        removed = 0
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            dir_path = Path(dirpath)
            # Skip system directories
            if any(part in {".library-manager", "_inbox", "_duplicates", "_metadata"} for part in dir_path.parts):
                continue
            
            if not dirnames and not filenames:
                try:
                    if not self.dry_run:
                        dir_path.rmdir()
                    removed += 1
                except OSError:
                    pass
        return removed
    
    def verify_library(self, progress_callback=None) -> Dict[str, int]:
        """Verify all cataloged files exist."""
        stats = {"total": 0, "missing": 0, "ok": 0, "size_mismatch": 0}
        
        books = self.db.get_all_books(limit=10000)
        
        for i, book in enumerate(books):
            if progress_callback:
                progress_callback(i, len(books), book)
            
            stats["total"] += 1
            file_path = Path(book.file_path)
            
            if not file_path.exists():
                stats["missing"] += 1
                self.db.mark_missing(book.id)
            else:
                # Check size
                actual_size = file_path.stat().st_size
                if actual_size != book.size_bytes:
                    stats["size_mismatch"] += 1
                else:
                    stats["ok"] += 1
                    self.db.update_last_seen(book.id)
        
        return stats


def organize_library(dry_run: bool = False, progress_callback=None) -> OrganizeResult:
    """Main entry point for organizing library."""
    organizer = LibraryOrganizer(dry_run=dry_run)
    
    # First organize inbox
    inbox_result = organizer.organize_inbox(progress_callback)
    
    # Then reorganize library
    library_result = organizer.reorganize_library(progress_callback)
    
    # Combine results
    combined = OrganizeResult(
        moved=inbox_result.moved + library_result.moved,
        renamed=inbox_result.renamed + library_result.renamed,
        duplicates_found=inbox_result.duplicates_found + library_result.duplicates_found,
        errors=inbox_result.errors + library_result.errors,
        skipped=inbox_result.skipped + library_result.skipped,
    )
    
    # Cleanup empty dirs
    removed = organizer.cleanup_empty_dirs()
    if removed:
        print(f"Removed {removed} empty directories")
    
    return combined