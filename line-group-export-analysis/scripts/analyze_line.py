#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE 匯出聊天記錄分析器

輸入：手機 LINE「匯出聊天記錄」解壓後的資料夾（內含每月的 YYYY-MM-DD.txt）
輸出：Markdown 報告 + summary.json + daily.csv

用法：
    python analyze_line.py --input "<匯出資料夾>" --out ./output

設計原則（對應 SKILL.md 的誠實聲明要求）：
  - 缺什麼就標成「不可得」，不用猜測補齊
  - 統計為觀察，動機／情緒為推測，報告中分欄呈現
  - 不對特定個人做政治傾向或意識形態判定
"""

import argparse
import csv
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

# ---------------------------------------------------------------- 編碼偵測

def read_text(path):
    """LINE 匯出可能帶 BOM，且不同月份編碼不一致。逐一試。"""
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5", "utf-16"):
        try:
            with open(path, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 全失敗則用 utf-8 寬鬆解碼，之後靠 regex 過濾雜訊
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- 解析

RE_DATE_HEADER = re.compile(r"^(\d{4})/(\d{2})/(\d{2})[^\d]*$")
# 文字訊息列：時間 + 分隔符 + 發文者 + 分隔符 + 內文
# 分隔符可能是 Tab、半形冒號+空白、或全形冒號
RE_MSG = re.compile(
    r"^(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<sep>\t|[:：])\s*(?P<who>[^\t:：]{1,60}?)\s*(?P=sep)\s*(?P<text>.*)$"
)
# 只有時間戳、沒有發文者 → 貼圖 / 貼圖梗圖 / 刪除
RE_BARE_STAMP = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2})\s*[\t]?\s*(?P<rest>.*)$")
RE_DELETED = re.compile(r"已刪除了一則訊息|撤回了一則訊息")
RE_STICKER = re.compile(r"^\[(貼圖|貼圖梗圖)\]$|^Sticker$")

# 可辨識的「回覆」標記（文字匯出通常拿不到被回覆原文）
RE_REPLY = re.compile(r"^\[回覆[^\]]*\]\s*|^Replying to\s*")

# ---------------------------------------------------------------- 話題詞表

TOPIC_KEYWORDS = {
    "吃吃喝喝": ["吃", "餐", "飯", "喝", "咖啡", "拉麵", "火鍋", "燒烤", "早餐", "午餐", "晚餐", "宵夜"],
    "旅遊出遊": ["旅遊", "出遊", "景點", "機票", "住宿", "民宿", "行程", "打卡"],
    "工作學業": ["工作", "上班", "加班", "會議", "報告", "專案", "作業", "考試", "老師"],
    "感情家庭": ["爸媽", "爸", "媽", "男友", "女友", "老公", "老婆", "小孩", "家庭"],
    "運動健康": ["運動", "健身", "跑步", "游泳", "爬山", "健康", "看醫生"],
    "娛樂遊戲": ["電影", "劇", "演唱會", "遊戲", "打牌", "娛樂"],
    "政治公共議題": ["選舉", "政策", "政府", "立委", "總統", "藍", "綠", "白", "國會", "戰爭", "外交"],
    "科技3C": ["手機", "電腦", "APP", "app", "相機", "螢幕", "AI", "軟體"],
    "情感關懷": ["加油", "辛苦了", "抱抱", "保重", "康乃馨", "❤", "感謝"],
}

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿]"
)


def classify_topic(text):
    hits = []
    for topic, words in TOPIC_KEYWORDS.items():
        if any(w in text for w in words):
            hits.append(topic)
    return hits or ["其他"]


# ---------------------------------------------------------------- 核心解析

def parse_folder(folder):
    msgs = []
    files = sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".txt") and re.match(r"^\d{4}-\d{2}-\d{2}\.txt$", f)
    )
    if not files:
        # 相容：資料夾內直接是 *.txt（月檔命名可能不同）
        files = sorted(
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".txt")
        )
    if not files:
        raise SystemExit("[錯誤] 找不到 .txt 聊天記錄檔。請確認 --input 指向解壓後的群組資料夾。")

    cur_date = None
    for path in files:
        cur_date = None
        for line in read_text(path).splitlines():
            line = line.rstrip("\r")
            if not line.strip():
                continue

            m = RE_DATE_HEADER.match(line.strip())
            if m:
                cur_date = "-".join(m.groups())
                continue
            if cur_date is None:
                # 沒日期標頭就退用檔名
                cur_date = os.path.splitext(os.path.basename(path))[0]

            m = RE_MSG.match(line)
            if m:
                text = m.group("text").strip()
                msgs.append({
                    "date": cur_date,
                    "hour": int(m.group("h")),
                    "minute": int(m.group("m")),
                    "who": m.group("who").strip(),
                    "text": text,
                    "kind": ("deleted" if RE_DELETED.search(text)
                             else "sticker" if RE_STICKER.match(text)
                             else "reply" if RE_REPLY.match(text)
                             else "text"),
                    "has_reply": bool(RE_REPLY.match(text)),
                })
                continue

            # 只有時間戳：貼圖 / 附件，發文者無法從此列取得
            m = RE_BARE_STAMP.match(line)
            if m and cur_date:
                msgs.append({
                    "date": cur_date,
                    "hour": int(m.group("h")),
                    "minute": int(m.group("m")),
                    "who": None,
                    "text": m.group("rest").strip(),
                    "kind": "media",
                    "has_reply": False,
                })
    return msgs, [os.path.basename(p) for p in files]


def analyze(msgs):
    by_who = defaultdict(list)
    for m in msgs:
        key = m["who"] if m["who"] else "(貼圖/媒體·無署名)"
        by_who[key].append(m)

    dates = sorted({m["date"] for m in msgs})
    n_days = len(dates)

    per_user = {}
    for who, ms in by_who.items():
        lengths = [len(m["text"]) for m in ms if m["kind"] == "text" and m["text"]]
        active_days = {m["date"] for m in ms}
        hours = Counter(m["hour"] for m in ms)
        peak = hours.most_common(1)[0] if hours else (None, 0)
        per_user[who] = {
            "total": len(ms),
            "share_pct": round(100 * len(ms) / len(msgs), 2) if msgs else 0,
            "active_days": len(active_days),
            "per_active_day": round(len(ms) / len(active_days), 2) if active_days else 0,
            "per_calendar_day": round(len(ms) / n_days, 3) if n_days else 0,
            "median_len": int(statistics.median(lengths)) if lengths else None,
            "p90_len": (sorted(lengths)[int(len(lengths) * 0.9) - 1] if lengths else None),
            "peak_hour": peak[0],
            "peak_hour_count": peak[1],
            "hour_hist": {str(h): hours.get(h, 0) for h in range(24)},
            "deleted": sum(1 for m in ms if m["kind"] == "deleted"),
            "sticker": sum(1 for m in ms if m["kind"] == "sticker"),
            "media": sum(1 for m in ms if m["kind"] == "media"),
            "emoji_total": sum(len(EMOJI_RE.findall(m["text"])) for m in ms),
        }

    all_hours = Counter(m["hour"] for m in msgs)
    topics = Counter()
    for m in msgs:
        if m["kind"] != "text" or not m["text"]:
            continue
        for t in classify_topic(m["text"]):
            topics[t] += 1

    daily = Counter(m["date"] for m in msgs)

    return {
        "n_messages": len(msgs),
        "n_users": len([w for w in by_who if w.startswith("(") is False]),
        "n_days": n_days,
        "date_from": dates[0] if dates else None,
        "date_to": dates[-1] if dates else None,
        "hour_hist": {str(h): all_hours.get(h, 0) for h in range(24)},
        "peak_hour": all_hours.most_common(1)[0][0] if all_hours else None,
        "topics": dict(topics.most_common()),
        "emoji_total": sum(len(EMOJI_RE.findall(m["text"])) for m in msgs),
        "has_reply_marker": any(m["has_reply"] for m in msgs),
        "per_user": dict(sorted(per_user.items(), key=lambda kv: -kv[1]["total"])),
        "daily": dict(sorted(daily.items())),
    }


# ---------------------------------------------------------------- 報告

def md_table(rows, headers):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def render_report(res, src_files):
    n = res["n_messages"]
    L = []
    A = L.append

    A(f"# LINE 群組聊天記錄分析報告\n")
    A(f"- **資料期間**：{res['date_from']} ~ {res['date_to']}（{res['n_days']} 個有發文的日期）")
    A(f"- **訊息總數**：{n:,} 則")
    A(f"- **參與者數**：{res['n_users']} 人")
    A(f"- **來源檔案**：{len(src_files)} 個 `{src_files[0] if src_files else '?'}` 格式檔")
    A("")

    A("## 〇、資料限制（請先讀）\n")
    A("| 項目 | 狀態 | 說明 |")
    A("|---|---|---|")
    A(f"| 資料完整性 | {'匯出檔，完整歷史' if src_files else '未知'} | "
      "來自 LINE 官方匯出，涵蓋帳號可見的全部記錄 |")
    A(f"| 回覆關聯 | {'部分可得' if res['has_reply_marker'] else '**不可得**'} | "
      "文字匯出不保留被回覆的原文，只能看到有 `[回覆…]` 標記 |")
    A("| 貼圖內容 | 不可得 | 僅有 `[貼圖]` 佔位，無圖像內容與文字 |")
    A("| 編輯/刪除原文 | 不可得 | 只留下「已刪除了一則訊息」 |")
    A("")
    A("> **本文的統計是觀察，不是對動機、情緒或立場成因的判定。**")
    A("> 本報告不對特定個人做政治傾向、意識形態等敏感屬性推斷；")
    A("> 議題面向的說明僅限於群組整體的話題分布。")
    A("")

    A("## 一、成員發文量\n")
    rows = []
    for who, s in res["per_user"].items():
        rows.append([who, f"{s['total']:,}", f"{s['share_pct']}%",
                     s["active_days"], s["per_active_day"], s["per_calendar_day"]])
    A(md_table(rows, ["成員", "訊息數", "占比", "活躍天數", "日均(活躍日)", "日均(全部日)"]))
    A("")
    if res["n_users"] > 1:
        tot = sum(s["total"] for k, s in res["per_user"].items() if not k.startswith("("))
        top = next(iter(res["per_user"]))
        ts = res["per_user"][top]["total"]
        if tot:
            hhi = sum((s["total"] / tot) ** 2 for k, s in res["per_user"].items() if not k.startswith("("))
            A(f"**集中度（HHI，以訊息占比平方和計）**：{hhi:.3f}"
              f"（{'高度集中' if hhi > 0.25 else '中度集中' if hii > 0.15 else '相當分散'}）；"
              f"發文最多的 **{top}** 佔 {100 * ts / tot:.1f}%。")
    A("")

    A("## 二、發文頻率與訊息長度\n")
    rows = []
    for who, s in res["per_user"].items():
        rows.append([who, s["median_len"] if s["median_len"] is not None else "—",
                     s["p90_len"] if s["p90_len"] is not None else "—",
                     s["peak_hour"] if s["peak_hour"] is not None else "—",
                     s["emoji_total"]])
    A(md_table(rows, ["成員", "訊息長度中位數", "P90 長度", "最活躍時段", "emoji 數"]))
    A("")
    A("> 長度用中位數而非平均，避免單一長文扭曲。P90 用來看『最長的那一成』有多長。")
    A("")

    A("## 三、群組活躍時段\n")
    hh = res["hour_hist"]
    peak = res["peak_hour"]
    rows = []
    for band, rng in [("凌晨 00–05", range(0, 6)), ("上午 06–11", range(6, 12)),
                      ("下午 12–17", range(12, 18)), ("晚上 18–23", range(18, 24))]:
        c = sum(hh[str(h)] for h in rng)
        rows.append([band, f"{c:,}", f"{100 * c / n:.1f}%" if n else "-"])
    A(md_table(rows, ["時段", "訊息數", "占比"]))
    A("")
    A(f"**尖峰小時**：{peak} 時（{hh[str(peak)]:,} 則）" if peak is not None else "")
    A("")
    A("```mermaid")
    A("xychart-beta")
    A('    title "每日訊息量"')
    A('    x-axis ["' + '", "'.join(list(res["daily"])[:20]) + '"]')
    A('    y-axis "訊息數" ' + str(max(res["daily"].values()) if res["daily"] else 1))
    A('    bar [' + ", ".join(str(res["daily"][d]) for d in list(res["daily"])[:20]) + ']')
    A("```")
    A("")

    A("## 四、話題分布（觀察）\n")
    if res["topics"]:
        rows = [[t, f"{c:,}", f"{100 * c / sum(res['topics'].values()):.1f}%"]
                for t, c in res["topics"].items()]
        A(md_table(rows, ["話題", "訊息數", "占比"]))
        A("")
        A("```mermaid")
        A("pie title 話題分布")
        for t, c in res["topics"].items():
            A(f'    "{t}" : {c}')
        A("```")
    else:
        A("_無可分類的純文字訊息。_")
    A("")

    A("## 五、推測（僅供參考，非結論）\n")
    A("以下是從上述數據延伸出的**可能**解釋，與前述觀察分開陳述，未經驗證：")
    A("")
    A("- 若某成員的訊息長度中位數遠低於群組平均，可能偏向**快速回應型**互動（刷串、接龍、表情符號回覆）。")
    A("- 若 emoji 數集中在少數成員，可能是群組的主要「情緒表達管道」。")
    A("- 尖峰時段若落在非工作時間，代表互動較可能發生於休息時段。")
    A("")
    A("以上皆為替代解釋之一，需更多資料才能排除其他可能。")
    A("")
    return "\n".join(x for x in L if x is not None)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="匯出資料夾")
    ap.add_argument("--out", default="./output")
    a = ap.parse_args()

    msgs, files = parse_folder(a.input)
    res = analyze(msgs)
    res["source_files"] = files

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "daily.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "messages"])
        for d, c in res["daily"].items():
            w.writerow([d, c])

    rep = render_report(res, files)
    # 明確用 newline="\n"：Windows 預設會轉成 CRLF，違反 repo 的 .gitattributes
    with open(os.path.join(a.out, "report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(rep)
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    print(f"[OK] 解析 {res['n_messages']} 則訊息 / {res['n_users']} 人 / {res['n_days']} 天")
    print(f"[->] {os.path.join(a.out, 'report.md')}")
    print(f"[->] {os.path.join(a.out, 'summary.json')}")
    print(f"[->] {os.path.join(a.out, 'daily.csv')}")
    if not res["has_reply_marker"]:
        print("[注意] 未偵測到回覆標記 — 文字匯出不保留回覆關聯，此指標不可得。")


if __name__ == "__main__":
    main()