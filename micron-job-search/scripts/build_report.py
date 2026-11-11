"""Build a Traditional-Chinese Markdown analysis report from micron_final.json.

Includes: summary tables, Mermaid pie/xychart/flowchart, per-category job tables
with Req ID + direct apply links, keyword frequency (resume ATS prep), and the
official Micron resume-format rules.

Usage:
  python build_report.py --final micron_final.json --md "E:\\path\\report.md"
"""
import argparse, collections, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")

CATS = ["工程師", "AI/數據/資訊/自動化", "管理師/專案管理", "廠務/安全/設施", "品質/可靠度", "採購/供應鏈"]
CATDESC = {
    "工程師": "製程 / 設備 / 製程整合(PI) / 測試 / 材料",
    "AI/數據/資訊/自動化": "資料科學、AI、資訊、工業智慧製造、自動化",
    "管理師/專案管理": "主管、專案經理、規劃、跨部門溝通",
    "廠務/安全/設施": "廠務、工業安全、公用設施、維修",
    "品質/可靠度": "品質工程、可靠度、品質系統",
    "採購/供應鏈": "採購、供應商管理、物流、供應鏈",
}
STOPW = {"THE", "AND", "WITH", "FOR", "WILL", "HAVE", "THAT", "THIS", "FROM", "ARE", "YOU", "OUR",
         "ABILITY", "EXPERIENCE", "WORKING", "KNOWLEDGE", "SKILLS", "ABLE", "STRONG", "EXCELLENT",
         "MUST", "WITHIN", "WHICH", "ABOUT", "USING", "THROUGH", "INTO", "YOUR", "ALL", "MORE",
         "THAN", "SUCH", "OTHER", "INCLUDING", "GOOD", "NEW", "USE", "BASED", "CANDIDATE",
         "SUCCESSFUL", "POSITION", "ROLE", "TEAM", "TEAMS", "YEARS", "YEAR", "REQUIRED",
         "REQUIREMENTS", "QUALIFICATIONS", "DEGREE", "PREFERRED", "OR", "AN", "AS", "AT", "ON",
         "IN", "TO", "OF", "IS", "BE", "WE", "A", "I"}


def lvl(t):
    u = t.upper()
    for k in ["DIRECTOR", "SR. MANAGER", "SR MANAGER", "SENIOR MANAGER", "SR. DIRECTOR", "PRODUCTION 2"]:
        if k in u: return "Director/Manager"
    for k in ["STAFF", "SR/STAFF", "SENIOR/STAFF", "SR. ", "SR ", "SENIOR ", "PRINCIPAL", "MANAGER"]:
        if k in u: return "Senior/Staff"
    return "Engineer/IC"


def kfreq(rs, n=28):
    c = collections.Counter()
    for r in rs:
        for q in r["quals"] + r["edu"]:
            for w in re.findall(r"[A-Za-z][A-Za-z/+#\-]{3,}", q):
                c[w.upper()] += 1
    return [(k, v) for k, v in c.most_common(300) if k not in STOPW and v >= 4][:n]


def esc(s):
    return re.sub(r"\s+", " ", str(s)).replace("|", "\\|")


def build(recs, md):
    by = collections.defaultdict(list)
    for r in recs:
        by[r["cat"]].append(r)
    for k in by:
        by[k].sort(key=lambda r: (r["posted"] != "", r["title"]))
    total = len(recs)

    L = []
    A = L.append
    A("# Micron Technology 台中廠 — 目標職類深度分析報告")
    A("")
    A("- **求職目標職類**：工程師、AI/數據/資訊/自動化、管理師/專案管理、廠務/安全/設施、品質/可靠度、採購/供應鏈")
    A("- **資料來源**：careers.micron.com（location = Taichung City, Taiwan）")
    A(f"- **符合目標職類之職缺數**：**{total}** 筆（已抓取完整 Job Description 內文）")
    A("")
    A("---")
    A("")
    A("## 一、職缺總覽")
    A("")
    A("| 職類 | 說明 | 職缺數 | 占比 | Director/Mgr | Senior/Staff | Engineer/IC |")
    A("|---|---|---:|---:|---:|---:|---:|")
    for c in CATS:
        rs = by[c]
        if not rs: continue
        lv = collections.Counter(lvl(r["title"]) for r in rs)
        A(f"| **{c}** | {CATDESC[c]} | {len(rs)} | {len(rs)/total*100:.1f}% | "
          f"{lv['Director/Manager']} | {lv['Senior/Staff']} | {lv['Engineer/IC']} |")
    A(f"| **合計** | | **{total}** | 100% | | | |")
    A("")
    A("### 1.1 職類分布圖")
    A("")
    A("```mermaid")
    A("pie showData")
    A(f"    title 目標職類分布 (共 {total} 筆)")
    for c in sorted(CATS, key=lambda k: -len(by[k])):
        if by[c]:
            A(f'    "{c}" : {len(by[c])}')
    A("```")
    A("")
    A("```mermaid")
    A("xychart-beta")
    A('    title "各職類職缺數分布"')
    short = {"工程師": "工程師", "AI/數據/資訊/自動化": "AI/數據", "管理師/專案管理": "管理師",
             "廠務/安全/設施": "廠務/安全", "品質/可靠度": "品質/可靠度", "採購/供應鏈": "採購/供應鏈"}
    keys = [c for c in CATS if by[c]]
    A("    x-axis [" + ", ".join(f'"{short[k]}"' for k in keys) + "]")
    A("    bar [" + ", ".join(str(len(by[k])) for k in keys) + "]")
    A("```")
    A("")
    A("### 1.2 職缺生態系")
    A("")
    A("```mermaid")
    A("flowchart TD")
    A(f'    R["Micron 台中廠<br/>目標職缺 {total} 筆"]')
    for c in CATS:
        if by[c]:
            A(f"    R --> {c}<br/>{len(by[c])} 筆")
    A("```")
    A("")
    A("---")
    A("")
    A("## 二、共通條件分析（履歷關鍵字）")
    A("")
    A("> 關鍵字由各職類 Requirements / Qualifications 內文統計而得，出現越多越受重視，可直接用於履歷描述與 ATS 關鍵字對照。")
    A("")
    for i, c in enumerate(CATS, 1):
        if not by[c]: continue
        kf = kfreq(by[c])
        if not kf: continue
        A(f"### 2.{i} {c} — 高頻關鍵字")
        A("")
        A("| 關鍵字 | 出現次數 |")
        A("|---|---:|")
        for k, v in kf:
            A(f"| {k} | {v} |")
        A("")
    A("### 2.7 學歷要求總覽")
    A("")
    A("| 職類 | 需學士(BS) | 需碩士(MS) | 需博士(PhD) | JD 未載明 |")
    A("|---|---:|---:|---:|---:|")
    for c in CATS:
        if not by[c]: continue
        d = collections.Counter(r["deg"] for r in by[c])
        A(f"| {c} | {d['BS']} | {d['MS']} | {d['PhD']} | {d['N/A']} |")
    A("")
    A("---")
    A("")
    A("## 三、重點職缺清單（含直接申請連結）")
    A("")
    n = 0
    for i, c in enumerate(CATS, 1):
        if not by[c]: continue
        A(f"### 3.{i} {c}（{len(by[c])} 筆）")
        A("")
        A("| # | 職缺標題 | Req ID | 職級 | 學歷 | 經驗 | 發布 | 連結 |")
        A("|---:|---|---|---|---|---|---|---|")
        for r in by[c]:
            n += 1
            yrs = "/".join(str(y) for y in r["yrs"]) if r["yrs"] else "N/A"
            A(f"| {n} | {esc(r['title'])} | {r['jid'] or '—'} | {lvl(r['title'])} | "
              f"{r['deg']} | {yrs} | {r['posted'] or '—'} | [投履歷]({r['url']}) |")
        A("")
    A("---")
    A("")
    A("## 四、重點職缺條件摘要 Top 40")
    A("")
    ranked = sorted(recs, key=lambda r: -(len(r["quals"]) * 2 + len(r["edu"])
                     + (3 if r["deg"] in ("PhD", "MS") else 0)))[:40]
    A("| # | 職缺 | Req ID | 學歷 | 主要條件 |")
    A("|---:|---|---|---|---|")
    for i, r in enumerate(ranked, 1):
        q = "；".join(esc(x)[:70] for x in (r["quals"][:3] or r["edu"][:2]))
        A(f"| {i} | {esc(r['title'])} | {r['jid'] or '—'} | {r['deg']} | {q} |")
    A("")
    A("---")
    A("")
    A("## 五、履歷格式建議（Micron 官方規範）")
    A("")
    A("Micron 官方於 [micron.com/about/careers/mail-fax-help](https://www.micron.com/about/careers/mail-fax-help) 提供明確規範，搭配 Workday / Eightfold AI 的 ATS 解析機制，整理如下。")
    A("")
    A("### 5.1 官方明訂規則（必守）")
    A("")
    A("| 項目 | 官方規範 |")
    A("|---|---|")
    A("| 投遞方式 | **一律線上投遞**，郵寄/傳真履歷不受理 |")
    A("| 姓名 | 姓名必須為履歷第一行 |")
    A("| 聯絡資訊 | 地址、電話、E-mail 緊接姓名下一行 |")
    A("| 頂部裝飾 | 不得使用 Logo 或特殊圖像 |")
    A("| 字級 | 10–14 pt |")
    A("| 字型 | 常用字型，Sans-serif 最佳（Helvetica、Arial）；禁用裝飾字型 |")
    A("| 斜體/底線 | 禁止使用；可用粗體與全大寫做段落標題 |")
    A("| 表格/框線 | 避免水平線、垂直線、表格或多欄版面 |")
    A("| 字距 | 不可壓縮字元或單字間距 |")
    A("| 其他資訊 | 全部置於聯絡資訊下方 |")
    A("")
    A("### 5.2 檔案格式")
    A("")
    A("- 格式 **.docx 或純文字 PDF**；**嚴禁掃描轉影像的 PDF**（ATS 無法解析）。")
    A("- 建議先複製貼上到純文字編輯器檢查，閱讀順序正常即代表 ATS 可正確解析。")
    A("- 檔名建議 `FirstName_LastName_Resume.pdf`。")
    A("")
    A("### 5.3 Workday / Eightfold AI 解析重點")
    A("")
    A("1. **使用標準段落標題**：Work Experience、Education、Skills、Certifications。")
    A("2. **禁用多欄版面、頁首頁尾承載關鍵資訊、表格、圖片**（與 Micron 官方規範一致）。")
    A("3. **鏡射職缺原文關鍵字**：職缺寫 HBM 就寫 HBM，寫 DFT/ATE/MATLAB/Python 就寫在履歷上。")
    A("4. **完整填寫 Workday profile 的選填欄位**（證照、語言、退伍役別），recruiters 常用篩選條件排除未完成 profile 的候選人。")
    A("5. **上傳後檢查自動回填欄位**是否正確，錯誤的日期或職稱會直接影響評分。")
    A("")
    A("### 5.4 AI 使用聲明")
    A("")
    A("> Candidates are encouraged to use AI tools to enhance your resume and/or application materials. However, all information provided must be accurate and reflect the candidate's true skills and experiences. Misuse of AI to fabricate or misrepresent qualifications will result in immediate disqualification.")
    A("")
    A("中文：允許使用 AI 工具協助撰寫，但所有資訊必須真實反映本人能力；虛構或誤導經歷將導致立即取消資格。")
    A("")
    A("### 5.5 履歷建議結構")
    A("")
    A("```")
    A("姓名")
    A("地址｜電話｜E-mail｜LinkedIn")
    A("")
    A("SUMMARY / 專業摘要（3-4 行，針對應徵職缺客製）")
    A("")
    A("SKILLS / 核心技能（關鍵字密集區，方便 ATS 抓取）")
    A("  例：Process Integration, HBM, Yield Analysis, SPC, DOE, Python, SQL,")
    A("      MATLAB, 8D/CAPA, FMEA, Cpk, SEM, CMP, WET etch, SPC/APC")
    A("")
    A("EXPERIENCE / 工作經驗（反向時間，每筆含量化成果）")
    A("  公司｜職稱｜起訖年月")
    A("  • 具體職責（動詞開頭，含設備/製程/系統名稱）")
    A("  • 量化成果（良率提升 X%、成本下降 Y%、稼動率 Z%）")
    A("  • 跨部門協作與規模（幾人團隊、幾億預算、幾座廠）")
    A("")
    A("EDUCATION / 教育背景")
    A("  學校｜科系｜學位｜畢業年份")
    A("")
    A("CERTIFICATIONS / 證照（LEGO Six Sigma, CQE, CPIM, CPSM, CSCP,")
    A("  PMP, ISO/IATF Lead Auditor）")
    A("")
    A("LANGUAGES / 語言（中文、英文）")
    A("```")
    A("")
    A("---")
    A("")
    A("## 六、投遞建議")
    A("")
    A("1. **一職一版**：針對 6 大職類各準備一份重點化履歷，開頭 Summary 對應該職類語言。")
    A("2. **優先關注新開職缺**：報告中「發布」欄為 `X days ago` 者（<30 天）競爭者較少。")
    A("3. **多據點職缺可複用**：標示 `+1 more` 者可同時投其他廠區，增加面試機會。")
    A("4. **MTB / FY28 NCG 系列為新廠計畫**：職缺數多、擴張快，通常對新血較友善。")
    A("5. **Beware**：避免掃描 PDF、避免多欄、避免圖片式技能表，確保 ATS 可解析。")
    A("")
    A("---")
    A("")
    A("> 職缺狀態即時變動，請以表中連結至 careers.micron.com 確認是否仍在招募中。")

    open(md, "w", encoding="utf-8").write("\n".join(L))
    print("written", total, {c: len(by[c]) for c in CATS}, "->", md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", required=True)
    ap.add_argument("--md", required=True)
    a = ap.parse_args()
    build(json.load(open(a.final, encoding="utf-8")), a.md)


main()
