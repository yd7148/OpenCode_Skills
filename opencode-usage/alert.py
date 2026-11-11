"""Evaluate the latest OpenCode usage snapshot and fire alerts.

Usage:
    python alert.py                 # evaluate, notify
    python alert.py --dry-run       # print what would fire, notify nothing
    python alert.py --quiet-ok      # stay silent when there is nothing to report
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request

SNAPSHOT = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode-usage", "snapshot.json"
)
SECRET = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode-usage", "telegram.enc"
)
STATE = os.path.join(
    os.path.expanduser("~"), ".local", "share", "opencode-usage", "alert-state.json"
)


def load_telegram_secret() -> tuple[str, str, str]:
    """Decrypt the bot token locally with DPAPI.

    Returns (token, chat_id, source). The token is held in memory only and is
    never written to disk, logs, the snapshot, or the dashboard. The plaintext
    is produced by a PowerShell subprocess running as the same Windows user;
    if that fails, nothing is transmitted.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if token and chat:
        return token, chat, "env"
    if not os.path.exists(SECRET):
        return "", "", "none"
    try:
        import json as _json

        with open(SECRET, encoding="utf-8-sig") as fh:
            data = _json.load(fh)
        enc, chat = data.get("token", ""), data.get("chat_id", "")
        if not data.get("enabled") or not enc or not chat:
            return "", "", "disabled"
        enc = enc.replace("'", "")
        # NOTE: powershell -Command appends trailing arguments to the command
        # text instead of binding them to $args, so the blob is embedded in the
        # script itself. Base64 never contains a single quote.
        script = (
            "Add-Type -AssemblyName System.Security;"
            f"$b=[Convert]::FromBase64String('{enc}');"
            "$x=[Security.Cryptography.ProtectedData]::Unprotect($b,$null,"
            "[Security.Cryptography.DataProtectionScope]::CurrentUser);"
            "[Console]::Out.Write([Text.Encoding]::UTF8.GetString($x))"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        plain = out.stdout.strip()
        if not plain:
            return "", chat, "decrypt-failed"
        return plain, chat, "dpapi"
    except Exception:
        return "", "", "error"


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)


def fingerprint(alerts: list) -> list:
    return sorted(f"{a['level']}:{a['title']}" for a in alerts)


def toast(title: str, message: str) -> bool:
    """Windows notification: BurntToast if present, else a msg.exe popup."""
    try:
        if subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Module -ListAvailable BurntToast"],
            capture_output=True,
            timeout=15,
        ).returncode == 0:
            r = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "New-BurntToastNotification -Text $args[0] -Message $args[1]",
                    title,
                    message,
                ],
                capture_output=True,
                timeout=20,
            )
            return r.returncode == 0
    except Exception:
        pass
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "[reflection.assembly]::loadwithpartialname('System.Windows.Forms');"
                "$n=New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon=[System.Drawing.SystemIcons]::Information;$n.Visible=$true;"
                f"$n.ShowBalloonTip(8000,'OpenCode Usage','{message[:200]}',"
                "[System.Windows.Forms.ToolTipIcon]::Info);Start-Sleep -s 8;$n.Dispose()",
            ]
        )
        return True
    except Exception:
        return False


def telegram(token: str, chat_id: str, text: str) -> bool:
    """Send a message via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace")).get("ok", False)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        print(f"  telegram HTTP {e.code}: {detail}", file=sys.stderr)
    except Exception as e:
        print(f"  telegram failed: {type(e).__name__}: {e}", file=sys.stderr)
    return False


ICON = {"crit": "\U0001F534", "warn": "\U0001F7E1", "info": "\U0001F535"}


def build_text(snap: dict, alerts: list) -> str:
    s, q, p, d = snap["sessions"], snap["quota"], snap["processes"], snap["disk"]
    lines = [
        f"*OpenCode Usage*  `{snap.get('generated_at','?')}`",
        f"sessions `{s['count']}` · requests today `{q['requests_today']}/{q['free_daily_cap']}`"
        f" ({q['used_pct']}%)",
        f"tokens `{s['tokens']['total']:,}` · cache hit `{s['tokens']['cache_hit_rate']*100:.0f}%`",
        f"db `{d.get('opencode.db',{}).get('mb',0):.0f} MB` · store `{d.get('_total_mb',0):.0f} MB`"
        f" · app `{p['rss_mb']:.0f} MB`",
        f"cost `${s['cost']:.2f}` (est `${s['cost_est']:.2f}`)",
    ]
    for a in alerts:
        lines.append(f"{ICON.get(a['level'],'')} *{a['title']}* — {a['detail']}")
    return "\n".join(lines)


def webhook(url: str, payload: dict) -> bool:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "opencode-usage/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  webhook failed: {type(e).__name__}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet-ok", action="store_true")
    ap.add_argument("--always", action="store_true", help="ignore dedup state")
    ap.add_argument("--test-telegram", action="store_true", help="send a test message")
    args = ap.parse_args()

    if not os.path.exists(SNAPSHOT):
        print("no snapshot yet; run collect.py first", file=sys.stderr)
        return 2

    with open(SNAPSHOT, encoding="utf-8") as fh:
        snap = json.load(fh)

    cfg = snap.get("config", {})
    token, chat, source = load_telegram_secret()

    if args.test_telegram:
        if not (token and chat):
            print(
                f"telegram not configured (source={source}). "
                f"Run set_telegram.ps1, or set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.",
                file=sys.stderr,
            )
            return 2
        ok = telegram(
            token,
            chat,
            "*OpenCode Usage* 測試訊息\n"
            f"`{snap.get('generated_at')}` · 來源 `{source}`\n"
            f"今日額度 `{snap.get('quota', {}).get('requests_today')}/"
            f"{snap.get('quota', {}).get('free_daily_cap')}`\n"
            f"db `{snap.get('disk', {}).get('opencode.db', {}).get('mb', 0):.0f} MB`\n"
            f"目前告警 {len(snap.get('alerts', []))} 筆 · token 由本機 DPAPI 解密，未寫入任何檔案",
        )
        print(f"telegram test ({source}):", "ok" if ok else "failed")
        return 0 if ok else 1

    alerts = snap.get("alerts", [])
    if not alerts and args.quiet_ok:
        print("no alerts")
        return 0

    state = load_state()
    current = fingerprint(alerts)
    new = [a for a in alerts if f"{a['level']}:{a['title']}" not in state.get("fired", [])]
    if not args.always:
        new = new if current != state.get("fired") else []

    for a in new:
        print(f"[{a['level']}] {a['title']}: {a['detail']}")

    if not new or args.dry_run:
        print(f"({len(new)} notification(s) {'would be sent' if args.dry_run else 'sent'})"
              if new else "no new alerts since last run")
        return 0

    hook = os.environ.get("OPENCODE_ALERT_WEBHOOK") or cfg.get("webhook", "")
    if hook:
        webhook(
            hook,
            {
                "source": "opencode-usage",
                "generated_at": snap.get("generated_at"),
                "alerts": new,
                "summary": {
                    "db_mb": snap.get("disk", {}).get("opencode.db", {}).get("mb"),
                    "requests_today": snap.get("quota", {}).get("requests_today"),
                    "rss_mb": snap.get("processes", {}).get("rss_mb"),
                },
            },
        )

    if token and chat:
        ok = telegram(token, chat, build_text(snap, new))
        print(f"  telegram ({source}): {'sent' if ok else 'failed'}")
    elif source in ("none", "disabled", "error", "decrypt-failed"):
        print(f"  telegram: skipped ({source})", file=sys.stderr)

    if cfg.get("toast", True):
        for a in new:
            toast(f"OpenCode · {a['title']}", a["detail"])

    state["fired"] = current
    state["at"] = snap.get("generated_at")
    save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
