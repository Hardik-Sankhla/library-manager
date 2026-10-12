# Scripts Reference

All scripts are located in `/mnt/Storage/library/scripts/` and should be added to PATH:

```bash
export PATH="/mnt/Storage/library/scripts:$PATH"
```

## Core Scripts

### `lib` - Main Unified CLI

**Purpose**: Simplified wrapper for all library-manager operations

**Usage**:
```bash
lib <command> [options]
```

**Commands**:

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Interactive setup | `lib init` |
| `config` | Show configuration | `lib config` |
| `doctor` | Health check | `lib doctor` |
| `add <path>` | Add file/dir to inbox | `lib add ~/Downloads/book.pdf` |
| `organize` | Full organize + rename | `lib organize` |
| `inbox` | Process inbox only | `lib inbox` |
| `dedupe` | Find duplicates | `lib dedupe` |
| `meta` | Extract metadata | `lib meta` |
| `search "query"` | Search library | `lib search "python"` |
| `info <id>` | Book details | `lib info 42` |
| `stats` | Library statistics | `lib stats` |
| `sync` | Push to Telegram | `lib sync` |
| `pull` | Pull from Telegram | `lib pull` |
| `status` | Sync status | `lib status` |
| `tglist` | List TG channel files | `lib tglist` |
| `verify` | Verify integrity | `lib verify` |
| `clean` | Cleanup | `lib clean` |
| `watch` | Daemon mode | `lib watch` |
| `watch-once` | Process inbox once | `lib watch-once` |
| `cron-install` | Install cron jobs | `lib cron-install` |
| `cron-remove` | Remove cron jobs | `lib cron-remove` |
| `cron-list` | List cron jobs | `lib cron-list` |
| `help` | Show help | `lib help` |
| `version` | Show version | `lib version` |

**Global Options**:
- `DRY_RUN=true lib organize` - Preview changes

---

### `lib-backup` - Backup Catalog & Config

**Purpose**: Create timestamped backup of catalog database and configuration (excludes actual book files)

**Usage**:
```bash
lib-backup
```

**Output**: `~/library-backups/library-backup-YYYYMMDD-HHMMSS.tar.gz`

**Includes**:
- `catalog.db` - SQLite database
- `config.yaml` - Configuration
- `.library-manager/` source code (excluding database)

**Excludes**:
- `books/` directory
- `_inbox/`, `_duplicates/`, `_metadata/`
- All PDF/EPUB files

**Retention**: Keeps last 10 backups automatically

---

### `lib-restore` - Restore from Backup

**Purpose**: Restore catalog and configuration from backup

**Usage**:
```bash
# List available backups
ls ~/library-backups/

# Restore specific backup
lib-restore library-backup-20241215-030000.tar.gz
```

**Restores**:
- `catalog.db`
- `config.yaml`
- `.library-manager/` source code
- Reinstalls package via `pip install -e .`

---

### `lib-sync-status` - Detailed Sync Status

**Purpose**: Show comprehensive sync status with progress details

**Usage**:
```bash
lib-sync-status
```

**Output**:
- Overall library statistics
- Books needing sync (with sizes)
- Recent sync history
- Telegram connection status
- Recent channel files

---

### `lib-clean` - Deep Cleanup

**Purpose**: Remove empty directories, temporary files, and orphaned metadata

**Usage**:
```bash
# Dry run (preview)
DRY_RUN=true lib-clean

# Actual cleanup
lib-clean
```

**Cleans**:
- Empty directories in `books/`
- `.crdownload` files (incomplete Chrome downloads)
- `.part` files (incomplete Firefox downloads)
- Orphaned metadata files (JSON files for books not in catalog)
- Python `__pycache__` and `.pyc` files

---

## Utility Scripts (Direct library-manager Commands)

These are thin wrappers around library-manager commands:

```bash
# Equivalent commands
lib organize          → library-manager organize
lib inbox             → library-manager organize --inbox-only
lib dedupe            → library-manager dedupe
lib meta              → library-manager metadata
lib search "query"    → library-manager search "query"
lib info 42           → library-manager info 42
lib stats             → library-manager stats
lib sync              → library-manager sync push
lib pull              → library-manager sync pull
lib status            → library-manager sync status
lib verify            → library-manager verify
lib clean             → library-manager clean
lib watch             → library-manager watch
lib watch-once        → library-manager watch --once
lib config            → library-manager config-cmd
```

---

## Installation

### Add to PATH (Permanent)
```bash
echo 'export PATH="/mnt/Storage/library/scripts:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Verify Installation
```bash
which lib
lib help
lib doctor
```

---

## Creating Custom Scripts

Example: `lib-recent` - Show recently added books

```bash
#!/usr/bin/env bash
# lib-recent - Show recently added books
# Save to /mnt/Storage/library/scripts/lib-recent

python3 << 'PYEOF'
from library_manager.core.database import get_db
from datetime import datetime, timedelta

db = get_db()
books = db.get_all_books(limit=10000)

# Sort by created_at descending
books.sort(key=lambda b: b.created_at, reverse=True)

print("📚 Recently Added Books")
print("=" * 50)

for book in books[:20]:
    created = book.created_at[:19].replace('T', ' ')
    size = book.size_bytes / 1024 / 1024
    print(f"  {book.title[:45]:45s} | {created} | {size:6.1f} MB")
    print(f"    {book.author[:40]}")
    print()
PYEOF
```

Make executable:
```bash
chmod +x /mnt/Storage/library/scripts/lib-recent
```

---

## Script Development Guidelines

1. **Shebang**: Use `#!/usr/bin/env bash` for bash scripts
2. **Error handling**: `set -euo pipefail`
3. **Colors**: Use consistent color scheme
4. **Help**: Support `--help` or `help` command
5. **Dry-run**: Respect `DRY_RUN` environment variable
6. **Logging**: Use `info`, `success`, `warn`, `error` functions

### Color Functions Template
```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*" >&2; }
header() { echo -e "\n${BOLD}${CYAN}$*${NC}\n"; }
```

---

## Troubleshooting Scripts

### Script Not Found
```bash
# Check PATH
echo $PATH
ls -la /mnt/Storage/library/scripts/

# Re-add to PATH
export PATH="/mnt/Storage/library/scripts:$PATH"
```

### Permission Denied
```bash
chmod +x /mnt/Storage/library/scripts/lib*
```

### Python Import Errors
```bash
# Ensure package is installed
pip install -e /mnt/Storage/library/.library-manager

# Or set PYTHONPATH
export PYTHONPATH="/mnt/Storage/library/.library-manager/src:$PYTHONPATH"
```