"""CLI interface for Library Manager."""
import click
from pathlib import Path
from typing import Optional
import sys
import os

from library_manager.core.config import get_config, set_config, Config
from library_manager.core.database import get_db, CatalogDB
from library_manager.organize.organizer import organize_library, LibraryOrganizer, OrganizeResult
from library_manager.telegram.sync import SyncManager, UploadResult
from library_manager.core.files import compute_sha256, extract_metadata, generate_clean_name, sanitize_filename


# Progress callback for rich output
def make_progress_callback(label: str, total: int):
    """Create a progress callback with rich progress bar."""
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )
        task = progress.add_task(label, total=total)
        
        def callback(current: int, total_items: int, item=None):
            progress.update(task, completed=current, description=f"{label} ({current}/{total_items})")
        
        return callback, progress
    except ImportError:
        # Fallback to simple output
        def callback(current: int, total_items: int, item=None):
            if current % 10 == 0 or current == total_items:
                print(f"  {label}: {current}/{total_items}")
        return callback, None


@click.group()
@click.version_option(version="1.0.0")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.pass_context
def cli(ctx, config, dry_run):
    """Library Manager - Personal offline library with Telegram cloud backup."""
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    
    if config:
        os.environ["LIBRARY_MANAGER_CONFIG"] = config


@cli.command()
@click.option("--api-id", type=int, help="Telegram API ID")
@click.option("--api-hash", help="Telegram API Hash")
@click.option("--channel-id", type=int, help="Telegram channel ID (negative for channels)")
@click.option("--bot-token", help="Bot token (alternative to user session)")
@click.option("--library-root", type=click.Path(), default="/mnt/Storage/library", help="Library root directory")
@click.option("--interactive/--non-interactive", default=True, help="Interactive setup")
@click.pass_context
def init(ctx, api_id, api_hash, channel_id, bot_token, library_root, interactive):
    """Initialize library manager configuration and Telegram connection."""
    click.echo("🔧 Initializing Library Manager...")
    
    config = get_config()
    
    if interactive:
        click.echo("\n📁 Library Configuration")
        library_root = click.prompt("Library root path", default=config.library_root, type=click.Path())
        config.library_root = library_root
        
        click.echo("\n📱 Telegram Configuration")
        click.echo("Get API credentials from https://my.telegram.org")
        api_id = click.prompt("API ID", type=int, default=config.telegram.api_id or "")
        api_hash = click.prompt("API Hash", default=config.telegram.api_hash or "")
        
        click.echo("\nCreate a private channel and add yourself as admin.")
        click.echo("Forward a message from the channel to @userinfobot to get the channel ID.")
        channel_id = click.prompt("Channel ID (negative number)", type=int, default=config.telegram.channel_id or "")
        
        use_bot = click.confirm("Use bot token instead of user session?", default=False)
        if use_bot:
            bot_token = click.prompt("Bot Token", default=config.telegram.bot_token or "")
            config.telegram.use_bot_token = True
            config.telegram.bot_token = bot_token
        
        config.telegram.api_id = api_id
        config.telegram.api_hash = api_hash
        config.telegram.channel_id = channel_id
    else:
        if api_id:
            config.telegram.api_id = api_id
        if api_hash:
            config.telegram.api_hash = api_hash
        if channel_id:
            config.telegram.channel_id = channel_id
        if bot_token:
            config.telegram.use_bot_token = True
            config.telegram.bot_token = bot_token
        if library_root:
            config.library_root = library_root
    
    # Create directories
    library_path = Path(config.library_root)
    for subdir in ["books", "_inbox", "_duplicates", "_metadata", ".library-manager"]:
        (library_path / subdir).mkdir(parents=True, exist_ok=True)
    
    # Save config
    config.save()
    
    click.echo(f"\n✅ Configuration saved to {config.library_root}/.library-manager/")
    click.echo(f"📁 Library root: {config.library_root}")
    
    if config.telegram.api_id and config.telegram.api_hash:
        click.echo("\n🔐 Testing Telegram connection...")
        sync = SyncManager()
        try:
            if sync.connect():
                click.echo("✅ Telegram connected successfully!")
            else:
                click.echo("❌ Telegram connection failed. Check credentials.")
        except Exception as e:
            click.echo(f"❌ Telegram connection error: {e}")
            click.echo("Run 'library-manager init' again to fix credentials.")
    
    # Create symlink if possible
    symlink_path = Path(config.symlink_path)
    try:
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(library_path)
        click.echo(f"🔗 Created symlink: {symlink_path} -> {library_path}")
    except PermissionError:
        click.echo(f"⚠️  Could not create symlink at {symlink_path} (need sudo)")
        click.echo(f"   Run: sudo ln -s {library_path} {symlink_path}")


@cli.command()
@click.option("--inbox-only", is_flag=True, help="Only organize inbox, not entire library")
@click.option("--no-rename", is_flag=True, help="Don't rename files, only organize")
@click.pass_context
def organize(ctx, inbox_only, no_rename):
    """Organize library files into structured folders with clean names."""
    dry_run = ctx.obj.get("dry_run", False)
    
    if dry_run:
        click.echo("🔍 DRY RUN - No changes will be made")
    
    click.echo("📚 Organizing library...")
    
    organizer = LibraryOrganizer(dry_run=dry_run)
    
    if inbox_only:
        click.echo("📥 Processing inbox only...")
        result = organizer.organize_inbox()
    else:
        result = organize_library(dry_run=dry_run)
    
    click.echo(f"\n✅ Organization complete!")
    click.echo(f"   📦 Moved: {result.moved}")
    click.echo(f"   ✏️  Renamed: {result.renamed}")
    click.echo(f"   🔄 Duplicates found: {result.duplicates_found}")
    click.echo(f"   ⏭️  Skipped: {result.skipped}")
    
    if result.errors:
        click.echo(f"\n❌ Errors ({len(result.errors)}):")
        for err in result.errors[:10]:
            click.echo(f"   - {err}")
        if len(result.errors) > 10:
            click.echo(f"   ... and {len(result.errors) - 10} more")


@cli.command()
@click.option("--all/--active-only", default=False, help="Include duplicate/archived books")
@click.pass_context
def dedupe(ctx, all):
    """Find and handle duplicate files."""
    dry_run = ctx.obj.get("dry_run", False)
    
    if dry_run:
        click.echo("🔍 DRY RUN - No changes will be made")
    
    click.echo("🔄 Finding duplicates...")
    
    organizer = LibraryOrganizer(dry_run=dry_run)
    result = organizer.find_duplicates()
    
    click.echo(f"\n✅ Deduplication complete!")
    click.echo(f"   🔄 Duplicates moved: {result.duplicates_found}")
    
    if result.errors:
        click.echo(f"\n❌ Errors ({len(result.errors)}):")
        for err in result.errors[:10]:
            click.echo(f"   - {err}")


@cli.command()
@click.pass_context
def metadata(ctx):
    """Extract/update metadata for all books."""
    dry_run = ctx.obj.get("dry_run", False)
    
    if dry_run:
        click.echo("🔍 DRY RUN - No changes will be made")
    
    click.echo("📋 Extracting metadata...")
    
    db = get_db()
    books = db.get_all_books(limit=10000)
    
    updated = 0
    errors = 0
    
    callback, progress = make_progress_callback("Extracting metadata", len(books))
    if progress:
        progress.start()
    
    try:
        for i, book in enumerate(books):
            if callback:
                callback(i, len(books), book)
            
            file_path = Path(book.file_path)
            if not file_path.exists():
                continue
            
            # Re-extract metadata
            metadata = extract_metadata(file_path)
            
            # Update book record
            changed = False
            if metadata.get("title") and not book.title:
                book.title = metadata["title"]
                changed = True
            if metadata.get("author") and not book.author:
                book.author = metadata["author"]
                changed = True
            if metadata.get("year") and not book.year:
                book.year = metadata["year"]
                changed = True
            if metadata.get("publisher") and not book.publisher:
                book.publisher = metadata["publisher"]
                changed = True
            if metadata.get("isbn") and not book.isbn:
                book.isbn = metadata["isbn"]
                changed = True
            if metadata.get("page_count") and not book.pages:
                book.pages = metadata["page_count"]
                changed = True
            
            if changed:
                db.update_book(book)
                updated += 1
    
    finally:
        if progress:
            progress.stop()
    
    click.echo(f"\n✅ Metadata extraction complete!")
    click.echo(f"   📝 Updated: {updated}")
    click.echo(f"   ❌ Errors: {errors}")


@cli.command()
@click.option("--push", "direction", flag_value="push", default=True, help="Upload to Telegram")
@click.option("--pull", "direction", flag_value="pull", help="Download from Telegram")
@click.option("--status", "direction", flag_value="status", help="Show sync status")
@click.pass_context
def sync(ctx, direction):
    """Sync library with Telegram backup."""
    dry_run = ctx.obj.get("dry_run", False)
    
    if dry_run and direction != "status":
        click.echo("🔍 DRY RUN - No changes will be made")
    
    sync_mgr = SyncManager()
    
    if direction == "status":
        click.echo("📊 Sync Status")
        db = get_db()
        stats = db.get_stats()
        
        click.echo(f"   📚 Total books: {stats['total_books']}")
        click.echo(f"   📦 Total size: {stats['total_size'] / 1024 / 1024 / 1024:.2f} GB")
        click.echo(f"   ☁️  Synced to Telegram: {stats['with_telegram']}")
        click.echo(f"   🔄 Duplicates: {stats['duplicates']}")
        click.echo(f"   📦 Archived: {stats['archived']}")
        click.echo(f"   ❓ Missing: {stats['missing']}")
        
        # Show pending sync
        books_needing = db.get_books_needing_sync()
        click.echo(f"   ⏳ Need sync: {len(books_needing)}")
        
        return
    
    if direction == "push":
        click.echo("☁️  Syncing to Telegram...")
        
        if not dry_run:
            try:
                sync_mgr.connect()
            except Exception as e:
                click.echo(f"❌ Telegram connection failed: {e}")
                click.echo("Run 'library-manager init' to configure Telegram.")
                return
        
        def progress_cb(current, total, book):
            if current % 5 == 0:
                click.echo(f"   📤 [{current}/{total}] {book.title[:50]}...")
        
        result = sync_mgr.sync_all(progress_cb)
        
        click.echo(f"\n✅ Sync complete!")
        click.echo(f"   ✅ Success: {result['success']}")
        click.echo(f"   ❌ Failed: {result['failed']}")
        click.echo(f"   ⏭️  Skipped: {result['skipped']}")
    
    elif direction == "pull":
        click.echo("📥 Downloading from Telegram...")
        
        if not dry_run:
            try:
                sync_mgr.connect()
            except Exception as e:
                click.echo(f"❌ Telegram connection failed: {e}")
                return
        
        def progress_cb(current, total, book):
            click.echo(f"   📥 [{current}/{total}] {book.title[:50]}...")
        
        result = sync_mgr.pull_missing(progress_cb)
        
        click.echo(f"\n✅ Download complete!")
        click.echo(f"   ✅ Success: {result['success']}")
        click.echo(f"   ❌ Failed: {result['failed']}")


@cli.command()
@click.argument("query")
@click.option("--limit", "-n", default=20, help="Maximum results")
@click.pass_context
def search(ctx, query, limit):
    """Search library catalog."""
    db = get_db()
    results = db.search(query, limit=limit)
    
    if not results:
        click.echo(f"No results for '{query}'")
        return
    
    click.echo(f"🔍 Found {len(results)} results for '{query}':\n")
    
    for i, book in enumerate(results, 1):
        click.echo(f"{i}. {book.title or 'Untitled'}")
        if book.author:
            click.echo(f"   ✍️  {book.author}")
        if book.year:
            click.echo(f"   📅 {book.year}")
        if book.categories:
            click.echo(f"   🏷️  {', '.join(book.categories)}")
        click.echo(f"   📁 {book.relative_path}")
        if book.telegram_message_id:
            click.echo(f"   ☁️  Telegram: #{book.telegram_message_id}")
        click.echo()


@cli.command()
@click.argument("identifier")
@click.pass_context
def info(ctx, identifier):
    """Show detailed information about a book."""
    db = get_db()
    
    # Try to find by ID, path, or hash
    book = None
    if identifier.isdigit():
        book = db.get_book(int(identifier))
    else:
        book = db.get_book_by_path(identifier)
        if not book:
            # Try by hash
            book = db.get_book_by_hash(identifier)
    
    if not book:
        click.echo(f"Book not found: {identifier}")
        return
    
    click.echo(f"📖 Book Details (ID: {book.id})")
    click.echo("=" * 50)
    click.echo(f"Title:       {book.title or 'Unknown'}")
    click.echo(f"Author:      {book.author or 'Unknown'}")
    if book.authors:
        click.echo(f"Authors:     {', '.join(book.authors)}")
    click.echo(f"Year:        {book.year or 'Unknown'}")
    click.echo(f"Publisher:   {book.publisher or 'Unknown'}")
    click.echo(f"ISBN:        {book.isbn or 'Unknown'}")
    click.echo(f"ISBN13:      {book.isbn13 or 'Unknown'}")
    click.echo(f"Language:    {book.language or 'Unknown'}")
    click.echo(f"Pages:       {book.pages or 'Unknown'}")
    click.echo(f"Series:      {book.series or 'None'} #{book.series_number or ''}")
    click.echo(f"Categories:  {', '.join(book.categories) or 'None'}")
    click.echo(f"Tags:        {', '.join(book.tags) or 'None'}")
    click.echo(f"Description: {book.description[:200] + '...' if book.description and len(book.description) > 200 else book.description or 'None'}")
    click.echo()
    click.echo(f"File:        {book.filename}")
    click.echo(f"Original:    {book.original_filename}")
    click.echo(f"Path:        {book.relative_path}")
    click.echo(f"Size:        {book.size_bytes / 1024 / 1024:.2f} MB")
    click.echo(f"SHA256:      {book.sha256_hash[:16]}...")
    click.echo(f"Status:      {book.status}")
    if book.telegram_message_id:
        click.echo(f"Telegram:    #{book.telegram_message_id} (Channel: {book.telegram_channel_id})")
        click.echo(f"Uploaded:    {book.telegram_uploaded_at or 'Unknown'}")
    click.echo(f"Created:     {book.created_at}")
    click.echo(f"Updated:     {book.updated_at}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show library statistics."""
    db = get_db()
    stats = db.get_stats()
    
    click.echo("📊 Library Statistics")
    click.echo("=" * 30)
    click.echo(f"Total Books:     {stats['total_books']}")
    click.echo(f"Total Size:      {stats['total_size'] / 1024 / 1024 / 1024:.2f} GB")
    click.echo(f"Synced to TG:    {stats['with_telegram']}")
    click.echo(f"Duplicates:      {stats['duplicates']}")
    click.echo(f"Archived:        {stats['archived']}")
    click.echo(f"Missing:         {stats['missing']}")
    
    if stats['categories']:
        click.echo("\n📂 By Category:")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
            click.echo(f"   {cat}: {count}")


@cli.command()
@click.pass_context
def verify(ctx):
    """Verify all cataloged files exist and match."""
    click.echo("🔍 Verifying library...")
    
    organizer = LibraryOrganizer()
    stats = organizer.verify_library()
    
    click.echo(f"\n✅ Verification complete!")
    click.echo(f"   ✅ OK: {stats['ok']}")
    click.echo(f"   ❌ Missing: {stats['missing']}")
    click.echo(f"   ⚠️  Size mismatch: {stats['size_mismatch']}")


@cli.command()
@click.option("--once", is_flag=True, help="Run once instead of continuous")
@click.pass_context
def watch(ctx, once):
    """Watch inbox for new files and auto-organize."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import time
    
    config = get_config()
    inbox = config.get_inbox_dir()
    
    click.echo(f"👀 Watching {inbox} for new files...")
    click.echo("Press Ctrl+C to stop")
    
    class InboxHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in [".pdf", ".epub", ".mobi", ".azw3", ".azw"]:
                click.echo(f"📥 New file detected: {file_path.name}")
                organizer = LibraryOrganizer()
                result = organizer.organize_inbox()
                if result.moved > 0:
                    click.echo(f"   ✅ Organized: {result.moved} files")
                if result.duplicates_found > 0:
                    click.echo(f"   🔄 Duplicates: {result.duplicates_found}")
    
    observer = Observer()
    observer.schedule(InboxHandler(), str(inbox), recursive=True)
    observer.start()
    
    try:
        if once:
            time.sleep(5)
            observer.stop()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    
    click.echo("\n👋 Watch stopped")


@cli.command()
@click.pass_context
def clean(ctx):
    """Clean up empty directories and temp files."""
    organizer = LibraryOrganizer()
    removed = organizer.cleanup_empty_dirs()
    click.echo(f"🧹 Removed {removed} empty directories")
    
    # Clean .crdownload files
    library_root = get_config().get_library_root()
    crdownloads = list(library_root.rglob("*.crdownload"))
    for f in crdownloads:
        f.unlink()
        click.echo(f"   Removed: {f.relative_to(library_root)}")
    
    click.echo("✅ Cleanup complete")


@cli.command()
@click.pass_context
def config_cmd(ctx):
    """Show current configuration."""
    config = get_config()
    
    click.echo("⚙️  Current Configuration")
    click.echo("=" * 30)
    click.echo(f"Library Root:    {config.library_root}")
    click.echo(f"Symlink Path:    {config.symlink_path}")
    click.echo(f"Telegram API ID: {config.telegram.api_id or 'Not set'}")
    click.echo(f"Telegram Channel: {config.telegram.channel_id or 'Not set'}")
    click.echo(f"Session Name:    {config.telegram.session_name}")
    click.echo(f"By Category:     {config.organization.by_category}")
    click.echo(f"By Author:       {config.organization.by_author}")
    click.echo(f"Series Folders:  {config.organization.create_series_folders}")


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()