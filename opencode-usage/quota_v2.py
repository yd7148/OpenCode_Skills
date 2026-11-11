"""quota.py — OpenCode Zen free-tier 額度追蹤（唯讀）

資料來源：~/.local/share/opencode/opencode.db（mode=ro）
指標定義：opencode 供應商的 assistant 訊息數 = 實際打向模型的請求次數
日界：UTC 00:00（= 台灣時間 08:00），對齊伺服器 buildYYYYMMDD

用法：
    python quota.py            # 終端報告
    python quota.py --json     # JSON（供排程/儀表板使用）
"""
import sqlite3, json, os, sys, time, collections
from datetime import datetime, timezone

DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
FREE_BASE = 200   # 免費層每日請求上限（dailyRequests，文件觀察值）
FREE_CAP = 400    # 新 IP 雙倍層（lifetime < dailyLimit * 7）


def connect():
    return sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)


def utc_day_start_ms(now_ms):
    d = datetime.fromtimestamp(now_ms / 1000, timezone.utc)
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def tally(conn, start_ms, end_ms=None):
    """回傳 (總數, per-model Counter)"""
    n = 0
    models = collections.Counter()
    sql = "select data from session_message where time_created >= ?"
    args = [start_ms]
    if end_ms:
        sql += " and time_created < ?"
        args.append(end_ms)
    for (data,) in conn.execute(sql, args):
        try:
            j = json.loads(data)
        except Exception:
            continue
        if not (j.get("role") == "assistant" or j.get("agent")):
            continue
        m = j.get("model") or {}
        if m.get("providerID") != "opencode":
            continue
        n += 1
        models[m.get("id") or "(unknown)"] += 1
    return n, models


def main():
    now = int(time.time() * 1000)
    day0 = utc_day_start_ms(now)
    conn = connect()

    today_n, today_models = tally(conn, day0)
    yday_n, _ = tally(conn, day0 - 86400000, day0)

    week = []
    for d in range(7):
        s = day0 - d * 86400000
        n, _ = tally(conn, s, s + 86400000)
        label = datetime.fromtimestamp(s / 1000, timezone.utc).strftime("%Y-%m-%d")
        week.append({"date": label, "requests": n,
                     "over_base": n > FREE_BASE, "over_cap": n > FREE_CAP})

    peak = max((w["requests"] for w in week), default=0)
    result = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "utc_now": datetime.fromtimestamp(now / 1000, timezone.utc).isoformat(),
        "utc_day_start": day0,
        "reset_local_time": "每日 08:00 (台灣時間)",
        "requests_today": today_n,
        "requests_yesterday": yday_n,
        "models_today": dict(today_models),
        "free_daily_base": FREE_BASE,
        "free_daily_cap": FREE_CAP,
        "pct_of_base": round(today_n / FREE_BASE * 100, 1),
        "pct_of_cap": round(today_n / FREE_CAP * 100, 1),
        "cap_is_estimate": True,
        "week": week,
        "peak_7d": peak,
    }

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("=" * 60)
    print("OpenCode Zen 免費層額度追蹤")
    print("=" * 60)
    print(f"產生時間   : {result['generated_at']}")
    print(f"UTC 現在   : {result['utc_now']}")
    print(f"重置時間   : {result['reset_local_time']}")
    print()
    print(f"今日請求數  : {today_n}")
    for k, v in sorted(today_models.items(), key=lambda x: -x[1]):
        print(f"            - {k}: {v}")
    print(f"昨日請求數  : {yday_n}")
    print()
    print(f"對比 base  : {FREE_BASE}  -> {result['pct_of_base']}%")
    print(f"對比 cap   : {FREE_CAP}  -> {result['pct_of_cap']}%")
    print("（數值為推估，非官方常數；伺服器端 Resource.ZEN_LIMITS 可隨時調整）")
    print()
    print("近 7 日（UTC 日界）:")
    for w in week:
        bar = "#" * min(50, w["requests"] // 20)
        flag = " <== 超過 cap 400" if w["over_cap"] else (
               " <== 超過 base 200" if w["over_base"] else "")
        print(f"  {w['date']}  {w['requests']:5}  {bar}{flag}")
    print()
    print(f"7 日峰值    : {peak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
