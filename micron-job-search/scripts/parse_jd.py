"""Parse Micron JD text into structured records (category, quals, degree, years, Req ID).

Handles the fact that ~60% of Micron JDs have NO 'Qualifications' heading at all --
requirements live inside Responsibilities or the intro paragraph.

Usage:
  python parse_jd.py --texts micron_texts.json --list micron_tc.json --out micron_final.json
"""
import json, re, sys, argparse, collections

sys.stdout.reconfigure(encoding="utf-8")


def classify(t):
    """Return target category or None. Order matters."""
    u = t.upper()
    if re.search(r"INTERN|SCHOLAR|RECRUITER|UNIVERSITY|CAMPUS", u):
        return None
    if re.search(r"TECHNICIAN|OPERATOR|ASSEMBLER|FAC SITE|MAINTENANCE|APC", u):
        return None
    if re.search(r"MANAGER|DIRECTOR|HEAD OF|LEADER|SUPERVISOR|PLANNER|PMO|SPECIALIST", u):
        return "管理師/專案管理"
    if re.search(r"DATA SCIENTIST|AI |AI\b|MACHINE LEARNING|ANALYT|CPIE|PIE|MODEL|FULL STACK|SOFTWARE|SW |IT |INTELLIGENCE|AUTOMATION", u):
        return "AI/數據/資訊/自動化"
    if re.search(r"SUPPLIER|PROCURMENT|LOGISTIC|SUPPLY|CHAIN|CATEGORY", u):
        return "採購/供應鏈"
    if re.search(r"QUALITY|RELIAB|QUALITY ENGINEER|QMS", u):
        return "品質/可靠度"
    if re.search(r"SAFETY|HEALTH|FACILIT", u):
        return "廠務/安全/設施"
    if re.search(r"ENGINEER|PHYSICIST|METALLURGIST|CHEMIST|TECHNOLOGIST|PHYSICS", u):
        return "工程師"
    return None


QH = re.compile(r"^(minimum|basic|required|essential)?\s*(qualifications|requirements)\s*:?$", re.I)
RH = re.compile(r"^(responsibilities|what you will need|job responsibilities|duties)\s*:?$", re.I)
EH = re.compile(r"^(education|educational requirements)\s*:?$", re.I)
STOP = re.compile(r"^(preferred|nice to have|about micron|to learn|all qualified|micron technology is|"
                  r"ai relevant|what you will need|benefits|salary|equal employment|micron is an|privacy)", re.I)


def sect(lines, head_re, stop_re, limit=10):
    for i, l in enumerate(lines):
        if head_re.match(l) and len(l) < 50:
            out, seen = [], set()
            for x in lines[i + 1:]:
                s = x.strip(" -•\t*●").strip()
                if stop_re.match(s) and len(s) < 70:
                    break
                if len(s) < 12 or s in seen:
                    continue
                seen.add(s)
                out.append(s)
                if len(out) >= limit:
                    break
            return out
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--texts", required=True)
    ap.add_argument("--list", dest="lst", required=True)
    ap.add_argument("--out", default="micron_final.json")
    a = ap.parse_args()

    jobs = json.load(open(a.lst, encoding="utf-8"))
    texts = json.load(open(a.texts, encoding="utf-8"))

    recs = []
    for j in jobs:
        cat = classify(j["title"])
        if not cat:
            continue
        t = texts.get(j["url"], "")
        lines = [l.strip() for l in t.split("\n")]
        q = sect(lines, QH, STOP)
        edu = sect(lines, EH, STOP, 4)
        if len(q) < 3:
            q = (q + sect(lines, RH, STOP, 6))[:6]
        jm = re.search(r"(JR\d{6})", t)
        pm = re.search(r"Posted\s+(\d+\s+\w+\s+ago)", t)
        deg = ("PhD" if re.search(r"Ph\.?D|doctorate", t, re.I)
               else "MS" if re.search(r"\bM\.?S\.?\b|Master", t)
               else "BS" if re.search(r"\bB\.?S\.?\b|Bachelor", t) else "N/A")
        yrs = sorted({int(x) for x in re.findall(r"(\d+)\+?\s*years", t, re.I)})
        recs.append({**j, "cat": cat, "quals": q, "edu": edu,
                     "jid": jm.group(1) if jm else "",
                     "posted": pm.group(1) if pm else "",
                     "deg": deg, "yrs": yrs[:3]})

    json.dump(recs, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("records", len(recs), "with quals", sum(1 for r in recs if r["quals"]),
          "with ReqID", sum(1 for r in recs if r["jid"]))
    print(collections.Counter(r["cat"] for r in recs))
    print(collections.Counter(r["deg"] for r in recs))


main()
