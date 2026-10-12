# Library Manager - Complete Documentation

A personal offline library management system with Telegram cloud backup. Organize, rename, deduplicate, and sync your book collection with unlimited free cloud storage via a private Telegram channel.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Commands Reference](#commands-reference)
- [Configuration](#configuration)
- [Telegram Setup](#telegram-setup)
- [Automation](#automation)
- [Scripts](#scripts)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install telethon pyrogram pymupdf ebooklib python-magic Pillow PyYAML tqdm rich click watchdog xxhash

# 2. Install library-manager in development mode
cd /mnt/Storage/library/.library-manager
pip install -e .

# 3. Initialize configuration (interactive)
library-manager init

# 4. Add books to inbox
cp ~/Downloads/*.pdf /mnt/Storage/library/_inbox/

# 5. Organize library
library-manager organize

# 6. Sync to Telegram cloud
library-manager sync push
```

### Using the `lib` Wrapper Script

For simpler daily usage, use the `lib` wrapper:

```bash
# Add to PATH
export PATH="/mnt/Storage/library/scripts:$PATH"

# Daily commands
lib add ~/Downloads/book.pdf      # Add file to inbox
lib organize                      # Full organize + rename
lib search "machine learning"     # Search books
lib sync                          # Backup to Telegram
lib status                        # Check sync status
lib doctor                        # Health check
```

---

## 🏗 Architecture

```
library-manager/
├── .library-manager/           # Source code & config
│   ├── src/
│   │   └── library_manager/
│   │       ├── __main__.py     # Entry point
│   │       ├── cli/
│   │       │   └── main.py     # Click CLI commands
│   │       ├── core/
│   │       │   ├── config.py   # Configuration management
│   │       │   ├── database.py # SQLite catalog
│   │       │   └── files.py    # Hashing, metadata, naming
│   │       ├── organize/
│   │       │   └── organizer.py # File organization logic
│   │       └── telegram/
│   │           └── sync.py     # Telegram backup/sync
│   ├── setup.py                # Package setup
│   ├── README.md               # This file
│   ├── SETUP_SUMMARY.md        # Setup summary
│   ├── auto_sync.sh            # Daily sync script
│   └── crontab.txt             # Cron job definitions
├── scripts/                    # Wrapper scripts
│   ├── lib                     # Main unified CLI
│   ├── lib-backup              # Backup catalog/config
│   ├── lib-restore             # Restore from backup
│   ├── lib-sync-status         # Detailed sync status
│   └── lib-clean               # Cleanup utility
├── docs/                       # Documentation
├── books/                      # Organized library (EXCLUDED from git)
├── _inbox/                     # Drop new files here (EXCLUDED)
├── _duplicates/                # Isolated duplicates (EXCLUDED)
├── _metadata/                  # Extracted metadata JSON (EXCLUDED)
└── .gitignore                  # Excludes all data directories
```

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  _inbox/    │────▶│  organize   │────▶│  books/     │
│  (drop)     │     │  + rename   │     │  (organized)│
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐            │
                    │  dedupe     │────────────┤
                    │  (by hash)  │            ▼
                    └─────────────┘     ┌─────────────┐
                                        │  metadata   │
                                        │  (extract)  │
                                        └──────┬──────┘
                                               │
                    ┌─────────────┐            │
                    │  catalog.db │◀───────────┤
                    │  (SQLite)   │            ▼
                    └──────┬──────┘     ┌─────────────┐
                           │            │  sync push  │
                           ▼            │  (Telegram) │
                    ┌─────────────┐     └─────────────┘
                    │  Telegram   │
                    │  Channel    │
                    └─────────────┘
```

---

## 📖 Commands Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `init` | Interactive setup (Telegram API, library path) |
| `organize` | Move files into structured folders with clean names |
| `organize --inbox-only` | Only process inbox, not entire library |
| `organize --no-rename` | Only organize, don't rename files |
| `dedupe` | Find and isolate duplicate files by content hash |
| `metadata` | Extract/update book metadata from PDFs/EPUBs |
| `sync push` | Upload new/changed files to Telegram |
| `sync pull` | Download missing files from Telegram |
| `sync status` | Show sync status |
| `search "query"` | Search catalog by title, author, description |
| `info <id\|path\|hash>` | Show detailed book information |
| `stats` | Show library statistics |
| `verify` | Check file integrity and catalog consistency |
| `watch` | Auto-organize inbox (daemon mode) |
| `watch --once` | Process inbox once (for cron) |
| `clean` | Remove empty dirs, temp files |
| `config-cmd` | Show current configuration |

### Wrapper Scripts (`scripts/`)

| Script | Description |
|--------|-------------|
| `lib` | Unified simplified CLI wrapper |
| `lib-backup` | Backup catalog.db and config (excludes books) |
| `lib-restore` | Restore from backup |
| `lib-sync-status` | Detailed sync status with progress |
| `lib-clean` | Deep cleanup (empty dirs, temp files, orphaned metadata) |

### Global Options

| Option | Description |
|--------|-------------|
| `--config, -c` | Config file path |
| `--dry-run` | Preview changes without making them |
| `--version` | Show version |
| `--help` | Show help |

---

## ⚙️ Configuration

Config file: `~/.config/library-manager/config.yaml`

```yaml
library_root: "/mnt/Storage/library"
symlink_path: "/library"
telegram:
  api_id: 123456
  api_hash: "your_api_hash"
  channel_id: -1001234567890
  session_name: "library_bot"
  use_bot_token: false
  bot_token: null
organization:
  by_category: true
  by_author: true
  create_series_folders: true
  max_depth: 3
naming:
  pattern: "{author} - {title} ({year}){ext}"
  series_pattern: "{author} - {series} {series_num:02d} - {title} ({year}){ext}"
  remove_patterns:
    - "\(Z-Library\)"
    - "_OceanofPDF\.com_"
    - "\[.*?\]"
    - "\(.*?Copy.*?\)"
    - "\s*-\s*Copy\s*\d*"
    - "\s*\d{10,}\s*"
    - "^\d+[_-\s]+"
    - "\(PDFDrive\)"
    - "\(z-lib\.org\)"
    - "\[.*?libribook\.com.*?\]"
    - "\[.*?O'Reilly.*?\]"
categories:
  AI/ML/LLM: ["ai", "machine learning", "deep learning", "llm", ...]
  Programming: ["programming", "software", "clean code", ...]
  # ... more categories
sync:
  auto_sync: false
  sync_interval_hours: 24
  max_file_size_mb: 1900
  parallel_uploads: 3
  verify_checksums: true
database:
  path: null  # Auto: {library_root}/.library-manager/catalog.db
```

### Library Structure (After Organize)

```
/mnt/Storage/library/
├── books/
│   ├── AI_ML_LLM/
│   │   ├── Author Name/
│   │   │   ├── Author Name - Book Title (2023).pdf
│   │   │   └── Series Name/
│   │   │       ├── Author Name - Series Name 01 - Book One (2022).pdf
│   │   │       └── Author Name - Series Name 02 - Book Two (2023).pdf
│   ├── Programming/
│   └── ...
├── _inbox/                   # Drop new files here
├── _duplicates/              # Isolated duplicates
├── _metadata/                # JSON metadata per book
├── catalog.db                # SQLite catalog
└── .library-manager/         # Source code & config
```

### File Naming Convention

```
Author Name - Book Title (Year).ext
Author Name - Series Name 01 - Book Title (Year).ext
```

Automatically removes:
- `(Z-Library)`, `_OceanofPDF.com_`, `[libribook.com]`
- `- Copy`, `- Copy (1)`, `(PDFDrive)`, `(z-lib.org)`
- Leading numbers, extra spaces, special characters

---

## 📱 Telegram Setup

### 1. Get API Credentials
1. Go to https://my.telegram.org
2. Log in with your phone number
3. Create a new application
4. Note down `api_id` and `api_hash`

### 2. Create Private Channel
1. Open Telegram
2. Create a **Private Channel** (not a group!)
3. Add yourself as admin
4. Optional: Create a bot via @BotFather and add as admin

### 3. Get Channel ID
1. Forward any message from your channel to @userinfobot
2. It will reply with the channel ID (negative number, e.g., `-1001234567890`)

### 4. Configure
```bash
# Interactive
library-manager init

# Or non-interactive
library-manager init --non-interactive \
  --api-id YOUR_API_ID \
  --api-hash "YOUR_API_HASH" \
  --channel-id -100XXXXXXXXXX
```

### 5. Test Sync
```bash
library-manager sync push
library-manager sync status
```

---

## 🤖 Automation

### Cron Jobs (Recommended)

```bash
# Install cron jobs
lib cron-install

# Or manually:
crontab /mnt/Storage/library/.library-manager/crontab.txt
```

**Installed jobs:**
- **Daily 3 AM**: Sync new/changed files to Telegram
- **Hourly**: Process inbox for new files
- **Weekly Sunday 4 AM**: Verify library integrity

### Cron Job Details

```bash
# Daily sync at 3 AM
0 3 * * * /mnt/Storage/library/.library-manager/auto_sync.sh

# Hourly inbox processing
0 * * * * /usr/bin/library-manager watch --once >> /var/log/library-manager-inbox.log 2>&1

# Weekly verification
0 4 * * 0 /usr/bin/library-manager verify >> /var/log/library-manager-verify.log 2>&1
```

### Systemd Service (Alternative)

Create `/etc/systemd/system/library-manager-sync.service`:
```ini
[Unit]
Description=Library Manager Daily Sync
After=network.target

[Service]
Type=oneshot
User=hardik-sankhla
Environment=PATH=/usr/local/bin:/usr/bin
ExecStart=/usr/bin/library-manager sync push
StandardOutput=journal
StandardError=journal
```

Create `/etc/systemd/system/library-manager-sync.timer`:
```ini
[Unit]
Description=Daily Library Manager Sync

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now library-manager-sync.timer
```

---

## 📜 Scripts

### `lib` - Main Wrapper
```bash
# Add to PATH permanently
echo 'export PATH="/mnt/Storage/library/scripts:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Now use anywhere
lib add ~/Downloads/book.pdf
lib organize
lib search "python"
lib sync
```

### `lib-backup` - Backup Catalog & Config
```bash
# Creates timestamped backup excluding books
lib-backup

# Backups stored in ~/library-backups/
# Keeps last 10 backups automatically
```

### `lib-restore` - Restore from Backup
```bash
# List available backups
ls ~/library-backups/

# Restore specific backup
lib-restore library-backup-20241215-030000.tar.gz
```

### `lib-sync-status` - Detailed Sync Status
```bash
lib-sync-status
# Shows: books needing sync, total size, recent history, TG connection
```

### `lib-clean` - Deep Cleanup
```bash
# Dry run first
DRY_RUN=true lib-clean

# Actual cleanup
lib-clean
```

---

## 🔧 Troubleshooting

### Common Issues

**`library-manager: command not found`**
```bash
pip install -e /mnt/Storage/library/.library-manager
# Or add to PATH
export PATH="/home/hardik-sankhla/.local/bin:$PATH"
```

**`Telegram connection failed`**
- Verify API credentials in `~/.config/library-manager/config.yaml`
- Ensure channel ID is negative (e.g., `-1001234567890`)
- Check channel is private and you're admin
- Try: `library-manager init` to re-authenticate

**`File too large for Telegram`**
- Telegram limit: 2GB per file
- Configure in config: `sync.max_file_size_mb: 1900`
- Large files are skipped automatically

**`Permission denied creating symlink`**
```bash
sudo ln -s /mnt/Storage/library /library
```

**`Database locked`**
- Ensure only one `library-manager` process runs at a time
- Check for stuck processes: `ps aux | grep library-manager`

**`Module not found` errors**
```bash
pip install telethon pyrogram pymupdf ebooklib python-magic Pillow PyYAML tqdm rich click watchdog xxhash
```

### Debug Mode
```bash
# Verbose output
library-manager --help
PYTHONPATH=/mnt/Storage/library/.library-manager/src python -m library_manager.cli.main --help
```

### Logs
- Sync logs: `/var/log/library-manager-sync.log`
- Inbox logs: `/var/log/library-manager-inbox.log`
- Verify logs: `/var/log/library-manager-verify.log`

---

## 📦 Backup & Recovery

### What's Backed Up
- `catalog.db` - SQLite database with all book records
- `config.yaml` - Configuration (including Telegram credentials)
- `.library-manager/` source code (excluding database)

### What's NOT Backed Up (Excluded)
- `books/` - Actual book files (3.4 GB+)
- `_inbox/`, `_duplicates/`, `_metadata/` - Working directories
- PDF/EPUB files in root

### Recovery Process
```bash
# 1. Restore backup
lib-restore library-backup-20241215-030000.tar.gz

# 2. Verify
lib doctor

# 3. Re-download books from Telegram if needed
lib pull
```

---

## 🔒 Security Notes

- **Never commit** `config.yaml` with real credentials to git
- **Never commit** `catalog.db` (contains personal file paths)
- **Never commit** `books/` or any PDF/EPUB files
- Telegram session files (`.session`) are excluded by `.gitignore`
- Use `.env` file for secrets if preferred

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests: `pytest` (when available)
5. Submit PR

---

## 📞 Support

- **Issues**: GitHub Issues
- **Author**: Hardik Sankhla
- **Email**: datascientist.hardiksankhla@gmail.com