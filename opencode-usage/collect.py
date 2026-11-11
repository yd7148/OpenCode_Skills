"""Read-only OpenCode usage collector.

Writes snapshot.json / history.jsonl and refreshes dashboard.html.
Never writes to the OpenCode database, auth.json, or config.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
SHARE = os.path.join(HOME, ".local", "share", "opencode")
DB = os.path.join(SHARE, "opencode.db")
LOG = os.path.join(SHARE, "log", "opencode.log")
AUTH = os.path.join(SHARE, "auth.json")
OUT_DIR = os.path.join(HOME, ".local", "share", "opencode-usage")
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(SKILL_DIR, "templates", "dashboard.html")

SNAPSHOT = os.path.join(OUT_DIR, "snapshot.json")
HISTORY = os.path.join(OUT_DIR, "history.jsonl")
DASHBOARD = os.path.join(OUT_DIR, "dashboard.html")
DASHBOARD_LINK = os.path.join(SKILL_DIR, "dashboard-latest.html")

# --------------------------------------------------------------------------- #
# Free-tier limit, reverse-engineered from the server source.
#
#   packages/console/app/src/routes/zen/util/ipRateLimiter.ts
#     const dailyLimit     = rateLimit ?? limits.dailyRequests
#     const dailyInterval  = rateLimit ? `${YYYYMMDD}${modelId.substring(0,2)}` : YYYYMMDD
#     isNew = isDefaultModel && lifetimeCount < dailyLimit * 7
#     if ((isNew && dailyCount >= dailyLimit * 2) || (!isNew && dailyCount >= dailyLimit))
#
#   packages/console/core/src/subscription.ts
#     getFreeLimits() -> getLimits()["free"]  // dailyRequests from Resource.ZEN_LIMITS
#
# Consequences that matter here:
#   1. The counter is keyed by IP ADDRESS, not by account. A new egress IP
#      (VPN, corporate proxy, mobile hotspot) resets everything.
#   2. The day rolls over at 00:00 UTC (buildYYYYMMDD uses toISOString), which is
#      08:00 in UTC+8. Not local midnight.
#   3. A model carrying its own `rateLimit` gets a SEPARATE bucket and its own
#      limit; models without one share a single bucket.
#   4. "New" IPs (lifetime < dailyLimit * 7) get DOUBLE the daily limit.
#   5. limits.dailyRequests lives in a server-side resource, not in git, so it
#      can change at any time. 200 is the documented/observed value; the tool
#      treats it as a configurable estimate, never as ground truth.
# Only provider "opencode" (Zen) traffic is counted against this limit.
# --------------------------------------------------------------------------- #
ZEN_PROVIDER = "opencode"
FREE_DAILY_BASE = 200   # limits.dailyRequests, as documented
FREE_NEW_USER_MULT = 2  # isNew -> dailyLimit * 2
FREE_LIFETIME_FACTOR = 7  # isNew = lifetime < dailyLimit * 7
GO_TIER = {"5h_usd": 12.0, "week_usd": 30.0, "month_usd": 60.0}

CONFIG_PATH = os.path.join(HOME, ".config", "opencode", "oc-usage.json")

DEFAULT_CONFIG = {
    "db_warn_mb": 4096,
    "db_crit_mb": 8192,
    "idle_warn_min": 240,
    "cost_warn_usd": 1.0,
    "quota_warn_pct": 80.0,
    "quota_crit_pct": 95.0,
    "free_daily_base": FREE_DAILY_BASE,
    "free_daily_cap": 400,  # base * 2, the "new IP" tier
    "free_daily_cap_is_estimate": True,
    "credits_enabled": True,
    "credits_ttl_min": 30,
    "webhook": "",
    "toast": True,
    "telegram": {
        "enabled": True,
        "bot_token": "",
        "chat_id": "",
        "silent_ok": True,
    },
    "theme": "dark",
}

# Fallback list prices (USD per 1M tokens) used only when a paid model shows up.
PRICES = {
    ("openrouter", "openai/gpt-5.5"): (1.05, 8.40, 0.105),
    ("openrouter", "anthropic/claude-sonnet-4-5"): (3.0, 15.0, 0.30),
    ("opencode", "gpt-5.6-sol"): (1.75, 14.0, 0.175),
    ("opencode", "gpt-5.6-luna"): (0.20, 1.20, 0.02),
    ("opencode", "claude-sonnet-4-5"): (3.0, 15.0, 0.30),
}


def now_ms() -> int:
    return int(time.time() * 1000)


def iso(ms: int | None) -> str | None:
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone().isoformat(
        timespec="seconds"
    )


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                cfg.update(json.load(fh))
        except Exception:
            pass
    return cfg


def dir_size_mb(path: str) -> tuple[float, int]:
    total, count = 0, 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
                count += 1
            except OSError:
                pass
    return round(total / 1048576, 2), count


def connect() -> sqlite3.Connection:
    uri = "file:" + DB.replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5)


def parse_model(raw: str | None) -> dict:
    if not raw:
        return {"provider": "unknown", "model": "unknown", "variant": ""}
    try:
        obj = json.loads(raw)
        return {
            "provider": obj.get("providerID", "unknown"),
            "model": obj.get("id", "unknown"),
            "variant": obj.get("variant", ""),
        }
    except Exception:
        return {"provider": "unknown", "model": raw, "variant": ""}


def estimate_cost(provider: str, model: str, tin, tout, tread) -> float:
    price = PRICES.get((provider, model))
    if not price:
        return 0.0
    pin, pout, pcache = price
    return round((tin / 1e6) * pin + (tout / 1e6) * pout + (tread / 1e6) * pcache, 6)


# --------------------------------------------------------------------------- #
# collection
# --------------------------------------------------------------------------- #


def collect_sessions(conn, cfg) -> dict:
    q = conn.execute
    now = now_ms()
    day = now - 86400000

    totals = q(
        """select count(*), coalesce(sum(cost),0), coalesce(sum(tokens_input),0),
                  coalesce(sum(tokens_output),0), coalesce(sum(tokens_reasoning),0),
                  coalesce(sum(tokens_cache_read),0), coalesce(sum(tokens_cache_write),0),
                  coalesce(sum(summary_files),0), coalesce(sum(summary_additions),0),
                  coalesce(sum(summary_deletions),0)
           from session"""
    ).fetchone()
    (
        n_sessions,
        cost,
        tin,
        tout,
        treason,
        tread,
        twrite,
        files,
        adds,
        dels,
    ) = totals

    last24 = q(
        """select count(*), coalesce(sum(tokens_input),0), coalesce(sum(tokens_output),0),
                  coalesce(sum(tokens_cache_read),0), coalesce(sum(cost),0)
           from session where time_updated >= ?""",
        (day,),
    ).fetchone()

    last_update = q("select max(time_updated) from session").fetchone()[0]

    by_model = []
    for raw, cnt, mi, mo, mr, mc, mcost in q(
        """select model, count(*), sum(tokens_input), sum(tokens_output),
                  sum(tokens_cache_read), sum(tokens_cache_write), sum(cost)
           from session group by model"""
    ):
        info = parse_model(raw)
        by_model.append(
            {
                **info,
                "sessions": cnt,
                "input": mi or 0,
                "output": mo or 0,
                "cache_read": mr or 0,
                "cache_write": mc or 0,
                "cost": round(mcost or 0, 4),
                "cost_est": estimate_cost(
                    info["provider"], info["model"], mi or 0, mo or 0, mr or 0
                ),
            }
        )
    by_model.sort(key=lambda r: r["input"] + r["output"] + r["cache_read"], reverse=True)

    by_project = []
    for pname, directory, cnt, tcreated in q(
        """select coalesce(p.name,''), s.directory, count(*), min(s.time_created)
           from session s left join project p on p.id = s.project_id
           group by s.project_id order by 3 desc"""
    ):
        by_project.append(
            {
                "name": pname or os.path.basename(directory or "?"),
                "directory": directory,
                "sessions": cnt,
                "first": iso(tcreated),
            }
        )

    recent = []
    for sid, title, raw, directory, c, u in q(
        """select id, title, model, directory, cost, time_updated
           from session order by time_updated desc limit 12"""
    ):
        info = parse_model(raw)
        recent.append(
            {
                "id": sid,
                "title": title or "(untitled)",
                **info,
                "cost": round(c, 4),
                "updated": iso(u),
                "age_min": round((now - u) / 60000, 1) if u else None,
            }
        )

    return {
        "count": n_sessions,
        "tokens": {
            "input": tin,
            "output": tout,
            "reasoning": treason,
            "cache_read": tread,
            "cache_write": twrite,
            "total": tin + tout + treason + tread + twrite,
            "cache_hit_rate": round(tread / (tin + tread), 4) if (tin + tread) else 0.0,
        },
        "cost": round(cost, 4),
        "cost_est": round(
            sum(m["cost_est"] for m in by_model), 4
        ),
        "diff": {"files": files, "additions": adds, "deletions": dels},
        "last24h": {
            "sessions": last24[0],
            "input": last24[1] or 0,
            "output": last24[2] or 0,
            "cache_read": last24[3] or 0,
            "cost": round(last24[4] or 0, 4),
        },
        "last_active": iso(last_update),
        "idle_min": round((now - last_update) / 60000, 1) if last_update else None,
        "by_model": by_model,
        "by_project": by_project,
        "recent": recent,
    }


def collect_requests(conn) -> dict:
    """Per-request stats from the message table (assistant turns only)."""
    q = conn.execute
    now = now_ms()
    horizon = now - 24 * 3600 * 1000

    row = q(
        """select count(*), coalesce(sum(json_extract(data,'$.tokens.input')),0),
                  coalesce(sum(json_extract(data,'$.tokens.output')),0),
                  coalesce(sum(json_extract(data,'$.tokens.reasoning')),0),
                  coalesce(sum(json_extract(data,'$.tokens.cache.read')),0),
                  coalesce(sum(json_extract(data,'$.cost')),0)
           from message
           where json_extract(data,'$.role')='assistant'"""
    ).fetchone()
    totals = {
        "requests": row[0] or 0,
        "input": row[1] or 0,
        "output": row[2] or 0,
        "reasoning": row[3] or 0,
        "cache_read": row[4] or 0,
        "cost": round(row[5] or 0, 4),
    }

    buckets = {}
    for created, in q(
        """select time_created from message
           where json_extract(data,'$.role')='assistant' and time_created >= ?
           order by time_created""",
        (horizon,),
    ):
        hour = datetime.fromtimestamp(created / 1000).strftime("%Y-%m-%d %H:00")
        buckets[hour] = buckets.get(hour, 0) + 1

    today = datetime.now().strftime("%Y-%m-%d")
    requests_today = sum(v for k, v in buckets.items() if k.startswith(today))

    # The server rolls its counter over at 00:00 UTC (buildYYYYMMDD uses
    # toISOString), so the "today" bucket must follow UTC, not local time.
    utc_now = datetime.now(timezone.utc)
    day_start_utc = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
    ms_utc_day = int(day_start_utc.timestamp() * 1000)

    def since(ms_ago: int) -> int:
        return q(
            """select count(*) from message
               where json_extract(data,'$.role')='assistant'
                 and json_extract(data,'$.providerID')=?
                 and time_created >= ?""",
            (ZEN_PROVIDER, now - ms_ago),
        ).fetchone()[0]

    def zen_since(ms_from: int) -> int:
        return q(
            """select count(*) from message
               where json_extract(data,'$.role')='assistant'
                 and json_extract(data,'$.providerID')=?
                 and time_created >= ?""",
            (ZEN_PROVIDER, ms_from),
        ).fetchone()[0]

    # Zen traffic only: the free limiter never sees other providers.
    zen_today = zen_since(ms_utc_day)
    zen_5h = since(5 * 3600 * 1000)
    zen_1h = since(3600 * 1000)
    zen_24h = since(24 * 3600 * 1000)
    zen_lifetime = q(
        """select count(*) from message
           where json_extract(data,'$.role')='assistant'
             and json_extract(data,'$.providerID')=?""",
        (ZEN_PROVIDER,),
    ).fetchone()[0]

    requests_all_today = sum(
        v for k, v in buckets.items() if k.startswith(datetime.now().strftime("%Y-%m-%d"))
    )

    first_5h = q(
        """select min(time_created) from message
           where json_extract(data,'$.role')='assistant'
             and json_extract(data,'$.providerID')=? and time_created >= ?""",
        (ZEN_PROVIDER, now - 5 * 3600 * 1000),
    ).fetchone()[0]

    zen_models = []
    for model, n, small in q(
        """select json_extract(data,'$.modelID'), count(*),
                  sum(case when json_extract(data,'$.small') in (1,'true') then 1 else 0 end)
           from message
           where json_extract(data,'$.role')='assistant'
             and json_extract(data,'$.providerID')=?
             and time_created >= ?
           group by 1 order by 2 desc""",
        (ZEN_PROVIDER, ms_utc_day),
    ):
        zen_models.append(
            {
                "model": model,
                "requests": n,
                "small": small or 0,
                "share_pct": round(n / zen_today * 100, 1) if zen_today else 0.0,
            }
        )

    series = []
    start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(
        hours=23
    )
    for i in range(24):
        key = (start + timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
        series.append({"hour": key, "requests": buckets.get(key, 0)})

    models = []
    for provider, model, cnt, tok in q(
        """select json_extract(data,'$.providerID'), json_extract(data,'$.modelID'),
                  count(*),
                  coalesce(sum(json_extract(data,'$.tokens.input'))
                         + sum(json_extract(data,'$.tokens.output')),0)
           from message
           where json_extract(data,'$.role')='assistant'
             and json_extract(data,'$.modelID') is not null
           group by 1,2 order by 4 desc"""
    ):
        models.append(
            {"provider": provider, "model": model, "requests": cnt, "tokens": tok or 0}
        )

    return {
        **totals,
        "requests_today": requests_today,
        "zen_today": zen_today,
        "zen_1h": zen_1h,
        "zen_5h": zen_5h,
        "zen_24h": zen_24h,
        "zen_lifetime": zen_lifetime,
        "zen_models_today": zen_models,
        "utc_day_start": day_start_utc.astimezone().isoformat(timespec="seconds"),
        "window_5h_start": iso(first_5h),
        "peak_hour": max(
            ({"hour": k, "requests": v} for k, v in buckets.items()),
            key=lambda r: r["requests"],
            default={"hour": None, "requests": 0},
        ),
        "hourly": series,
        "by_model": models,
    }


def collect_disk() -> dict:
    out = {}
    for name in ("log", "snapshot", "storage", "tool-output", "repos"):
        path = os.path.join(SHARE, name)
        if os.path.isdir(path):
            mb, count = dir_size_mb(path)
            out[name] = {"mb": mb, "files": count}
    db_mb = round(os.path.getsize(DB) / 1048576, 2) if os.path.exists(DB) else 0
    out["opencode.db"] = {"mb": db_mb, "files": 1}
    for suffix in ("-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            out["opencode.db" + suffix] = {
                "mb": round(os.path.getsize(p) / 1048576, 2),
                "files": 1,
            }
    out["_total_mb"] = round(sum(v["mb"] for k, v in out.items() if not k.startswith("_")), 2)
    return out


def collect_processes() -> dict:
    ps = (
        "Get-Process OpenCode -ErrorAction SilentlyContinue | "
        "Measure-Object -Property WorkingSet64 -Sum"
    )
    procs = []
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process OpenCode -ErrorAction SilentlyContinue | "
                "ForEach-Object { \"{0}|{1}|{2}\" -f $_.Id, "
                "[math]::Round($_.CPU,1), [math]::Round($_.WorkingSet64/1MB,1) }",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
        for line in out.strip().splitlines():
            parts = line.split("|")
            if len(parts) == 3:
                procs.append(
                    {
                        "pid": int(parts[0]),
                        "cpu_s": float(parts[1]),
                        "rss_mb": float(parts[2]),
                    }
                )
    except Exception:
        pass
    return {
        "count": len(procs),
        "rss_mb": round(sum(p["rss_mb"] for p in procs), 1),
        "cpu_s": round(sum(p["cpu_s"] for p in procs), 1),
        "processes": procs,
    }


# Strict: only ERROR/WARN lines count, and permission echoes are ignored so the
# monitor's own commands cannot create phantom rate-limit events.
RATE_PAT = re.compile(
    r"(?<![\d.])(429|429 Too Many Requests)\b"
    r"|rate[ _-]?limit(?:ed)?\b|too many requests|quota (?:exceeded|exhausted)"
    r"|insufficient (?:quota|credit|balance)",
    re.I,
)
LVL_PAT = re.compile(r"level=(ERROR|WARN)")
NOISE_PAT = re.compile(r"message=evaluated permission|^[^=]*=[\d.]+Z?\s*$")


def is_error_line(line: str) -> bool:
    if NOISE_PAT.search(line):
        return False
    m = LVL_PAT.search(line)
    return bool(m)


def collect_log() -> dict:
    out = {"scanned_mb": 0.0, "errors_24h": 0, "rate_limit_events": 0, "recent": []}
    if not os.path.exists(LOG):
        return out
    out["scanned_mb"] = round(os.path.getsize(LOG) / 1048576, 2)
    try:
        # tail only: the log grows unbounded, never read the whole file
        with open(LOG, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 4 * 1048576))
            tail = fh.read().decode("utf-8", "replace")
    except OSError:
        return out

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    hits = []
    for line in tail.splitlines():
        if not is_error_line(line):
            continue
        m = re.match(r"(\S+)", line)
        ts = m.group(1) if m else ""
        try:
            fresh = datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff
        except Exception:
            fresh = False
        if not fresh:
            continue
        rate = bool(RATE_PAT.search(line))
        if rate:
            out["rate_limit_events"] += 1
        out["errors_24h"] += 1
        if len(hits) < 8:
            hits.append(line[:220])
    out["recent"] = hits
    return out


def cached_credits(ttl_min: int) -> dict:
    if os.path.exists(SNAPSHOT):
        try:
            with open(SNAPSHOT, encoding="utf-8") as fh:
                old = json.load(fh)
            stamps = old.get("credits_checked_at") or 0
            if stamps and (now_ms() - stamps) / 60000 < ttl_min:
                return old.get("credits", {})
        except Exception:
            pass
    return {}


def probe_credits(cfg) -> dict:
    res = {}
    if not cfg.get("credits_enabled", True):
        return res
    try:
        with open(AUTH, encoding="utf-8") as fh:
            auth = json.load(fh)
    except Exception:
        return res

    def get(url, key, headers=None):
        h = {"Authorization": "Bearer " + key, "User-Agent": "opencode-usage/1.0"}
        h.update(headers or {})
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    or_key = (auth.get("openrouter") or {}).get("key")
    if or_key:
        try:
            data = get("https://openrouter.ai/api/v1/credits", or_key)
            d = data.get("data", data)
            total, used = d.get("total_credits"), d.get("total_usage")
            res["openrouter"] = {
                "ok": True,
                "total_credits": total,
                "total_usage": used,
                "remaining": round((total or 0) - (used or 0), 4)
                if total is not None
                else None,
            }
        except urllib.error.HTTPError as e:
            res["openrouter"] = {"ok": False, "status": e.code, "note": "silently degraded"}
        except Exception as e:
            res["openrouter"] = {"ok": False, "note": type(e).__name__}

    agnes = auth.get("agnes") or {}
    if agnes.get("key"):
        base = agnes.get("url") or "https://api.agnes.ai"
        url = base.rstrip("/") + "/v1/dashboard/billing/credit_grants"
        try:
            data = get(url, agnes["key"])
            res["agnes"] = {
                "ok": True,
                "remaining": (data.get("data") or data).get("total_granted", 0)
                - (data.get("data") or data).get("total_used", 0),
            }
        except Exception as e:
            res["agnes"] = {"ok": False, "note": "no public credit endpoint"}

    res["opencode_zen"] = {
        "ok": True,
        "note": "no public API for free tier; using local estimate",
        "remaining": None,
    }
    return res


def sanitize_config(cfg: dict) -> dict:
    """Never let secrets reach snapshot.json or the injected dashboard HTML."""
    safe = {}
    for k, v in cfg.items():
        if k in ("webhook", "telegram"):
            if k == "telegram" and isinstance(v, dict):
                # keep only non-secret switches
                safe["telegram"] = {
                    kk: vv for kk, vv in v.items() if kk in ("enabled", "silent_ok")
                }
            continue
        if isinstance(v, str) and ("token" in k.lower() or "key" in k.lower()):
            continue
        safe[k] = v
    return safe


def build(cfg) -> dict:
    conn = connect()
    try:
        sessions = collect_sessions(conn, cfg)
        requests = collect_requests(conn)
    finally:
        conn.close()

    disk = collect_disk()
    procs = collect_processes()
    log = collect_log()
    credits = cached_credits(cfg.get("credits_ttl_min", 30)) or probe_credits(cfg)

    cap = cfg.get("free_daily_cap") or 400
    base = cfg.get("free_daily_base") or FREE_DAILY_BASE
    used = requests["zen_today"]
    lifetime = requests["zen_lifetime"]
    new_tier_threshold = base * FREE_LIFETIME_FACTOR
    quota = {
        "provider": ZEN_PROVIDER,
        "free_daily_base": base,
        "free_daily_cap": cap,
        "cap_is_estimate": bool(cfg.get("free_daily_cap_is_estimate", True)),
        "tier_note": f"base {base} (limits.dailyRequests) x{FREE_NEW_USER_MULT} "
        f"while IP lifetime < {new_tier_threshold}",
        "warn_pct": cfg.get("quota_warn_pct", 80.0),
        "crit_pct": cfg.get("quota_crit_pct", 95.0),
        "requests_today": used,
        "used_pct": round(used / cap * 100, 1) if cap else None,
        "remaining_est": max(cap - used, 0),
        "window_1h": requests["zen_1h"],
        "window_5h": requests["zen_5h"],
        "window_24h": requests["zen_24h"],
        "lifetime": lifetime,
        "local_is_new_tier": lifetime < new_tier_threshold,
        "window_5h_start": requests["window_5h_start"],
        "utc_day_start": requests["utc_day_start"],
        "models_today": requests["zen_models_today"],
        "peak_hour": requests["peak_hour"],
        "blocked_events": log["rate_limit_events"],
        "cap_source": "ipRateLimiter.ts (dev branch) + issues #25619 / #15585 / #33495 / #34344",
        "go_tier": GO_TIER,
        "window_5h_cap_usd": GO_TIER["5h_usd"],
    }

    alerts = evaluate(cfg, sessions, requests, disk, log, quota)

    return {
        "generated_at": iso(now_ms()),
        "generated_ms": now_ms(),
        "interval_min": 10,
        "host": os.environ.get("COMPUTERNAME", "?"),
        "config": sanitize_config(cfg),
        "sessions": sessions,
        "requests": requests,
        "disk": disk,
        "processes": procs,
        "log": log,
        "quota": quota,
        "credits": credits,
        "credits_checked_at": now_ms(),
        "alerts": alerts,
        "history": read_history(72),
    }


def evaluate(cfg, sessions, requests, disk, log, quota) -> list:
    alerts = []
    db_mb = disk.get("opencode.db", {}).get("mb", 0)
    if db_mb > cfg.get("db_crit_mb", 8192):
        alerts.append(
            {
                "level": "crit",
                "title": "Database critical",
                "detail": f"opencode.db is {db_mb:.0f} MB (critical "
                f"{cfg['db_crit_mb']} MB). event/part blobs are ~82% of it - archive "
                f"old sessions; VACUUM will not help (no free pages).",
            }
        )
    elif db_mb > cfg.get("db_warn_mb", 4096):
        alerts.append(
            {
                "level": "warn",
                "title": "Database size",
                "detail": f"opencode.db is {db_mb:.0f} MB (threshold "
                f"{cfg['db_warn_mb']} MB).",
            }
        )
    idle = sessions.get("idle_min")
    if idle is not None and idle > cfg.get("idle_warn_min", 240):
        alerts.append(
            {
                "level": "info",
                "title": "Idle",
                "detail": f"No session activity for {idle / 60:.1f} h.",
            }
        )
    q = quota
    if q["used_pct"] is not None and q["used_pct"] >= q["crit_pct"]:
        alerts.append(
            {
                "level": "crit",
                "title": "Free quota nearly exhausted",
                "detail": f"{q['requests_today']}/{q['free_daily_cap']} Zen requests "
                f"({q['used_pct']}%) - about {q['remaining_est']} left. Counted per IP and "
                f"per UTC day (resets at the start of utc_day_start).",
            }
        )
    elif q["used_pct"] is not None and q["used_pct"] >= q["warn_pct"]:
        alerts.append(
            {
                "level": "warn",
                "title": "Free quota at "
                f"{q['used_pct']}%",
                "detail": f"{q['requests_today']}/{q['free_daily_cap']} Zen requests used "
                f"({q['used_pct']}%), {q['remaining_est']} estimated left. "
                f"Rolling 5h window: {q['window_5h']}.",
            }
        )
    if q["blocked_events"]:
        alerts.append(
            {
                "level": "crit",
                "title": "FreeUsageLimitError (429) received",
                "detail": f"{q['blocked_events']} rate-limit events in 24h - the free cap "
                f"was actually hit. The counter is per IP, so changing network resets it.",
            }
        )
    cost = sessions.get("cost_est", 0)
    if cost > cfg.get("cost_warn_usd", 5.0):
        alerts.append(
            {
                "level": "warn",
                "title": "Estimated cost",
                "detail": f"Estimated spend is ${cost:.2f} (threshold "
                f"${cfg['cost_warn_usd']}).",
            }
        )
    for name, info in disk.items():
        if name.startswith("_") or name == "opencode.db":
            continue  # the database has its own warn/crit rules above
        if info["mb"] > 2048:
            alerts.append(
                {
                    "level": "info",
                    "title": "Large store",
                    "detail": f"{name} is {info['mb']:.0f} MB.",
                }
            )
            break
    return alerts


def read_history(limit: int) -> list:
    if not os.path.exists(HISTORY):
        return []
    rows = []
    try:
        with open(HISTORY, encoding="utf-8") as fh:
            for line in fh.readlines()[-limit:]:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except Exception:
        pass
    return rows


def write_outputs(snap: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    flat = {
        "generated_at": snap["generated_at"],
        "generated_ms": snap["generated_ms"],
        "sessions": snap["sessions"]["count"],
        "tokens_total": snap["sessions"]["tokens"]["total"],
        "tokens_input": snap["sessions"]["tokens"]["input"],
        "tokens_output": snap["sessions"]["tokens"]["output"],
        "cache_read": snap["sessions"]["tokens"]["cache_read"],
        "requests": snap["requests"]["requests"],
        "requests_today": snap["requests"]["requests_today"],
        "db_mb": snap["disk"].get("opencode.db", {}).get("mb", 0),
        "store_mb": snap["disk"].get("_total_mb", 0),
        "rss_mb": snap["processes"]["rss_mb"],
        "quota_pct": snap["quota"]["used_pct"],
        "cost_est": snap["sessions"]["cost_est"],
        "alerts": len(snap["alerts"]),
    }
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(flat, ensure_ascii=False) + "\n")
    # keep history bounded
    try:
        with open(HISTORY, encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) > 20000:
            with open(HISTORY, "w", encoding="utf-8") as fh:
                fh.writelines(lines[-10000:])
    except OSError:
        pass

    with open(SNAPSHOT, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1)

    if os.path.exists(TEMPLATE):
        with open(TEMPLATE, encoding="utf-8") as fh:
            html = fh.read()
        payload = json.dumps(snap, ensure_ascii=False)
        html = html.replace("/*__DATA__*/null", payload)
        with open(DASHBOARD, "w", encoding="utf-8") as fh:
            fh.write(html)
        try:
            shutil.copyfile(DASHBOARD, DASHBOARD_LINK)
        except OSError:
            pass


def report(snap: dict) -> str:
    s, r, d, q = snap["sessions"], snap["requests"], snap["disk"], snap["quota"]
    t = s["tokens"]
    lines = [
        f"OpenCode usage @ {snap['generated_at']}  ({snap['host']})",
        "-" * 62,
        f"sessions            {s['count']}   (last 24h: {s['last24h']['sessions']})",
        f"requests            {r['requests']}  (today: {r['requests_today']})",
        f"tokens total        {t['total']:,}",
        f"  input             {t['input']:,}",
        f"  output            {t['output']:,}",
        f"  reasoning         {t['reasoning']:,}",
        f"  cache read/write  {t['cache_read']:,} / {t['cache_write']:,}"
        f"   (hit rate {t['cache_hit_rate'] * 100:.1f}%)",
        f"cost                ${s['cost']:.4f}  (estimated ${s['cost_est']:.4f})",
        f"free quota (Zen)     {q['requests_today']}/{q['free_daily_cap']} since "
        f"{q['utc_day_start'][11:16]} (UTC day)  ({q['used_pct']}%)  left {q['remaining_est']}",
        f"  windows            1h {q['window_1h']} · 5h {q['window_5h']} · 24h {q['window_24h']}"
        f"  (busiest hour in 24h: {q['peak_hour']['requests']})",
        f"  blocked events     {q['blocked_events']}   [{q['tier_note']}]",
        f"disk                db {d.get('opencode.db', {}).get('mb', 0):.0f} MB,"
        f" total {d['_total_mb']:.0f} MB",
        f"processes           {snap['processes']['count']} x OpenCode,"
        f" {snap['processes']['rss_mb']:.0f} MB RSS",
        f"last activity       {s['last_active']} ({s['idle_min']:.0f} min ago)"
        if s.get("idle_min") is not None
        else "last activity       unknown",
        "",
        "top models:",
    ]
    for m in s["by_model"][:6]:
        lines.append(
            f"  {m['provider']}/{m['model']:<28} {m['sessions']:>4} sess"
            f"  in {m['input']:>12,}  out {m['output']:>10,}  cache {m['cache_read']:>12,}"
        )
    lines += ["", "credits:"]
    for name, info in (snap.get("credits") or {}).items():
        if info.get("ok") and info.get("remaining") is not None:
            lines.append(f"  {name:<14} remaining {info['remaining']}")
        else:
            lines.append(f"  {name:<14} unknown ({info.get('note', info.get('status'))})")
    if snap["alerts"]:
        lines += ["", "alerts:"]
    for a in snap["alerts"]:
        lines.append(f"  [{a['level']}] {a['title']}: {a['detail']}")
    else:
        lines += ["", "no alerts"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print markdown report")
    ap.add_argument("--no-dashboard", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(DB):
        print(f"opencode.db not found: {DB}", file=sys.stderr)
        return 2

    t0 = time.time()
    cfg = load_config()
    snap = build(cfg)
    snap["collect_ms"] = int((time.time() - t0) * 1000)
    write_outputs(snap)

    if args.report:
        print(report(snap))
    else:
        print(
            f"snapshot -> {SNAPSHOT}  ({snap['collect_ms']} ms, "
            f"{len(snap['alerts'])} alerts)"
        )
        if not args.no_dashboard and os.path.exists(DASHBOARD):
            print(f"dashboard -> {DASHBOARD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
