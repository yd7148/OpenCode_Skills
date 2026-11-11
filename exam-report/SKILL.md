---
name: exam-report
description: Use when the user needs to process 國營事業 / 台電 / 中油 / 中水 / 台糖 recruitment exam PDFs. Covers extracting and cropping individual questions into images (pdf-exam-extractor), OCR-recognising them, solving exam problems (電路學, 電子學, 基本電學), scraping official answer keys, and generating a complete detailed Traditional-Chinese answer report with Markdown tables, circuit-diagram solutions from VLM component extraction plus SPICE simulation, and 113/114 two-year naming plus GitHub sync. Trigger on "考題 PDF", "國營事業考題", "台電考題", "匯總會議/考題", "整份考題詳細解答", "電路學題目", "答案 PDF", "答案對照".
license: MIT
---

# Taipower Exam Report

## 路徑須知

本 skill 內的絕對路徑來自**撰寫時的機器**，在其他機器上不一定存在。執行前請：

- **skills 目錄**以 `~/.config/opencode/skills/` 為準（PowerShell 用 `Join-Path $env:USERPROFILE ".config\opencode\skills"` 推導），不要假設是 `<PROJECT_ROOT_A>\.opencode\skills\` 或任何特定磁碟機。
- **專案／輸出／暫存路徑**先確認存在；找不到就問使用者實際路徑，不要自行猜測或建立。
- 本 skill（包含 `references/`）出現的 `<PROJECT_ROOT_C>` 等前綴屬**操作紀錄範例**，不是可依賴的事實。

End-to-end workflow: OCR-extracted exam questions → (for circuit diagrams) Qwen2.5-VL-7B component extraction → SP topologies back-inferred from values + official answer → ngspice/PySpice simulation → verdict (PASS/REVIEW/SIM-ERR) → merge with per-question authoritative content into a complete detailed-answer markdown report.

## Year Pair (113 / 114 電機)

| Item | 114 annual (114-2025) | 113 annual (113-2024) |
|---|---|---|
| Source PDF | `test-pdf/114-2025/電機/*.pdf` | `test-pdf/113-2024/電機/113年度新進職員甄試試題科目A_電機_電路學、電子學.pdf` |
| Answer PDF | 官方解答 PDF (question text + options inline) | `113年度新進職員甄試試題解答A_電機_電路學、電子學.pdf` — **authoritative** (題目+選項+[X] 答案全部內嵌) |
| Extraction dir | `提取結果_v4/` | `提取結果_v113/` |
| Official key | hardcoded in pipeline | `answers_113.json` + `q01.md..q50.md` headers |
| VLM pipeline | `vlm_auto_pipeline.py` | `vlm_auto_pipeline_113.py` |
| Report builder | `build_full_exam.py` | `build_full_exam_113.py` |
| Verifier | — (none for 114) | `verify_full_exam_113.py` → `驗證結果- 113 年...md` |
| Circuit Qs | 16 | **19**: `[4,5,6,9,10,12,17,18,21,22,23,28,31,36,38,40,42,45,50]` (scan `q??.md` for 「右圖」) |

## Directory Layout

```
test-pdf/<YY>-<year>/電機/提取結果_v<YY>/      (YY=113 or 114)
  q01.png ... q50.png      # per-question cropped images (full-width rows, ZOOM=2, includes right-side diagram)
  q01.md  ... q50.md       # per-question OCR text / authoritative parsed content
  answers_113.json         # 113 official answer key (exclusive to 113 dir)
  完整解答.md               # old OCR merge — UNRELIABLE: 113 version has 9 wrong answer headers
  exam_pageN.png / answer_pageN.png
```

## Key Scripts (project root <PROJECT_ROOT_C>\2026-08-Taipower-test)

- `vlm_auto_pipeline.py` (114) / `vlm_auto_pipeline_113.py` (113) — VLM auto pipeline: image → components → SP back-inference → SPICE → verdict.
  - 113 copy is generated from 114 by swapping `IMAGE_BASE`, `CIRCUIT_QUESTIONS`, `ANSWER_LETTERS` (=`answers_113.json`), `ANSWER_VALUES` (Q4/Q9/Q17/Q21/Q22), and report path `vlm_auto_report_113.json`.
  - `ANSWER_LETTERS` / `ANSWER_VALUES` hold the official key.
  - `resistor_sp.py` back-inference is wired in via `_back_infer`.
  - VLM = `Qwen2_5_VLForConditionalGeneration` (NOT AutoModelForVision2Seq), `max_new_tokens=900, do_sample=False`, image resized to 600px width, device_map='cuda:0'.
- `resistor_sp.py` — brute-force series/parallel topology search using `Fraction`; `test_sp.py` validates it (all pass).
- `build_full_exam.py` (114) / `build_full_exam_113.py` (113) — merge *all 50 questions* (題目/選項/實際答案/解題過程 + VLM verdict for circuit Qs).
  - 113 builder reads q??.md headers as authoritative answers and embeds freshly-written `SOLUTIONS` dict; it does **not** trust the old 完整解答.md.
  - Output: **`完整詳細解答- <YY> 年經濟部所屬事業機構新進職員甄試試題.md`**.
- `verify_full_exam_113.py` — parses the generated report and checks every question: 題目/選項/實際答案/解題過程 present AND header answer == `answers_113.json`. Writes **`驗證結果- 113 年...md`** (separate file per user request).
- `exam_agent.py` — main solver agent (SymPy/MNA/PySpice triple verification).

## 113-Specific Lessons (9 previously-mistaken answers)

Old 完整解答.md headers contradicted official key on Q3/Q4/Q11/Q21/Q22/Q24/Q28/Q33/Q34 and sometimes rewrote correct math to force the wrong option. Correct as of the official key:
- Q3 = B (4A): R=ρL/A=2Ω, I=8/2=4A. (old forced C)
- Q4 = A (0A): balanced Wheatstone bridge 4/8 = 5/10 → I=0.
- Q11 = A: numerator is `15S²+56S+47`, Heaviside residues → 3e⁻ᵗ+5e⁻²ᵗ+7e⁻³ᵗ.
- Q21 = B (1+√3), Q22 = A (1.5Ω), Q24 = D (6Hz: f0=1/(2π√(LC))), Q33 = D (12.5Ω), Q34 = D (15.7V Vp-p).
- Q28 = official composite **A、C** (複選/送分) — report IC=1.96mA (C) then note both accepted.
- Always regenerate solutions from the official answer PDF text, never reuse old 完整解答.md conclusions verbatim.

## Environment Gotchas (Windows)

- Output: wrap with `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')` before printing Chinese/emoji.
- Import torch BEFORE HF/PySpice imports; set `KMP_DUPLICATE_LIB_OK='TRUE'` first.
- PySpice: `os.add_dll_directory(r'C:\ngspice\Spice64_dll\dll-vs')` + `r'C:\ngspice\Spice64\bin'`.
- **Never** call `ngspice -b x.cir` directly — it hangs after ~60s; always use PySpice `circuit.simulator()` (the `CircuitSimulator(circ)` class is deprecated, no `.SIMULATOR` attr).
- Branch keys are prefixed, e.g. source `V1` → branch `vv1`; use `str(key).endswith('v1')` to find it.
- Full-width punctuation: regex against report must use `（`/`）` not `(`/`)`.

## Report Naming Convention

`.md` files on GitHub must follow: `<short description>- <NN> 年經濟部所屬事業機構新進職員甄試試題.md`
(e.g. `完整詳細解答- 114 年經濟部所屬事業機構新進職員甄試試題.md`, `完整詳細解答- 113 年經濟部所屬事業機構新進職員甄試試題.md`).

## GitHub Sync

- `.gitignore` excludes `models/` (15GB Qwen weights — never commit), `__pycache__/`.
- Remote: `https://github.com/yd7148/TaipowerExam.git`
- Commit scope: scripts + `vlm_auto_report*.json` + `完整詳細解答-...md` + `驗證結果-...md` + `.opencode/skills/taipower-exam-report/SKILL.md`. Files under `test-pdf/.../提取結果_v*/q*.png` are large; keep them out of commits unless asked.

## Ongoing Limits (known)

- VLM topology reading is unreliable → most questions land in `REVIEW`/`NO-CIRCUIT` by design; only accept as PASS when SPICE matches official answer.
- 113 crops are short full-width rows; Q21/Q22 (infinite-ladder / small diagrams) come back NO-CIRCUIT — fine, that's a documented verdict not a failure.
- Not yet implemented: BJT models, zener model, AC phasor sim, multi-valued unlabeled questions.

---

## 整併子功能索引（本 skill 由多個舊 skill 合併）

| 子功能 | 詳細內容 | 觸發情境 |
|---|---|---|
| 考題切圖與 OCR | `reference/pdf-exam-extractor.md` | PDF→影像、題目邊界偵測、裁切、EasyOCR |
| 解題與答案查詢 | `reference/taipower-exam-solver.md` | pymupdf 抽題、解題、官方答案 PDF 抓取 |
| 完整解答報告產出 | `（本文件主體）` | VLM 元件萃取 + SPICE + 答案比對 → Markdown 報告，113/114 雙年支援 |

> 讀取子功能時請先 Read 對應的 reference 檔案，內容為原 skill 完整說明。
