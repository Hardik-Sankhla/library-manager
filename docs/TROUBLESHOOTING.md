# Troubleshooting Guide

## Quick Diagnostics

Run health check first:
```bash
lib doctor
```

## Common Issues

### Installation Issues

#### `library-manager: command not found`
```bash
# Install in development mode
pip install -e /mnt/Storage/library/.library-manager

# Or add to PATH
export PATH="/home/hardik-sankhla/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

#### `ModuleNotFoundError: No module named 'library_manager'`
```bash
# Reinstall package
cd /mnt/Storage/library/.library-manager
pip install -e .

# Check Python path
python3 -c "import library_manager; print(library_manager.__file__)"
```

#### `ImportError: cannot import name 'xxx'`
```bash
# Ensure all dependencies installed
pip install -r /mnt/Storage/library/requirements.txt

# Check specific module
python3 -c "import telethon; print('telethon ok')"
python3 -c "import pymupdf; print('pymupdf ok')"
```

### Telegram Issues

#### `Telegram connection failed` / `Session not authorized`
```bash
# Re-run init to re-authenticate
library-manager init

# Or delete session and retry
rm ~/.config/library-manager/library_bot.session*
library-manager init
```

#### `Cannot access channel` / `Channel ID invalid`
- Verify channel ID is **negative** (e.g., `-1001234567890`)
- Channel must be **Private** (not public)
- You must be **admin** of the channel
- If using bot: bot must be **admin** of channel

#### `Rate limited, wait X seconds`
```bash
# Reduce parallel uploads in config
# Edit ~/.config/library-manager/config.yaml:
sync:
  parallel_uploads: 1  # Reduce from 3

# Or wait and retry
```

#### `File too large`
- Telegram limit: **2GB per file**
- Default config: `max_file_size_mb: 1900` (1.9GB)
- Increase up to 2000 if needed:
```yaml
sync:
  max_file_size_mb: 2000
```
- Files larger than limit are **skipped automatically**

#### `FloodWaitError` / `FilePartMissingError`
- Network issues or Telegram rate limiting
- Wait a few minutes and retry
- Reduce `parallel_uploads` if persistent

### Database Issues

#### `Database locked` / `sqlite3.OperationalError`
```bash
# Check for running processes
ps aux | grep library-manager

# Kill if stuck
pkill -f library-manager

# Verify database integrity
sqlite3 /mnt/Storage/library/.library-manager/catalog.db "PRAGMA integrity_check;"
```

#### `Catalog out of sync` (files moved manually)
```bash
# Re-scan and rebuild
library-manager verify
library-manager organize
library-manager metadata
```

#### `Missing books` after verify
```bash
# Check _duplicates folder
ls /mnt/Storage/library/_duplicates/

# Restore from Telegram
library-manager sync pull

# Or restore from backup
lib-restore library-backup-XXXXXX.tar.gz
```

### File Organization Issues

#### Files not organizing
```bash
# Check inbox
ls /mnt/Storage/library/_inbox/

# Process inbox
lib inbox
# or
library-manager organize --inbox-only
```

#### Wrong categorization
- Edit categories in `~/.config/library-manager/config.yaml`
- Add custom keywords to existing categories
- Re-run: `library-manager metadata` then `library-manager organize`

#### Filename not cleaning
- Check `naming.remove_patterns` in config
- Add custom regex patterns
- Re-run: `library-manager organize`

#### Duplicates not detected
```bash
# Force dedupe scan
library-manager dedupe

# Check by hash manually
sqlite3 catalog.db "SELECT sha256_hash, COUNT(*) FROM books GROUP BY sha256_hash HAVING COUNT(*) > 1;"
```

### Sync Issues

#### Sync status shows 0 synced but files exist
```bash
# Check if files have telegram_message_id
sqlite3 catalog.db "SELECT COUNT(*) FROM books WHERE telegram_message_id IS NOT NULL;"

# Force re-sync all
library-manager sync push
```

#### Pull doesn't download files
```bash
# Check missing books have telegram_message_id
sqlite3 catalog.db "SELECT id, title, telegram_message_id FROM books WHERE status='missing';"

# Download specific book (requires custom script)
```

### Performance Issues

#### Slow metadata extraction
- Large PDFs take time to process
- Run in background: `nohup library-manager metadata &`
- Check progress: `tail -f /var/log/library-manager-metadata.log`

#### Slow search
- Database indexes are automatic
- For very large libraries (>10k books), consider:
```sql
CREATE INDEX idx_title_fts ON books(title);
```

#### High memory usage
- Process in batches
- Reduce `parallel_uploads` in config

### Permission Issues

#### `Permission denied` creating symlink
```bash
# Create manually with sudo
sudo ln -s /mnt/Storage/library /library
```

#### `Permission denied` on files
```bash
# Fix ownership
sudo chown -R hardik-sankhla:hardik-sankhla /mnt/Storage/library

# Fix permissions
find /mnt/Storage/library -type f -exec chmod 644 {} \;
find /mnt/Storage/library -type d -exec chmod 755 {} \;
```

### Cron Issues

#### Cron jobs not running
```bash
# Check cron service
systemctl status cron

# Check cron logs
grep CRON /var/log/syslog | tail -20

# Test command manually
/mnt/Storage/library/.library-manager/auto_sync.sh
```

#### Cron runs but fails
```bash
# Check logs
cat /var/log/library-manager-sync.log
cat /var/log/library-manager-inbox.log

# Ensure PATH in crontab
PATH=/usr/local/bin:/usr/bin:/bin
0 3 * * * /mnt/Storage/library/.library-manager/auto_sync.sh
```

## Debugging

### Enable Verbose Output
```bash
# Library manager verbose
library-manager --help

# Python debug
PYTHONPATH=/mnt/Storage/library/.library-manager/src python -m library_manager.cli.main --help
```

### Check Logs
```bash
# Sync logs
tail -f /var/log/library-manager-sync.log

# Inbox logs
tail -f /var/log/library-manager-inbox.log

# Verify logs
tail -f /var/log/library-manager-verify.log
```

### Database Queries
```bash
# Total books
sqlite3 catalog.db "SELECT COUNT(*) FROM books WHERE status='active';"

# By category
sqlite3 catalog.db "SELECT categories, COUNT(*) FROM books WHERE status='active' GROUP BY categories;"

# Missing files
sqlite3 catalog.db "SELECT title, file_path FROM books WHERE status='missing';"

# Duplicates
sqlite3 catalog.db "SELECT sha256_hash, COUNT(*) FROM books WHERE status='active' GROUP BY sha256_hash HAVING COUNT(*) > 1;"

# Need sync
sqlite3 catalog.db "SELECT title FROM books WHERE status='active' AND (telegram_message_id IS NULL OR telegram_uploaded_at < last_seen_at);"
```

### Reset Everything
```bash
# WARNING: Deletes all catalog data
rm /mnt/Storage/library/.library-manager/catalog.db
rm -rf /mnt/Storage/library/_metadata/*

# Reorganize from scratch
library-manager organize
library-manager metadata
```

## Getting Help

1. Run `lib doctor` for system health check
2. Check logs in `/var/log/library-manager-*.log`
3. Search GitHub Issues
4. Create new issue with:
   - `lib doctor` output
   - Relevant log excerpts
   - Steps to reproduce
   - Config (with secrets redacted)

## Emergency Recovery

### Books Lost Locally but in Telegram
```bash
# 1. Restore catalog from backup
lib-restore library-backup-YYYYMMDD.tar.gz

# 2. Download from Telegram
library-manager sync pull
```

### Telegram Channel Deleted
- Books are still in local `books/` directory
- Create new channel
- Update config with new channel ID
- Run `library-manager sync push` to re-upload

### Config Corrupted
```bash
# Restore from backup
lib-restore library-backup-YYYYMMDD.tar.gz

# Or reconfigure
library-manager init
```