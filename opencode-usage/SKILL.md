---
name: opencode-usage
description: Monitor and report OpenCode usage, quota, and local resource consumption. Reads the local opencode.db (read-only) to produce session/token/model statistics, disk usage, OpenCode process CPU/RAM, and free-tier quota estimates; probes provider credit APIs (OpenRouter, Agnes) with silent fallback; generates an HTML dashboard. Use when asked "OpenCode 用量", "用了多少 token", "剩餘額度", "quota", "oc-usage", "用量儀表板", "opencode 佔用多少磁碟/記憶體", "rate limit", or to check / refresh the OpenCode usage dashboard.
license: MIT
---

# OpenCode Usage Monitor

Full documentation, metric definitions, and rationale: **[README.md](README.md)**
(資料來源、欄位定義、門檻訂定依據、花費模型、Telegram 設定、教學筆記)

Read-only observability for the local OpenCode installation. Never writes to
`opencode.db`, `auth.json`, or any OpenCode config.

## Data sources

| Source | What it gives |
|---|---|
| `~/.local/share/opencode/opencode.db` (opened `mode=ro`) | `session` (cost, tokens_*, model, time_*), `message` (per-request tokens, cost, providerID/modelID) |
| `~/.local/share/opencode/log/opencode.log` | `stream error` / 429 / rate-limit events |
| `~/.local/share/opencode/auth.json` | provider keys, used only for credit API probes |
| `Get-Process OpenCode` | CPU / working set of the desktop app |
| Disk scan of `~/.local/share/opencode/*` | db, log, snapshot, tool-output sizes |

`event` table (172k rows, large `data` column) is **never** scanned.

## Output directory

`%USERPROFILE%/.local/share/opencode-usage/`

- `snapshot.json` — latest metrics
- `history.jsonl` — one line per run, appended (for trend/history)
- `dashboard.html` — self-contained dashboard, data injected at generation
- `dashboard-latest.html` — convenience copy at the skill root

## Usage

```powershell
# Generate snapshot + refresh dashboard (default)
python "$env:USERPROFILE\.config\opencode\skills\opencode-usage\collect.py"

# CLI report to terminal
python ...\collect.py --report

# Cleanup: survey (read-only) / safe / db / purge
python ...\cleanup.py survey
python ...\cleanup.py safe --apply
python ...\cleanup.py purge --days 30            # refuses without --yes PURGE
```

Exit code `0` always, unless the database is unreadable (`2`).

## Free-tier limit (important)

The anonymous Zen free tier allows **200 requests per day** (HTTP 429,
`FreeUsageLimitError`), **not** 200 per 5 hours. The 5-hour window belongs to the
paid **OpenCode Go** subscription and is denominated in **dollars** ($12 / 5h,
$30 / week, $60 / month). See README section 4.3 for the evidence.

## Maintenance buttons

The dashboard's Maintenance panel triggers `cleanup.py` through the
`ocusage://` URL protocol, so no resident web server is needed:

```powershell
powershell -ExecutionPolicy Bypass -File ...\register_protocol.ps1
```

`ocusage://safe` and `ocusage://db` are non-destructive. Session purging is
deliberately **not** a button: it needs the typed `--yes PURGE` token in a
terminal because it permanently removes conversation history.

## Scheduled refresh

`install_task.ps1` registers a Windows Scheduled Task that runs every 10 minutes
and rebuilds `dashboard.html` with zero resident memory.

```powershell
powershell -ExecutionPolicy Bypass -File ...\install_task.ps1
```

## Interpreting the numbers

- **Cost is `0` for every free model** (`big-pickle`, `space-bunny-free`,
  `mimo-v2.5-free`, `openrouter/free`, `agnes-*` when free tier). `cost_est`
  is an estimate from models.dev list prices, only meaningful once a paid model
  is used.
- **Free-tier quota is not exposed by an API** for OpenCode Zen, so
  `quota.requests_today` is compared against the published daily free cap and
  `quota.blocked_events` counts 429s seen in the log.
- `credits` is `null` whenever a provider API is unreachable (401, proxy, no
  key). This is expected and degrades silently — never treat it as an error.

## Alerting

`alert.py` evaluates thresholds from the latest snapshot and fires a Windows
toast (`New-BurntToastNotification` or a `msg.exe` popup fallback) and/or POSTs
JSON to the `OPENCODE_ALERT_WEBHOOK` environment variable (n8n), and a
Telegram message.

Triggers: db above `db_warn_mb` / `db_crit_mb`, free quota at 80% (warn) or 95%
(crit), any 429 `FreeUsageLimitError` (crit), no session activity for
`idle_warn_min`, or estimated cost above `cost_warn_usd`.

Deduplicated on `level:title`, so changing numbers never re-notifies but a level
change does.

### Telegram: token stays on this machine

The bot token is **never** written to a config file, the snapshot, the
dashboard, a log, or git. It is stored DPAPI-encrypted (Windows user scope) in
`~/.local/share/opencode-usage/telegram.enc` with an ACL restricted to the
current user, and decrypted in memory by `alert.py` only when a message is
actually sent.

```powershell
powershell -ExecutionPolicy Bypass -File ...\set_telegram.ps1            # masked input
powershell -ExecutionPolicy Bypass -File ...\set_telegram.ps1 -Status
powershell -ExecutionPolicy Bypass -File ...\set_telegram.ps1 -Disable
python ...\alert.py --test-telegram
```

Do not ask the user to paste the token into a chat: that would send it to the
model provider. Always have them run `set_telegram.ps1` themselves.

`collect.py` runs every 10 minutes and injects `snapshot.json` into
`dashboard.html`, so `sanitize_config()` strips `telegram`, `webhook` and any
`*token*` / `*key*` key from the config that reaches the browser. Keep it that
way if you add new settings.

