#!/bin/bash
# Library Manager Auto-Sync Script
# Runs daily sync to Telegram

export PATH="/home/hardik-sankhla/.local/bin:/usr/local/bin:/usr/bin:$PATH"
cd /mnt/Storage/library

LOG_DIR="$HOME/.local/share/library-manager/logs"
mkdir -p "$LOG_DIR"

# Run sync push
library-manager sync --push >> "$LOG_DIR/sync.log" 2>&1

# Run verification weekly on Sundays
if [ "$(date +%u)" -eq 7 ]; then
    library-manager verify >> "$LOG_DIR/verify.log" 2>&1
fi