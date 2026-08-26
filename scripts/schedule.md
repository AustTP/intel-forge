# Scheduling the refresh

`scripts/refresh.sh` is a plain script; schedule it however your OS prefers.
Pick one of the following. Weekly is a sane default; tune to how fast your
domain moves.

## cron (Linux / macOS)

```cron
# Every Monday at 07:00: edit `crontab -e`
0 7 * * 1  /bin/bash /path/to/intel-forge/scripts/refresh.sh
```

## systemd timer (Linux)

`/etc/systemd/system/intel-refresh.service`:

```ini
[Service]
Type=oneshot
ExecStart=/bin/bash /path/to/intel-forge/scripts/refresh.sh
```

`/etc/systemd/system/intel-refresh.timer`:

```ini
[Timer]
OnCalendar=Mon 07:00
Persistent=true

[Install]
WantedBy=timers.target
```

Then: `systemctl enable --now intel-refresh.timer`

## launchd (macOS)

`~/Library/LaunchAgents/com.you.intel-refresh.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.you.intel-refresh</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/path/to/intel-forge/scripts/refresh.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer></dict>
</dict>
</plist>
```

Then: `launchctl load ~/Library/LaunchAgents/com.you.intel-refresh.plist`

## Environment / secrets

`refresh.sh` sources a `.env` file at the repo root if present (gitignored).
Put API tokens there:

```
EXAMPLE_API_TOKEN=...
ANTHROPIC_API_KEY=...        # only if you use the reference triage judge
```

Knobs (all optional, set in the environment or `.env`):

- `LOOKBACK`: days to look back each run (default 10)
- `FRESHNESS_DAYS`: staleness threshold for skills (default 180)
- `PYTHON`: python interpreter to use
