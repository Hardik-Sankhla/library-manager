# Configuration Guide

## Configuration File Location

`~/.config/library-manager/config.yaml`

## Complete Configuration Reference

```yaml
# Library root directory (where books are stored)
library_root: "/mnt/Storage/library"

# Symlink path for easy access (requires sudo)
symlink_path: "/library"

# Telegram Configuration
telegram:
  # Get from https://my.telegram.org
  api_id: 123456
  api_hash: "your_api_hash_here"
  
  # Channel ID (negative number for channels)
  # Get by forwarding message to @userinfobot
  channel_id: -1001234567890
  
  # Session name for Telegram client
  session_name: "library_bot"
  
  # Use bot token instead of user session (optional)
  use_bot_token: false
  bot_token: null

# Organization Rules
organization:
  # Organize by category (AI/ML/LLM, Programming, etc.)
  by_category: true
  
  # Organize by author name
  by_author: true
  
  # Create series subfolders
  create_series_folders: true
  
  # Maximum directory depth
  max_depth: 3

# File Naming Patterns
naming:
  # Standard book pattern
  pattern: "{author} - {title} ({year}){ext}"
  
  # Series book pattern
  series_pattern: "{author} - {series} {series_num:02d} - {title} ({year}){ext}"
  
  # Regex patterns to remove from filenames
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

# Auto-categorization Keywords
categories:
  AI/ML/LLM:
    - "ai"
    - "machine learning"
    - "deep learning"
    - "llm"
    - "language model"
    - "neural network"
    - "transformer"
    - "generative ai"
    - "agentic"
    - "rag"
    - "mlops"
    - "pytorch"
    - "tensorflow"
  Programming:
    - "programming"
    - "software"
    - "clean code"
    - "refactoring"
    - "design pattern"
    - "architecture"
    - "algorithm"
    - "data structure"
    - "compiler"
    - "interpreter"
    - "debugging"
    - "testing"
    - "tdd"
  Data Science:
    - "data science"
    - "data analysis"
    - "pandas"
    - "numpy"
    - "visualization"
    - "statistics"
    - "statistical learning"
    - "data engineering"
    - "etl"
    - "pipeline"
  Math/Stats:
    - "mathematics"
    - "calculus"
    - "linear algebra"
    - "probability"
    - "statistics"
    - "mathematical"
    - "proof"
    - "theorem"
  Web Development:
    - "web"
    - "frontend"
    - "backend"
    - "react"
    - "vue"
    - "angular"
    - "node"
    - "django"
    - "flask"
    - "fastapi"
    - "api"
    - "rest"
    - "graphql"
    - "javascript"
    - "typescript"
    - "css"
    - "html"
  Systems:
    - "operating system"
    - "linux"
    - "kernel"
    - "distributed"
    - "concurrency"
    - "parallel"
    - "network"
    - "protocol"
    - "tcp"
    - "http"
    - "grpc"
    - "microservice"
    - "kubernetes"
    - "docker"
    - "container"
  Security:
    - "security"
    - "cryptography"
    - "encryption"
    - "hacking"
    - "penetration"
    - "vulnerability"
    - "auth"
    - "oauth"
    - "jwt"
    - "ssl"
    - "tls"
  Cloud:
    - "cloud"
    - "aws"
    - "azure"
    - "gcp"
    - "serverless"
    - "lambda"
    - "terraform"
    - "infrastructure"
    - "devops"
    - "ci/cd"
  Science:
    - "physics"
    - "chemistry"
    - "biology"
    - "neuroscience"
    - "cognitive"
    - "quantum"
    - "relativity"
  Psychology:
    - "psychology"
    - "behavioral"
    - "cognitive"
    - "therapy"
    - "cbt"
    - "mindfulness"
    - "mental health"
    - "personality"
  Philosophy:
    - "philosophy"
    - "ethics"
    - "logic"
    - "epistemology"
    - "metaphysics"
    - "stoicism"
    - "existentialism"
  Fiction:
    - "novel"
    - "fiction"
    - "fantasy"
    - "sci-fi"
    - "science fiction"
    - "mystery"
    - "thriller"
    - "romance"
    - "shadow slave"
  Business:
    - "business"
    - "entrepreneur"
    - "startup"
    - "management"
    - "leadership"
    - "strategy"
    - "marketing"
    - "finance"
    - "economics"
    - "lean startup"
  Self-Help:
    - "self-help"
    - "habit"
    - "productivity"
    - "motivation"
    - "mindset"
    - "atomic habits"
    - "deep work"
    - "essentialism"
    - "influence"
    - "persuasion"
  Biography:
    - "biography"
    - "autobiography"
    - "memoir"
    - "life of"
    - "story of"
  Reference:
    - "reference"
    - "handbook"
    - "guide"
    - "manual"
    - "encyclopedia"
    - "dictionary"
    - "companion"

# Sync Configuration
sync:
  # Auto-sync on file changes (requires watchdog)
  auto_sync: false
  
  # Sync interval in hours (for cron)
  sync_interval_hours: 24
  
  # Maximum file size for Telegram upload (MB)
  # Telegram limit is 2GB (2048 MB)
  max_file_size_mb: 1900
  
  # Parallel uploads
  parallel_uploads: 3
  
  # Verify checksums after upload
  verify_checksums: true

# Database Configuration
database:
  # Custom database path (null = auto)
  path: null
```

## Environment Variables

You can override config with environment variables:

```bash
export LIBRARY_ROOT="/mnt/Storage/library"
export TELEGRAM_API_ID="123456"
export TELEGRAM_API_HASH="your_hash"
export TELEGRAM_CHANNEL_ID="-1001234567890"
```

## Adding Custom Categories

Edit the `categories` section in config.yaml. Each category has a list of keywords. Books are matched against keywords in title, author, description, and filename.

```yaml
categories:
  MyCategory:
    - "keyword1"
    - "keyword2"
```

## Custom Naming Patterns

Available placeholders:
- `{author}` - Primary author
- `{title}` - Book title
- `{year}` - Publication year
- `{series}` - Series name
- `{series_num}` - Series number (zero-padded)
- `{ext}` - File extension (including dot)

## Sync Configuration Tips

- **Large files**: If you have files > 2GB, they'll be skipped. Increase `max_file_size_mb` up to 2000.
- **Slow uploads**: Reduce `parallel_uploads` if you hit rate limits.
- **Unreliable network**: Enable `verify_checksums` for integrity verification.

## Database Location

By default: `{library_root}/.library-manager/catalog.db`

Custom location:
```yaml
database:
  path: "/custom/path/catalog.db"
```