# Automation & Cron Jobs

## Recommended Cron Jobs

The library-manager includes a pre-configured crontab at `.library-manager/crontab.txt`:

```bash
# Daily sync at 3 AM
0 3 * * * /mnt/Storage/library/.library-manager/auto_sync.sh

# Hourly inbox processing
0 * * * * /usr/bin/library-manager watch --once >> /var/log/library-manager-inbox.log 2>&1

# Weekly verification on Sunday at 4 AM
0 4 * * 0 /usr/bin/library-manager verify >> /var/log/library-manager-verify.log 2>&1
```

## Installing Cron Jobs

### Using the wrapper script
```bash
lib cron-install
```

### Manually
```bash
crontab /mnt/Storage/library/.library-manager/crontab.txt
```

### View Current Jobs
```bash
lib cron-list
# or
crontab -l
```

### Remove Jobs
```bash
lib cron-remove
# or manually edit crontab
crontab -e
```

## Cron Job Details

### Daily Sync (3 AM)
**Script**: `/mnt/Storage/library/.library-manager/auto_sync.sh`

Runs:
1. `library-manager sync push` - Upload new/changed files
2. Weekly (Sundays): `library-manager verify` - Check integrity

**Log**: `/var/log/library-manager-sync.log`

### Hourly Inbox Processing
**Command**: `library-manager watch --once`

Processes any new files in `_inbox/` directory once per hour.

**Log**: `/var/log/library-manager-inbox.log`

### Weekly Verification (Sunday 4 AM)
**Command**: `library-manager verify`

Checks all cataloged files exist and match expected sizes.

**Log**: `/var/log/library-manager-verify.log`

## Customizing Cron Schedule

Edit `/mnt/Storage/library/.library-manager/crontab.txt`:

```bash
# Different sync time (e.g., 2 AM)
0 2 * * * /mnt/Storage/library/.library-manager/auto_sync.sh

# More frequent inbox (every 30 minutes)
*/30 * * * * /usr/bin/library-manager watch --once >> /var/log/library-manager-inbox.log 2>&1

# Verification on Saturday instead
0 4 * * 6 /usr/bin/library-manager verify >> /var/log/library-manager-verify.log 2>&1
```

Then reinstall:
```bash
lib cron-install
```

## Systemd Alternative

For more robust scheduling, use systemd timers:

### Sync Service
`/etc/systemd/system/library-manager-sync.service`:
```ini
[Unit]
Description=Library Manager Daily Sync
After=network.target

[Service]
Type=oneshot
User=hardik-sankhla
Environment=PATH=/usr/local/bin:/usr/bin
WorkingDirectory=/mnt/Storage/library
ExecStart=/usr/bin/library-manager sync push
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Sync Timer
`/etc/systemd/system/library-manager-sync.timer`:
```ini
[Unit]
Description=Daily Library Manager Sync

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
```

### Inbox Service
`/etc/systemd/system/library-manager-inbox.service`:
```ini
[Unit]
Description=Library Manager Inbox Processor
After=network.target

[Service]
Type=oneshot
User=hardik-sankhla
Environment=PATH=/usr/local/bin:/usr/bin
WorkingDirectory=/mnt/Storage/library
ExecStart=/usr/bin/library-manager watch --once
StandardOutput=journal
StandardError=journal
```

### Inbox Timer (Hourly)
`/etc/systemd/system/library-manager-inbox.timer`:
```ini
[Unit]
Description=Hourly Library Manager Inbox Processing

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable Systemd Timers
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now library-manager-sync.timer
sudo systemctl enable --now library-manager-inbox.timer
```

### Check Status
```bash
systemctl list-timers | grep library-manager
journalctl -u library-manager-sync -f
```

## Log Rotation

Configure logrotate for library-manager logs:

`/etc/logrotate.d/library-manager`:
```
/var/log/library-manager-*.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644 hardik-sankhla hardik-sankhla
}
```

## Monitoring

### Check Sync Health
```bash
# Last sync time
grep "Sync complete" /var/log/library-manager-sync.log | tail -1

# Failed uploads
grep "Failed" /var/log/library-manager-sync.log | tail -5

# Inbox processing
grep "Organized" /var/log/library-manager-inbox.log | tail -5
```

### Health Check Script
```bash
#!/bin/bash
# save as /usr/local/bin/lib-health-check

echo "=== Library Manager Health Check ==="
echo "Date: $(date)"
echo ""

# Check cron
echo "Cron jobs:"
crontab -l | grep -E "library-manager|auto_sync" || echo "  NONE FOUND"
echo ""

# Check last sync
echo "Last sync:"
grep "Sync complete" /var/log/library-manager-sync.log 2>/dev/null | tail -1 || echo "  No sync log found"
echo ""

# Check inbox
INBOX_COUNT=$(find /mnt/Storage/library/_inbox -type f \( -name "*.pdf" -o -name "*.epub" \) 2>/dev/null | wc -l)
echo "Inbox files pending: $INBOX_COUNT"
echo ""

# Check disk space
echo "Disk usage:"
df -h /mnt/Storage | tail -1
echo ""

# Library stats
echo "Library stats:"
library-manager stats 2>/dev/null | head -10
```

Add to crontab for daily health report:
```bash
0 8 * * * /usr/local/bin/lib-health-check | mail -s "Library Manager Health" user@example.com
```

## Environment Variables for Cron

Cron runs with minimal environment. Ensure PATH includes library-manager:

```bash
# In crontab:
PATH=/usr/local/bin:/usr/bin:/bin
0 3 * * * /mnt/Storage/library/.library-manager/auto_sync.sh
```

Or use full paths:
```bash
0 3 * * * /usr/bin/library-manager sync push
```

## Testing Cron Jobs

```bash
# Test daily sync script
/mnt/Storage/library/.library-manager/auto_sync.sh

# Test inbox processing
library-manager watch --once

# Test verification
library-manager verify
```

All should run without errors before installing to cron.