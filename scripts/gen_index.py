#!/usr/bin/env python3
"""Regenerate the README.md and SKILLS.md indexes in this repository.

Scans every ``<skill>/SKILL.md`` for its frontmatter and rewrites the generated
regions of README.md and SKILLS.md.

Usage:
    python3 scripts/gen_index.py            regenerate the indexes in place
    python3 scripts/gen_index.py --check    report problems, write nothing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
SKILLS = REPO / "SKILLS.md"

CATEGORIES: list[tuple[str, str]] = [
    ("engineering", "工程模擬與 CAD"),
    ("documents", "文件與會議紀錄"),
    ("exams", "考試與解題"),
    ("media", "影音下載、處理與分析"),
    ("automation", "瀏覽器與桌面自動化"),
    ("business", "辦公、求職與商務"),
    ("development", "開發工具與 Skill 管理"),
    ("graphics", "圖像生成與桌寵"),
]

MEMBERSHIP: dict[str, str] = {
    "dwg-to-dxf": "engineering",
    "sd-webui-vae-fix": "engineering",
    "docx-edit": "documents",
    "news-weekly-docx-move": "documents",
    "image-to-pdf": "documents",
    "md-to-pdf": "documents",
    "meeting-transcript-summary": "documents",
    "zh-text-polish": "documents",
    "line-group-export-analysis": "documents",
    "pdf-reader": "documents",
    "pptx": "documents",
    "xlsx": "documents",
    "exam-report": "exams",
    "on24-video-download": "media",
    "takeout-exif-merge": "media",
    "tts": "media",
    "twii-excel-fill": "media",
    "video-analysis": "media",
    "yt-batch-download": "media",
    "yt-upload": "media",
    "browser-control": "automation",
    "browser-site-guides": "automation",
    "browser-stack-routing": "automation",
    "opencode-browser": "automation",
    "open-computer-use": "automation",
    "web-tools": "automation",
    "cv-job-application": "business",
    "micron-job-search": "business",
    "resume-cloudflare-maintenance": "business",
    "taobao-cost": "business",
    "yd7148-portfolio-deploy": "business",
    "opencode-env": "development",
    "github-skill-sync": "development",
    "py-binary-deps": "development",
    "opencode-session-auto-name": "development",
    "opencode-usage": "development",
    "network-port-check": "development",
    "mac-disk-cleanup": "development",
    "cloudflare-platform": "development",
    "astro-dev": "development",
    "mate-engine": "graphics",
    "comfyui-qwen-image-edit": "graphics",
    "mate-engine-anim-patch": "graphics",
}

NOT_INSTALLED: dict[str, str] = {
}

DEPENDENCY: dict[str, str] = {
    "astro-dev": "純知識（來源 opencodeskills.dev）",
    "browser-control": "瀏覽器自動化：browser-control CLI / MCP、ffmpeg",
    "browser-site-guides": "瀏覽器自動化：browser-control CLI（擴充須自備，無額外安裝）",
    "browser-stack-routing": "瀏覽器自動化：bsk CLI、browser-control MCP、opencode-browser 外掛（三軌擇一）",
    "cloudflare-platform": "雲端服務：wrangler / Cloudflare 帳號",
    "cv-job-application": "瀏覽器自動化：Playwright CDP、ddddocr、EasyOCR、pymupdf",
    "dwg-to-dxf": "額外系統工具：ODA File Converter、Python ezdxf",
    "exam-report": "重型機器學習：venv（pymupdf、EasyOCR、Qwen2.5-VL、ngspice）",
    "github-skill-sync": "無額外依賴（git / rsync / ssh）",
    "docx-edit": "純 Python：python-docx、pywin32（需 MS Word COM）",
    "news-weekly-docx-move": "無額外依賴（PowerShell + 網路分享）",
    "image-to-pdf": "純 Python：Pillow",
    "mate-engine": "額外系統工具：dnfile / dncil / UnityPy（動畫擴充）",
    "mate-engine-anim-patch": "額外系統工具：dnfile / dncil / UnityPy",
    "md-to-pdf": "純 Python：Pillow（中文字體自動偵測）",
    "mac-disk-cleanup": "無額外依賴（macOS 內建 du / df / rm）",
    "meeting-transcript-summary": "無額外依賴（opencode 內建工具）",
    "zh-text-polish": "無額外依賴（opencode 內建工具）",
    "micron-job-search": "瀏覽器自動化：Playwright、Pillow",
    "network-port-check": "無額外依賴（macOS 需 curl / nc / dig / openssl / swiftc）",
    "on24-video-download": "額外系統工具：curl、ffmpeg、Pillow、RapidOCR",
    "open-computer-use": "npm 套件：open-computer-use（macOS 14+ 需授權）",
    "opencode-browser": "瀏覽器自動化：OpenCode 外掛 @different-ai/opencode-browser + Node.js",
    "opencode-session-auto-name": "npm 套件：opencode-auto-name（0 Token）",
    "opencode-usage": "純 Python：標準庫（跨平台）",
    "pdf-reader": "重型機器學習：venv（PyMuPDF、RapidOCR、opencc）",
    "pptx": "npm 套件／純 Python：pptxgenjs、python-pptx",
    "py-binary-deps": "無額外依賴（Python + pip / uv；ffmpeg 需於 PATH）",
    "resume-cloudflare-maintenance": "無額外依賴（純 git / wrangler 流程）",
    "sd-webui-vae-fix": "WebUI 環境：webui 內建 Python（torch + safetensors）",
    "takeout-exif-merge": "額外系統工具：ExifTool",
    "taobao-cost": "純 Python：openpyxl",
    "tts": "純 Python：edge-tts（+ ffmpeg）",
    "twii-excel-fill": "純 Python：openpyxl",
    "video-analysis": "重型機器學習：venv（whisper、RapidOCR、PyMuPDF、opencc）、ffmpeg、yt-dlp",
    "web-tools": "瀏覽器自動化：Crawl4AI venv、Playwright（Firefox）",
    "xlsx": "npm 套件／純 Python：exceljs、openpyxl",
    "yd7148-portfolio-deploy": "雲端服務：Node、GitHub Pages、Cloudflare",
    "yt-batch-download": "額外系統工具：yt-dlp、browser_cookie3、ffmpeg、deno",
    "yt-upload": "瀏覽器自動化：Playwright",
    "comfyui-qwen-image-edit": "額外系統工具：ComfyUI + Qwen-Image-2.1 模型、/prompt API",
}

DEPENDENCY_GROUPS: list[tuple[str, str]] = [
    ("無額外依賴", "無額外依賴"),
    ("純 Python", "純 Python（跨平台）"),
    ("重型機器學習", "重型機器學習（各 skill 專用 venv）"),
    ("額外系統工具", "需額外系統工具"),
    ("npm 套件", "需 npm 套件"),
    ("瀏覽器自動化", "瀏覽器自動化"),
    ("COMSOL 環境", "需 COMSOL 環境"),
    ("<CORP_MAIL_SYSTEM> 環境", "需 <CORP_MAIL_SYSTEM> 環境"),
    ("WebUI 環境", "需 WebUI 環境"),
    ("雲端服務", "需雲端服務"),
]

PLATFORM_MARKS = {
    "cv-job-application": "🪟",
    "docx-edit": "🪟",
    "dwg-to-dxf": "🪟",
    "news-weekly-docx-move": "🪟",
    "exam-report": "🪟",
    "mate-engine-anim-patch": "🪟",
    "sd-webui-vae-fix": "🪟",
    "yd7148-portfolio-deploy": "🪟",
}

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
LINKED_SKILL = re.compile(r"\]\(([a-z0-9][a-z0-9-]*)/SKILL\.md\)")
SKILL_HEADING = re.compile(r"^##\s+(?:\d+\.\s*)?([a-z0-9][a-z0-9-]*)\s*$")

TOP_RESERVED = {"分類總覽", "Skill 詳細說明"}


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    fields: dict[str, str] = {}
    if not match:
        return fields
    key = None
    for line in match.group(1).splitlines():
        if re.match(r"^[a-zA-Z_][\w-]*:", line):
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip().strip("'\"")
        elif key and line.startswith((" ", "\t")) and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def first_sentence(text: str, limit: int = 110) -> str:
    flat = " ".join(text.split())
    parts = re.split(r"(?<=[。；;.!?])\s", flat, maxsplit=1)
    out = parts[0] if parts else flat
    if len(out) > limit:
        out = out[: limit - 1].rstrip() + "…"
    return out.replace("|", "\\|")


def collect() -> tuple[list[dict], list[str]]:
    skills: list[dict] = []
    problems: list[str] = []
    for child in sorted(REPO.iterdir()):
        if not child.is_dir() or not (child / "SKILL.md").is_file():
            continue
        fields = parse_frontmatter(child / "SKILL.md")
        name = fields.get("name", "")
        description = fields.get("description", "")
        if name != child.name:
            problems.append(f"{child.name}: frontmatter name={name!r} 與資料夾名不符")
        if not description:
            problems.append(f"{child.name}: frontmatter 缺少 description")
        if "license" not in fields:
            problems.append(f"{child.name}: frontmatter 缺少 license")
        if child.name not in MEMBERSHIP:
            problems.append(f"{child.name}: 未分類，請補 scripts/gen_index.py 的 MEMBERSHIP")
        skills.append(
            {
                "dir": child.name,
                "summary": first_sentence(description) if description else "（缺少 description）",
                "category": MEMBERSHIP.get(child.name, "development"),
                "dependency": DEPENDENCY.get(child.name, "未分類"),
                "mark": PLATFORM_MARKS.get(child.name, "🍎"),
                "not_installed": NOT_INSTALLED.get(child.name, ""),
            }
        )
    return skills, problems


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def splice(text: str, start: str, end: str, title: str, body: str, anchor: str, mode: str) -> str:
    if start in text and end in text:
        head, _, rest = text.partition(start)
        _, _, tail = rest.partition(end)
        tail_lines = tail.splitlines()
        while tail_lines and not tail_lines[0].strip():
            del tail_lines[0]
        return "\n".join(head.splitlines() + [start, *body.rstrip().splitlines(), "", end, ""] + tail_lines)
    lines = text.splitlines()
    try:
        first = next(i for i, line in enumerate(lines) if line.startswith(anchor))
    except StopIteration:
        raise SystemExit(f"找不到章節：{anchor}") from None
    block = [title, "", start, *body.rstrip().splitlines(), "", end, ""]
    if mode == "insert-before":
        return "\n".join(lines[:first] + block + lines[first:])
    stop = len(lines)
    for i in range(first + 1, len(lines)):
        if lines[i].startswith("## "):
            stop = i
            break
    return "\n".join(lines[:first] + block + lines[stop:])


def readme_index(skills: list[dict]) -> str:
    out = [
        f"共 **{len(skills)} 個 skill** 資料夾直接放在 Repo 根目錄；下方依功能分成 {len(CATEGORIES)} 類。",
        "",
        "| 分類 | 數量 |",
        "|---|---:|",
    ]
    for slug, label in CATEGORIES:
        out.append(f"| {label} | {len([s for s in skills if s['category'] == slug])} |")
    for slug, label in CATEGORIES:
        out += ["", f"### {label}", "", "| Skill | 平台 | 一句話說明 | 依賴／平台 |", "|---|:--:|---|---|"]
        for s in skills:
            if s["category"] != slug:
                continue
            note = f"**〔{s['not_installed']}，本機不安裝〕**" if s["not_installed"] else ""
            out.append(
                f"| [`{s['dir']}`]({s['dir']}/SKILL.md) | {s['mark']} | {s['summary']} {note} | {s['dependency']} |"
            )
    return "\n".join(out)


def readme_deps(skills: list[dict]) -> str:
    out = ["依賴資訊由 `scripts/gen_index.py` 的 `DEPENDENCY` 對照表產生，維護時請改該表。", "", "| 類型 | Skill |", "|---|---|"]
    claimed: set[str] = set()
    for prefix, label in DEPENDENCY_GROUPS:
        members = [s["dir"] for s in skills if s["dependency"].startswith(prefix)]
        claimed |= set(members)
        if members:
            out.append(f"| {label} | " + "、".join(f"`{m}`" for m in members) + " |")
    rest = [s["dir"] for s in skills if s["dir"] not in claimed]
    if rest:
        out.append("| **未分類（需補 DEPENDENCY）** | " + "、".join(f"`{m}`" for m in rest) + " |")
    return "\n".join(out)


def readme_not_installed(skills: list[dict]) -> str:
    out = [
        "下列 skill 保留在 Repo 供參考，但**本機 `~/.config/opencode/skills/` 刻意不安裝**；",
        "`github-skill-sync` 下載時會自動跳過。",
        "",
        "| Skill | 類別 | 原因 |",
        "|---|---|---|",
    ]
    for s in skills:
        if s["not_installed"]:
            out.append(f"| [`{s['dir']}`]({s['dir']}/SKILL.md) | {s['not_installed']} | 使用者不使用該軟體 |")
    out += ["", "排除規則見 [`github-skill-sync`](github-skill-sync/SKILL.md) 的下載章節。"]
    return "\n".join(out)


def readme_all(skills: list[dict]) -> str:
    out = [f"共 {len(skills)} 個 skill。", "", "| Skill | 平台 | 說明 |", "|---|:--:|---|"]
    for s in skills:
        note = f"〔{s['not_installed']}，本機不安裝〕" if s["not_installed"] else ""
        out.append(f"| [`{s['dir']}`]({s['dir']}/SKILL.md) | {s['mark']} | {s['summary']} {note} |")
    return "\n".join(out)


def skills_overview(skills: list[dict]) -> str:
    order = {slug: i for i, (slug, _) in enumerate(CATEGORIES)}
    out = ["| # | Skill | 一句話說明 |", "|---:|---|---|"]
    for i, s in enumerate(sorted(skills, key=lambda x: (order.get(x["category"], 99), x["dir"])), start=1):
        out.append(f"| {i} | [`{s['dir']}`](#{i}-{s['dir']}) | {s['summary']} |")
    return "\n".join(out)


def split_blocks(lines: list[str], names: set[str]) -> tuple[list[str], list[tuple[str, str, list[str]]], list[tuple[str, list[str]]]]:
    marks: list[tuple[int, str, bool]] = []
    for i, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        title = line[3:].strip()
        name = re.sub(r"^\d+\.\s*", "", title).strip()
        if name in names:
            marks.append((i, name, True))
        elif name in TOP_RESERVED or title.startswith("附錄"):
            marks.append((i, title, False))
    if not marks:
        raise SystemExit("SKILLS.md 找不到可解析的章節")
    preamble = lines[: marks[0][0]]
    sections: list[tuple[str, str, list[str]]] = []
    for idx, (line_no, name, is_skill) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(lines)
        kind = "skill" if is_skill else ("appendix" if name.startswith("附錄") else "top")
        sections.append((kind, name, lines[line_no:end]))
    return preamble, sections, []


def rebuild_skills_md(text: str, skills: list[dict]) -> tuple[str, list[str]]:
    names = {s["dir"] for s in skills}
    lines = text.splitlines()
    preamble, sections, _ = split_blocks(lines, names)
    notes: list[str] = []
    top: list[list[str]] = []
    appendix: list[list[str]] = []
    ordered: list[str] = []
    bodies: dict[str, list[str]] = {}

    for kind, name, block in sections:
        if kind == "top":
            if name == "Skill 詳細說明":
                continue
            top.append(block)
        elif kind == "appendix":
            appendix.append(block)
        elif name in bodies:
            notes.append(f"丟棄重複章節：{name}（{len(block)} 行，前已有完整內容）")
        else:
            bodies[name] = block
            ordered.append(name)

    category_of = {s["dir"]: s["category"] for s in skills}
    rank = {slug: i for i, (slug, _) in enumerate(CATEGORIES)}
    table_order = sorted(skills, key=lambda x: (rank.get(x["category"], 99), x["dir"]))
    number_of = {s["dir"]: i for i, s in enumerate(table_order, start=1)}
    ordered.sort(key=lambda n: number_of[n])
    absent = [s["dir"] for s in table_order if s["dir"] not in bodies]
    if absent:
        notes.append("尚無詳細說明章節，已自動產生指標章節：" + "、".join(absent))
    summaries = {s["dir"]: s["summary"] for s in skills}
    for name in absent:
        bodies[name] = [f"## {number_of[name]}. {name}", "", f"詳見 [{name}/SKILL.md]({name}/SKILL.md)。", "", f"{summaries[name]}", ""]
        ordered.append(name)
    ordered.sort(key=lambda n: number_of[n])

    detail: list[str] = []
    for name in ordered:
        block = [f"## {number_of[name]}. {name}"] + list(bodies[name][1:])
        while len(block) > 1 and (not block[1].strip() or block[1].strip() == "---"):
            del block[1]
        while len(block) > 1 and (not block[-1].strip() or block[-1].strip() == "---"):
            block.pop()
        detail.append("\n".join(block))

    out = list(preamble)
    for block in top:
        out += block
        out += [""]
    out += ["## Skill 詳細說明", ""]
    out += ["\n\n---\n\n".join(detail)]
    for block in appendix:
        out += ["", "---", ""] + block
    return "\n".join(out), notes


def replace_overview(text: str, skills: list[dict]) -> str:
    head, marker, tail = text.partition("### 全部 skills 一覽")
    if not marker:
        return text
    body = re.split(r"^## ", tail, maxsplit=1, flags=re.M)
    table = skills_overview(skills)
    rest = ("## " + body[1]) if len(body) > 1 else ""
    return head + marker + "\n\n" + table + "\n\n" + rest


def broken_links(text: str, names: set[str], label: str) -> list[str]:
    return [f"{label}: 連結指向不存在的目錄 {n}/" for n in sorted(set(LINKED_SKILL.findall(text)) - names)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate README.md and SKILLS.md indexes")
    parser.add_argument("--check", action="store_true", help="只檢查不寫入")
    args = parser.parse_args()

    skills, problems = collect()
    names = {s["dir"] for s in skills}

    readme_text = read(README)
    skills_text = read(SKILLS)

    rebuilt_skills, notes = rebuild_skills_md(skills_text, skills)
    rebuilt_skills = replace_overview(rebuilt_skills, skills)
    rebuilt_skills = re.sub(r"目前收錄 \*\*\d+ 個 skills\*\*", f"目前收錄 **{len(skills)} 個 skills**", rebuilt_skills)

    rebuilt_readme = readme_text
    rebuilt_readme = splice(
        rebuilt_readme, "<!-- gen:readme-index:start -->", "<!-- gen:readme-index:end -->",
        "## 功能分類", readme_index(skills), "## 功能分類", "replace",
    )
    rebuilt_readme = splice(
        rebuilt_readme, "<!-- gen:readme-deps:start -->", "<!-- gen:readme-deps:end -->",
        "## 依賴／平台總覽", readme_deps(skills), "## 依賴／平台總覽", "replace",
    )
    rebuilt_readme = splice(
        rebuilt_readme, "<!-- gen:readme-not-installed:start -->", "<!-- gen:readme-not-installed:end -->",
        "## 預設不安裝（本機刻意排除）", readme_not_installed(skills), "## 安裝", "insert-before",
    )
    rebuilt_readme = splice(
        rebuilt_readme, "<!-- gen:readme-all:start -->", "<!-- gen:readme-all:end -->",
        f"## Skill 一覽（共 {len(skills)} 個）", readme_all(skills), "## Skill 一覽", "replace",
    )
    rebuilt_readme = re.sub(
        r"所有 \d+ 個 skill 資料夾直接放在 Repo 根目錄；下方依功能分成 \d+ 類，可直接點選。",
        "", rebuilt_readme,
    )
    # 同步所有 "## Skill 分類索引（N 個）" 這類標題裡的計數。
    # 這行標題位於 gen:readme-all 自動區塊之外，不同步就會與區塊內的實際數字矛盾
    # （曾發生：標題 35、區塊 36）。
    rebuilt_readme = re.sub(
        r"(##\s*Skill\s*(?:一覽|分類索引)（(?:共\s*)?)\d+(\s*個）)",
        rf"\g<1>{len(skills)}\g<2>",
        rebuilt_readme,
    )

    problems += broken_links(rebuilt_readme, names, "README.md")
    problems += broken_links(rebuilt_skills, names, "SKILLS.md")

    def normalized(text: str) -> str:
        return text if text.endswith("\n") else text + "\n"

    changed = [
        path.name
        for path, new in ((README, rebuilt_readme), (SKILLS, rebuilt_skills))
        if normalized(read(path)) != normalized(new)
    ]

    if args.check:
        for p in problems:
            print(f"problem: {p}")
        for c in changed:
            print(f"stale: {c} 需重新產生（python3 scripts/gen_index.py）")
        if not problems and not changed:
            print(f"OK: {len(skills)} 個 skill，索引與連結一致")
        return 1 if problems or changed else 0

    for note in notes:
        print(f"note: {note}")
    write(README, rebuilt_readme)
    write(SKILLS, rebuilt_skills)
    print("updated: " + ", ".join(changed) if changed else "索引已是最新")
    for p in problems:
        print(f"problem: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
