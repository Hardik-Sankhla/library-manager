#!/bin/bash
# Library Manager Auto-Sync Script
# Runs daily sync to Telegram

export PATH="/usr/bin:/usr/local/bin:$PATH"
cd /mnt/Storage/library

# Run sync push
/usr/bin/library-manager sync push >> /var/log/library-manager-sync.log 2>&1

# Run verification weekly on Sundays
if [ "$(date +%u)" -eq 7 ]; then
    /usr/bin/library-manager verify >> /var/log/library-manager-verify.log 2>&1
fi
