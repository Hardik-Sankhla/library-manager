# Library Manager

A personal offline library management system with Telegram cloud backup. Organize, rename, deduplicate, and sync your book collection with unlimited free cloud storage via a private Telegram channel.

## 🎯 Features

- 📚 **Organize** - Automatically sort books into category/author/series folders
- ✏️ **Rename** - Clean up messy filenames (removes Z-Library, OceanofPDF, copy numbers, etc.)
- 🔄 **Deduplicate** - Find and isolate duplicate files by content hash (SHA256)
- 📋 **Metadata** - Extract title, author, year, ISBN, series info from PDFs/EPUBs
- ☁️ **Telegram Backup** - Unlimited free cloud storage via private channel (2GB/file limit)
- 🔍 **Search** - Fast SQLite-powered search by title, author, category, tags
- 📊 **Statistics** - Library overview with category breakdown
- 👀 **Watch** - Auto-organize new files dropped in inbox
- ✅ **Verify** - Check file integrity and catalog consistency

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/hardik-sankhla/library-manager.git
cd library-manager

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install package
pip install -e .

# 4. Configure (interactive)
library-manager init

# 5. Add books to inbox
cp ~/Downloads/*.pdf _inbox/

# 6. Organize
library-manager organize

# 7. Sync to cloud
library-manager sync push
```

## 📖 Documentation

- [Complete Documentation](docs/README.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Telegram Setup](docs/TELEGRAM_SETUP.md)
- [Automation & Cron](docs/AUTOMATION.md)
- [Scripts Reference](docs/SCRIPTS.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🛠 Requirements

- Python 3.10+
- Telegram API credentials (free from [my.telegram.org](https://my.telegram.org))
- Private Telegram channel

### Python Dependencies

```
telethon>=1.45.0
pyrogram>=2.0.106
pymupdf>=1.28.2
ebooklib>=0.20
python-magic>=0.4.27
Pillow>=11.0.0
PyYAML>=6.0
tqdm>=4.70.0
rich>=13.0.0
click>=8.1.0
watchdog>=6.0.0
xxhash>=3.4.0
```

Install: `pip install -r requirements.txt`

## 📁 Project Structure

```
library-manager/
├── .library-manager/           # Source code & config
│   ├── src/library_manager/    # Main package
│   ├── setup.py                # Package setup
│   ├── auto_sync.sh            # Daily sync script
│   └── crontab.txt             # Cron job definitions
├── scripts/                    # Wrapper scripts
│   ├── lib                     # Main unified CLI
│   ├── lib-backup              # Backup catalog/config
│   ├── lib-restore             # Restore from backup
│   ├── lib-sync-status         # Detailed sync status
│   └── lib-clean               # Cleanup utility
├── docs/                       # Documentation
├── books/                      # Organized library (gitignored)
├── _inbox/                     # Drop new files here (gitignored)
├── _duplicates/                # Isolated duplicates (gitignored)
├── _metadata/                  # Extracted metadata (gitignored)
└── .gitignore                  # Excludes all data directories
```

## 📱 Telegram Setup

1. Get API credentials from https://my.telegram.org
2. Create a **Private Channel** (not group)
3. Add yourself as admin
4. Get channel ID: forward message from channel to @userinfobot
5. Run `library-manager init` and enter credentials

## 🤖 Automation

```bash
# Install cron jobs (daily sync, hourly inbox, weekly verify)
lib cron-install

# Or manually
crontab .library-manager/crontab.txt
```

## 📜 Scripts

| Script | Purpose |
|--------|---------|
| `lib` | Unified CLI wrapper (add, organize, search, sync, etc.) |
| `lib-backup` | Backup catalog.db and config (excludes books) |
| `lib-restore` | Restore from backup |
| `lib-sync-status` | Detailed sync status with progress |
| `lib-clean` | Deep cleanup utility |

## 📊 Example Usage

```bash
# Add books to inbox
lib add ~/Downloads/book.pdf

# Full organize + rename
lib organize

# Search library
lib search "machine learning"

# Show book details
lib info 42

# Library statistics
lib stats

# Sync to Telegram
lib sync

# Check sync status
lib status

# Health check
lib doctor
```

## 🔒 What's in Git (vs Excluded)

| Included | Excluded (.gitignore) |
|----------|----------------------|
| Source code | `books/` (3.4 GB+) |
| Wrapper scripts | `_inbox/`, `_duplicates/`, `_metadata/` |
| Documentation | `catalog.db` |
| Config templates | `*.pdf`, `*.epub`, etc. |
| `.gitignore` | `.session` files |

## 📄 License

MIT License

## 👤 Author

**Hardik Sankhla**
- BTech CSE (Data Science) - JIET Institute of Design and Technology
- Email: datascientist.hardiksankhla@gmail.com
- GitHub: @hardik-sankhla

---

*Built with ❤️ for personal library management*