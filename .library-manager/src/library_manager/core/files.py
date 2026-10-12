"""File utilities: hashing, metadata extraction, file operations."""
import hashlib
import xxhash
import magic
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import fitz  # PyMuPDF
import ebooklib
from ebooklib import epub
from PIL import Image
import io
import re
from datetime import datetime


def compute_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_xxhash(file_path: Path, chunk_size: int = 8192) -> str:
    """Compute xxHash (fast) of a file."""
    x = xxhash.xxh64()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            x.update(chunk)
    return x.hexdigest()


def get_mime_type(file_path: Path) -> str:
    """Get MIME type of a file."""
    mime = magic.Magic(mime=True)
    return mime.from_file(str(file_path))


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Get basic file information."""
    stat = file_path.stat()
    return {
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "mime_type": get_mime_type(file_path),
        "extension": file_path.suffix.lower(),
    }


def extract_pdf_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from PDF file."""
    metadata = {}
    page_count = 0
    
    try:
        doc = fitz.open(str(file_path))
        page_count = doc.page_count
        
        # Get document metadata
        pdf_meta = doc.metadata
        if pdf_meta:
            metadata = {
                "title": pdf_meta.get("title", "").strip(),
                "author": pdf_meta.get("author", "").strip(),
                "subject": pdf_meta.get("subject", "").strip(),
                "creator": pdf_meta.get("creator", "").strip(),
                "producer": pdf_meta.get("producer", "").strip(),
                "creation_date": pdf_meta.get("creationDate", "").strip(),
                "modification_date": pdf_meta.get("modDate", "").strip(),
                "keywords": pdf_meta.get("keywords", "").strip(),
            }
        
        # Try to extract text from first few pages for content analysis
        text_sample = ""
        for i in range(min(3, page_count)):
            page = doc[i]
            text_sample += page.get_text()[:2000]
        
        metadata["text_sample"] = text_sample[:5000]
        
        doc.close()
    except Exception as e:
        metadata["error"] = str(e)
    
    metadata["page_count"] = page_count
    return metadata


def extract_epub_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from EPUB file."""
    metadata = {}
    page_count = 0
    
    try:
        book = epub.read_epub(str(file_path))
        
        # Get metadata
        title = book.get_metadata("DC", "title")
        creator = book.get_metadata("DC", "creator")
        publisher = book.get_metadata("DC", "publisher")
        date = book.get_metadata("DC", "date")
        identifier = book.get_metadata("DC", "identifier")
        language = book.get_metadata("DC", "language")
        description = book.get_metadata("DC", "description")
        subject = book.get_metadata("DC", "subject")
        
        metadata = {
            "title": title[0][0] if title else "",
            "author": creator[0][0] if creator else "",
            "publisher": publisher[0][0] if publisher else "",
            "year": extract_year(date[0][0]) if date else None,
            "isbn": identifier[0][0] if identifier else "",
            "language": language[0][0] if language else "",
            "description": description[0][0] if description else "",
            "tags": [s[0] for s in subject] if subject else [],
        }
        
        # Count pages (approximate by content items)
        page_count = len(list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT)))
        
    except Exception as e:
        metadata["error"] = str(e)
    
    metadata["page_count"] = page_count
    return metadata


def extract_mobi_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from MOBI/AZW3 file."""
    # MOBI support is limited, use basic file info
    return {"error": "MOBI metadata extraction not fully supported"}


def extract_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from any supported file type."""
    ext = file_path.suffix.lower()
    
    if ext == ".pdf":
        return extract_pdf_metadata(file_path)
    elif ext in [".epub"]:
        return extract_epub_metadata(file_path)
    elif ext in [".mobi", ".azw3"]:
        return extract_mobi_metadata(file_path)
    else:
        return {"error": f"Unsupported format: {ext}"}


def extract_year(date_str: str) -> Optional[int]:
    """Extract year from various date formats."""
    if not date_str:
        return None
    
    # Try various patterns
    patterns = [
        r"(\d{4})",  # Just year
        r"D:(\d{4})",  # PDF date format
        r"(\d{4})-\d{2}-\d{2}",  # ISO date
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(date_str))
        if match:
            year = int(match.group(1))
            if 1000 <= year <= 2100:
                return year
    
    return None


def parse_authors(author_str: str) -> List[str]:
    """Parse author string into list of authors."""
    if not author_str:
        return []
    
    # Split by common separators
    separators = [",", ";", " and ", " & ", " with "]
    authors = [author_str]
    
    for sep in separators:
        new_authors = []
        for a in authors:
            new_authors.extend([x.strip() for x in a.split(sep) if x.strip()])
        authors = new_authors
    
    # Clean up
    authors = [re.sub(r"\s+", " ", a).strip() for a in authors]
    authors = [a for a in authors if a and len(a) > 1]
    
    return authors


def clean_filename(filename: str, remove_patterns: List[str] = None) -> str:
    """Clean up a filename by removing common junk patterns."""
    if remove_patterns is None:
        from library_manager.core.config import DEFAULT_CONFIG
        remove_patterns = DEFAULT_CONFIG["naming"]["remove_patterns"]
    
    name = filename
    
    # Remove extension temporarily
    stem = Path(filename).stem
    ext = Path(filename).suffix
    
    # Apply removal patterns
    for pattern in remove_patterns:
        stem = re.sub(pattern, "", stem, flags=re.IGNORECASE)
    
    # Clean up whitespace and special chars
    stem = re.sub(r"\s+", " ", stem)  # Multiple spaces to single
    stem = re.sub(r"\s*[-_]\s*$", "", stem)  # Trailing dashes/underscores
    stem = re.sub(r"^\s*[-_]\s*", "", stem)  # Leading dashes/underscores
    stem = re.sub(r"\s{2,}", " ", stem)  # Multiple spaces
    stem = stem.strip(" ._-")
    
    # Fix common issues
    stem = stem.replace("..", ".")
    stem = stem.replace("__", "_")
    stem = stem.replace("--", "-")
    
    return stem + ext


def generate_clean_name(metadata: Dict[str, Any], original_name: str, 
                        pattern: str = None, series_pattern: str = None) -> str:
    """Generate a clean filename from metadata."""
    from library_manager.core.config import get_config
    
    config = get_config()
    if pattern is None:
        pattern = config.naming.pattern
    if series_pattern is None:
        series_pattern = config.naming.series_pattern
    
    # Extract fields
    title = metadata.get("title", "").strip()
    author = metadata.get("author", "").strip()
    authors = metadata.get("authors", [])
    year = metadata.get("year")
    series = metadata.get("series", "").strip()
    series_num = metadata.get("series_number")
    ext = Path(original_name).suffix
    
    # If no good metadata, use cleaned original
    if not title and not author:
        return clean_filename(original_name)
    
    # Use first author if multiple
    if not author and authors:
        author = authors[0]
    
    # Determine if it's a series
    is_series = bool(series) and series_num is not None
    
    try:
        if is_series and series_pattern:
            name = series_pattern.format(
                author=author or "Unknown",
                title=title or "Untitled",
                year=year or "Unknown",
                series=series,
                series_num=series_num,
                ext=ext,
            )
        else:
            name = pattern.format(
                author=author or "Unknown",
                title=title or "Untitled",
                year=year or "Unknown",
                ext=ext,
            )
    except KeyError:
        # Fallback
        name = f"{author or 'Unknown'} - {title or 'Untitled'} ({year or 'Unknown'}){ext}"
    
    # Sanitize filename
    name = sanitize_filename(name)
    return name


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for filesystem compatibility."""
    # Remove/replace problematic characters
    filename = re.sub(r'[<>:\"/\\|?*]', "_", filename)
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)  # Control characters
    # Also sanitize directory separators in names (commas, etc. in path components)
    filename = filename.replace(",", "_")  # Commas cause issues in paths
    
    # Handle reserved names (Windows)
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", 
                "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", 
                "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
    stem = Path(filename).stem.upper()
    if stem in reserved:
        filename = "_" + filename
    
    # Trim if too long
    if len(filename) > max_length:
        stem = Path(filename).stem
        ext = Path(filename).suffix
        max_stem = max_length - len(ext)
        filename = stem[:max_stem] + ext
    
    return filename


def detect_series(metadata: Dict[str, Any], filename: str) -> Tuple[str, Optional[float]]:
    """Detect series name and number from metadata or filename."""
    series = metadata.get("series", "").strip()
    series_num = metadata.get("series_number")
    
    if series and series_num is not None:
        return series, series_num
    
    # Try to extract from filename
    stem = Path(filename).stem
    
    # Common series patterns
    patterns = [
        r"(.+?)\s+(\d+)\s*$",  # "Series Name 1"
        r"(.+?)\s+#(\d+)",  # "Series Name #1"
        r"(.+?)\s+Book\s+(\d+)",  # "Series Name Book 1"
        r"(.+?)\s+Vol\.?\s*(\d+)",  # "Series Name Vol 1"
        r"(.+?)\s+Volume\s+(\d+)",  # "Series Name Volume 1"
        r"(.+?)\s+(\d+)(?:st|nd|rd|th)",  # "Series Name 1st"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, stem, re.IGNORECASE)
        if match:
            potential_series = match.group(1).strip(" -_:.")
            try:
                num = float(match.group(2))
                if 0 < num < 1000:  # Reasonable range
                    return potential_series, num
            except ValueError:
                pass
    
    return "", None


def categorize_book(metadata: Dict[str, Any], filename: str, categories: Dict[str, List[str]]) -> List[str]:
    """Auto-categorize a book based on metadata and filename."""
    text = " ".join([
        metadata.get("title", ""),
        metadata.get("author", ""),
        metadata.get("description", ""),
        metadata.get("subject", ""),
        metadata.get("keywords", ""),
        filename,
    ]).lower()
    
    matched_categories = []
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in text:
                matched_categories.append(category)
                break
    
    return matched_categories if matched_categories else ["Uncategorized"]


def is_ebook_file(file_path: Path) -> bool:
    """Check if file is a supported ebook format."""
    return file_path.suffix.lower() in [".pdf", ".epub", ".mobi", ".azw3", ".azw"]


def get_cover_image(file_path: Path, output_path: Optional[Path] = None) -> Optional[bytes]:
    """Extract cover image from ebook."""
    ext = file_path.suffix.lower()
    
    try:
        if ext == ".pdf":
            doc = fitz.open(str(file_path))
            if doc.page_count > 0:
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
                img_data = pix.tobytes("png")
                doc.close()
                
                if output_path:
                    output_path.write_bytes(img_data)
                return img_data
        
        elif ext == ".epub":
            book = epub.read_epub(str(file_path))
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_COVER:
                    img_data = item.get_content()
                    if output_path:
                        output_path.write_bytes(img_data)
                    return img_data
                # Also check for image items with cover in name
                if "cover" in item.get_name().lower() and item.get_type() == ebooklib.ITEM_IMAGE:
                    img_data = item.get_content()
                    if output_path:
                        output_path.write_bytes(img_data)
                    return img_data
    
    except Exception:
        pass
    
    return None