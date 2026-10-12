# Telegram Setup Guide

## Prerequisites

- Telegram account
- Phone number for verification
- Ability to create channels

## Step 1: Get API Credentials

1. Open https://my.telegram.org in browser
2. Log in with your phone number (enter code sent via Telegram)
3. Click "API development tools"
4. Create new application:
   - **App title**: Library Manager (or any name)
   - **Short name**: library-manager
   - **Platform**: Desktop
   - **Description**: Personal library backup bot
5. Save the **api_id** and **api_hash**

## Step 2: Create Private Channel

### Option A: User Account (Recommended)

1. Open Telegram Desktop or Mobile
2. Create New Channel:
   - Name: "Library Backup" (or any name)
   - Type: **Private Channel** (NOT a group!)
   - Description: Optional
3. Add yourself as admin (you're creator by default)
4. **Important**: Do NOT add any other members

### Option B: Bot Account (Alternative)

1. Message @BotFather in Telegram
2. `/newbot` → follow prompts
3. Save the **bot token**
4. Create private channel
5. Add bot as admin to channel

## Step 3: Get Channel ID

1. Post any message in your channel (e.g., "test")
2. Forward that message to @userinfobot
3. Bot replies with channel info:
   ```
   Chat ID: -1001234567890
   ```
4. Copy the **negative number** (including the minus sign)

## Step 4: Configure Library Manager

### Interactive Setup
```bash
library-manager init
```
Follow prompts for:
- Library root path
- API ID
- API Hash
- Channel ID
- Bot token (optional)

### Non-Interactive Setup
```bash
library-manager init --non-interactive \
  --api-id 123456 \
  --api-hash "your_api_hash" \
  --channel-id -1001234567890
```

### With Bot Token
```bash
library-manager init --non-interactive \
  --api-id 123456 \
  --api-hash "your_api_hash" \
  --channel-id -1001234567890 \
  --bot-token "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

## Step 5: Test Connection

```bash
# Test sync (dry run first)
library-manager --dry-run sync push

# Actual sync
library-manager sync push

# Check status
library-manager sync status
```

## Troubleshooting

### "Telegram session not authorized"
- Run `library-manager init` again
- Enter phone number when prompted
- Enter code sent to Telegram app
- Enter 2FA password if enabled

### "Cannot access channel"
- Verify channel ID is correct (negative number)
- Ensure channel is **private** (not public)
- Ensure you're admin of the channel
- If using bot: ensure bot is admin

### "Rate limited, wait X seconds"
- Telegram limits: ~30 messages/second, 20 files/minute
- Reduce `parallel_uploads` in config
- Wait and retry

### "File too large"
- Telegram limit: 2GB per file
- Files larger than `max_file_size_mb` (default 1900) are skipped
- Compress or split large PDFs

## Security Notes

- **Never share** your `api_hash` or `bot_token`
- **Never commit** config.yaml with real credentials to git
- Channel should be **private** - only you (and bot) should have access
- Session file (`library_bot.session`) contains auth - keep secure

## Channel Structure

Each uploaded book appears as a message with:

```
📖 **Book Title**
✍️ Author Name
📅 2023
🔢 ISBN: 978-1234567890
📚 Series Name #1
🏷️ AI/ML/LLM, Programming
📄 450 pages
🌐 English

📝 Description preview...

🔖 Library ID: 42
📁 books/AI_ML_LLM/Author Name/Author Name - Book Title (2023).pdf
```

## Downloading from Telegram

```bash
# Download all missing files
library-manager sync pull

# Or download specific book by message ID
# (requires custom script)
```

## Multiple Channels

Currently only one channel supported. For multiple backups, run separate instances with different config files:

```bash
library-manager --config /path/to/config2.yaml sync push
```