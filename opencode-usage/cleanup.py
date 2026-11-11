"""OpenCode usage monitor - cleanup utility.

Profiles
--------
safe    (default) rotate the log, drop stale tool-output caches, trim history.
                  Opens the database read-only except for a WAL checkpoint.
db      WAL truncate + incremental vacuum only. Reclaims the -wal file, no data
                  loss, but frees little because freelist_count is usually 0.
purge   DESTRUCTIVE. Deletes sessions older than --days from opencode.db and
                  vacuums. This is the only action that meaningfully shrinks the
                  database, and it permanently removes conversation history.

Everything is read-only until the action is actually run, and `purge` requires
an explicit confirmation token.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sqlite3
import sys
import time

HOME = os.path.expanduser("~")
SHARE = os.path.join(HOME, ".local", "share", "opencode")
DB = os.path.join(SHARE, "opencode.db")
LOG = os.path.join(SHARE, "log", "opencode.log")
TOOL_OUT = os.path.join(SHARE, "tool-output")
OUT_DIR = os.path.join(HOME, ".local", "share", "opencode-usage")
HISTORY = os.path.join(OUT_DIR, "history.jsonl")
DASHBOARD = os.path.join(OUT_DIR, "dashboard.html")
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIRM_TOKEN = "PURGE"


def human(n: float) -> str:
    n = float(n)
    if n >= 1073741824:
        return f"{n / 1073741824:.2f} GB"
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n:.0f} B"


def connect(readonly: bool = True) -> sqlite3.Connection:
    mode = "ro" if readonly else "rw"
    uri = "file:" + DB.replace("\\", "/") + f"?mode={mode}"
    return sqlite3.connect(uri, uri=True, timeout=20)


def age_days(path: str) -> float:
    return (time.time() - os.path.getmtime(path)) / 86400


# --------------------------------------------------------------------------- #
# survey
# --------------------------------------------------------------------------- #


def survey(tool_days: int, keep_log_mb: float, keep_history: int) -> dict:
    items = []

    if os.path.exists(LOG):
        size = os.path.getsize(LOG)
        keep = int(keep_log_mb * 1048576)
        items.append(
            {
                "id": "log",
                "label": "opencode.log",
                "action": f"rotate, keep last {keep_log_mb:g} MB",
                "size": size,
                "reclaimable": max(size - keep, 0),
                "risk": "none",
            }
        )

    stale = stale_files = fresh = 0
    if os.path.isdir(TOOL_OUT):
        for name in os.listdir(TOOL_OUT):
            p = os.path.join(TOOL_OUT, name)
            if os.path.isfile(p):
                size = os.path.getsize(p)
                if age_days(p) > tool_days:
                    stale += size
                    stale_files += 1
                else:
                    fresh += size
        items.append(
            {
                "id": "tool-output",
                "label": "tool-output/",
                "action": f"delete {stale_files} cached tool results older than "
                f"{tool_days} days (keep {human(fresh)})",
                "size": stale + fresh,
                "reclaimable": stale,
                "risk": "low - only affects re-reading old tool output",
            }
        )

    for suffix in ("-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            items.append(
                {
                    "id": "db" + suffix,
                    "label": "opencode.db" + suffix,
                    "action": "WAL truncate (checkpoint)",
                    "size": os.path.getsize(p),
                    "reclaimable": os.path.getsize(p),
                    "risk": "none",
                }
            )

    if os.path.exists(HISTORY):
        lines = open(HISTORY, encoding="utf-8").readlines()
        extra = max(len(lines) - keep_history, 0)
        size = os.path.getsize(HISTORY)
        items.append(
            {
                "id": "history",
                "label": "history.jsonl",
                "action": f"keep the most recent {keep_history} rows "
                f"(drop {extra})",
                "size": size,
                "reclaimable": int(size * (extra / len(lines))) if lines else 0,
                "risk": "none",
            }
        )

    old_bytes = old_rows = 0
    if os.path.exists(DB):
        conn = connect()
        try:
            cutoff = int((time.time() - tool_days * 86400) * 1000)
            row = conn.execute(
                "select count(*), coalesce(sum(length(data)),0) from event e "
                "join session s on s.id = e.aggregate_id "
                "where s.time_updated < ?",
                (cutoff,),
            ).fetchone()
            old_rows = row[0] or 0
            old_bytes = row[1] or 0
            free = conn.execute("pragma freelist_count").fetchone()[0]
            psize = conn.execute("pragma page_size").fetchone()[0]
            total = conn.execute("pragma page_count").fetchone()[0] * psize
        finally:
            conn.close()
        items.append(
            {
                "id": "purge",
                "label": "opencode.db (purge old sessions)",
                "action": f"delete sessions untouched for {tool_days}+ days, then VACUUM",
                "size": total,
                "reclaimable": old_bytes,
                "risk": "DESTRUCTIVE - permanently removes conversation history",
                "rows": old_rows,
                "vacuum_gain": max(total - (total - old_bytes) - free * psize, 0),
            }
        )

    return {
        "items": items,
        "safe_reclaimable": sum(
            i["reclaimable"] for i in items if i["id"] not in ("purge",)
        ),
        "purge_reclaimable": next(
            (i["reclaimable"] for i in items if i["id"] == "purge"), 0
        ),
        "total_reclaimable": sum(i["reclaimable"] for i in items),
    }


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #


def rotate_log(keep_mb: float) -> int:
    keep = int(keep_mb * 1048576)
    size = os.path.getsize(LOG)
    if size <= keep:
        return 0
    with open(LOG, "rb") as fh:
        fh.seek(size - keep)
        tail = fh.read()
    backup = LOG + ".1"
    if os.path.exists(backup):
        os.remove(backup)
    # the desktop app holds the file open; copy then truncate in place
    shutil.copyfile(LOG, backup)
    try:
        with open(LOG, "r+b") as fh:
            fh.seek(0)
            fh.write(tail)
            fh.truncate()
    except PermissionError:
        return 0
    return size - len(tail)


def purge_tool_output(days: int) -> tuple[int, int]:
    if not os.path.isdir(TOOL_OUT):
        return 0, 0
    freed = count = 0
    for name in os.listdir(TOOL_OUT):
        p = os.path.join(TOOL_OUT, name)
        try:
            if os.path.isfile(p) and age_days(p) > days:
                freed += os.path.getsize(p)
                os.remove(p)
                count += 1
        except OSError:
            pass
    return freed, count


def trim_history(keep: int) -> int:
    if not os.path.exists(HISTORY):
        return 0
    lines = open(HISTORY, encoding="utf-8").readlines()
    if len(lines) <= keep:
        return 0
    before = os.path.getsize(HISTORY)
    with open(HISTORY, "w", encoding="utf-8") as fh:
        fh.writelines(lines[-keep:])
    return before - os.path.getsize(HISTORY)


def checkpoint_wal() -> int:
    before = 0
    for suffix in ("-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            before += os.path.getsize(p)
    conn = connect(readonly=False)
    try:
        conn.execute("pragma wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        conn.close()
    after = 0
    for suffix in ("-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            after += os.path.getsize(p)
    return max(before - after, 0)


def purge_sessions(days: int, backup: str | None) -> dict:
    cutoff = int((time.time() - days * 86400) * 1000)
    conn = connect(readonly=False)
    try:
        before = os.path.getsize(DB)
        if backup:
            print(f"  backup -> {backup}", flush=True)
            dst = sqlite3.connect(backup)
            try:
                conn.backup(dst)
            finally:
                dst.close()

        sessions = [
            r[0]
            for r in conn.execute(
                "select id from session where time_updated < ?", (cutoff,)
            )
        ]
        if not sessions:
            return {"deleted": 0, "freed": 0, "before": before, "after": before}

        print(f"  deleting {len(sessions)} sessions, then VACUUM ...", flush=True)
        conn.execute("pragma foreign_keys=on")
        conn.executemany("delete from session where id = ?", [(s,) for s in sessions])
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()
        after = os.path.getsize(DB)
        return {
            "deleted": len(sessions),
            "freed": max(before - after, 0),
            "before": before,
            "after": after,
        }
    finally:
        conn.close()


# --------------------------------------------------------------------------- #


def print_survey(sv: dict) -> None:
    print("OpenCode cleanup survey")
    print("-" * 78)
    for i in sv["items"]:
        mark = "!" if i["risk"].startswith("DESTRUCTIVE") else " "
        print(f"{mark} {i['label']:<34} {human(i['size']):>9}")
        print(f"    {i['action']}")
        print(f"    reclaim {human(i['reclaimable'])}   risk: {i['risk']}")
    print("-" * 78)
    print(f"safe cleanup reclaims : {human(sv['safe_reclaimable'])}   (no data loss)")
    print(
        f"session purge reclaims: {human(sv['purge_reclaimable'])}   "
        f"(DESTRUCTIVE, CLI only)"
    )
    print(f"total available       : {human(sv['total_reclaimable'])}")


def parse_target(raw: str) -> tuple[str, list]:
    """Accept 'safe' or a protocol URL such as 'ocusage://purge?days=30'."""
    if "//" not in raw:
        return raw.strip("/"), []
    from urllib.parse import parse_qs, urlparse

    p = urlparse(raw)
    args = []
    for k, v in parse_qs(p.query).items():
        args += ["--" + k.replace("-", "_")] + v
    return p.netloc or p.path.strip("/"), args


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("target", nargs="?", default="survey", help="survey|safe|db|purge")
    ap.add_argument("--days", type=int, default=30, help="age threshold in days")
    ap.add_argument("--keep-log-mb", type=float, default=2.0)
    ap.add_argument("--keep-history", type=int, default=2000)
    ap.add_argument("--apply", action="store_true", help="actually perform it")
    ap.add_argument("--yes", type=str, default="", help=f"type {CONFIRM_TOKEN} to confirm")
    ap.add_argument("--backup", type=str, default="", help="backup db path (purge)")
    ap.add_argument("--no-dashboard", action="store_true")
    args = ap.parse_args()

    target, extra = parse_target(args.target)
    for i in range(0, len(extra) - 1, 2):
        key = extra[i].lstrip("-")
        if key in ("days", "keep_history"):
            setattr(args, key, int(extra[i + 1]))
        elif key in ("keep_log_mb",):
            setattr(args, key, float(extra[i + 1]))

    tool_days = max(args.days, 1)
    sv = survey(tool_days, args.keep_log_mb, args.keep_history)
    print_survey(sv)

    if target in ("survey", "dry", ""):
        return 0

    if target not in ("safe", "db", "purge"):
        print(f"unknown target: {target}", file=sys.stderr)
        return 1

    if not args.apply:
        print(f"\nDRY RUN. add --apply to perform '{target}'.")
        return 0

    if target == "purge":
        if args.yes.strip().upper() != CONFIRM_TOKEN:
            print(
                f"\npurge is DESTRUCTIVE. re-run with --apply --yes {CONFIRM_TOKEN}"
                f"{' --backup <path>' if not args.backup else ''}",
                file=sys.stderr,
            )
            return 3

    freed = []
    print()
    if target in ("safe", "purge"):
        n = rotate_log(args.keep_log_mb)
        freed.append(("log rotated", n))
    if target in ("safe", "purge"):
        b, c = purge_tool_output(tool_days)
        freed.append((f"tool-output: {c} files", b))
        freed.append(("history trimmed", trim_history(args.keep_history)))
    if target in ("safe", "db", "purge"):
        freed.append(("WAL checkpoint", checkpoint_wal()))

    if target == "purge":
        res = purge_sessions(tool_days, args.backup or None)
        freed.append((f"db purged: {res['deleted']} sessions", res["freed"]))

    total = sum(n for _, n in freed)
    for label, n in freed:
        print(f"  {label:<34} {human(n):>9}")
    print(f"  {'TOTAL FREED':<34} {human(total):>9}")

    if not args.no_dashboard and os.path.exists(DASHBOARD):
        try:
            os.startfile(DASHBOARD)  # noqa: S606
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
