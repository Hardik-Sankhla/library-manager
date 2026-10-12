# Library Manager

Personal offline library with Telegram cloud backup. Organize, rename, deduplicate, and sync your book collection with unlimited free cloud storage via a private Telegram channel.

## Features

- 📚 **Organize** - Automatically sort books into category/author/series folders
- ✏️ **Rename** - Clean up messy filenames (removes Z-Library, OceanofPDF, copy numbers, etc.)
- 🔄 **Deduplicate** - Find and isolate duplicate files by content hash
- 📋 **Metadata** - Extract title, author, year, ISBN, series info from PDFs/EPUBs
- ☁️ **Telegram Backup** - Unlimited free cloud storage via private channel (2GB/file limit)
- 🔍 **Search** - Fast SQLite-powered search by title, author, category, tags
- 📊 **Statistics** - Library overview with category breakdown
- 👀 **Watch** - Auto-organize new files dropped in inbox
- ✅ **Verify** - Check file integrity and catalog consistency

## Installation

```bash
# Install dependencies
pip install telethon pyrogram pymupdf ebooklib python-magic Pillow PyYAML tqdm rich click watchdog xxhash

# Install library-manager in development mode
cd /mnt/Storage/library/.library-manager
pip install -e .
```

## Quick Start

```bash
# 1. Initialize configuration
library-manager init

# 2. Organize existing library
library-manager organize

# 3. Rename files to clean format
library-manager rename

# 4. Find duplicates
library-manager dedupe

# 5. Extract metadata
library-manager metadata

# 6. Sync to Telegram
library-manager sync push
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Interactive setup (Telegram API, library path) |
| `organize` | Move files into structured folders |
| `rename` | Clean up filenames (run after organize) |
| `dedupe` | Find and move duplicate files |
| `metadata` | Extract/update book metadata |
| `sync push` | Upload new/changed files to Telegram |
| `sync pull` | Download missing files from Telegram |
| `sync status` | Show sync status |
| `search "query"` | Search catalog |
| `info <id|path|hash>` | Show book details |
| `stats` | Library statistics |
| `verify` | Check file integrity |
| `watch` | Auto-organize inbox (daemon) |
| `clean` | Remove empty dirs, temp files |
| `config` | Show current configuration |

## Telegram Setup

1. Get API credentials from https://my.telegram.org
2. Create a **private channel** (not group)
3. Add yourself as admin
4. Get channel ID: forward a message from channel to @userinfobot
5. Run `library-manager init` and enter credentials

## Library Structure

```
/mnt/Storage/library/
├── books/                    # Organized library
│   ├── AI_ML_LLM/
│   │   ├── Author Name/
│   │   │   ├── Author Name - Book Title (2023).pdf
│   │   │   └── Series Name/
│   │   │       ├── Author Name - Series Name 01 - Book One (2022).pdf
│   │   │       └── Author Name - Series Name 02 - Book Two (2023).pdf
│   ├── Programming/
│   │   └── ...
│   └── Fiction/
│       └── ...
├── _inbox/                   # Drop new files here
├── _duplicates/              # Isolated duplicates
├── _metadata/                # Extracted metadata JSON
├── catalog.db                # SQLite catalog
└── .library-manager/         # Config, logs, source code
```

## File Naming Convention

```
Author - Title (Year).ext
Author - Series 01 - Title (Year).ext
```

Automatically removes:
- `(Z-Library)`, `_OceanofPDF.com_`, `[libribook.com]`
- `- Copy`, `- Copy (1)`, `(PDFDrive)`, `(z-lib.org)`
- Leading numbers, extra spaces, special characters

## Configuration

Config file: `~/.config/library-manager/config.yaml`

```yaml
library_root: "/mnt/Storage/library"
symlink_path: "/library"
telegram:
  api_id: 123456
  api_hash: "your_api_hash"
  channel_id: -1001234567890
  session_name: "library_bot"
organization:
  by_category: true
  by_author: true
  create_series_folders: true
sync:
  max_file_size_mb: 1900
  parallel_uploads: 3
```

## Cron Jobs

```bash
# Daily sync at 3 AM
0 3 * * * /usr/local/bin/library-manager sync push

# Hourly inbox processing
0 * * * * /usr/local/bin/library-manager watch --once

# Weekly verification
0 4 * * 0 /usr/local/bin/library-manager verify
```

## Requirements

- Python 3.10+
- Telegram API credentials (free from my.telegram.org)
- Private Telegram channel

## License

MIT License