---
name: docx-edit
description: Use when the user asks to read, edit, convert, extract from, or generate Word .docx files (新增/修改/取代 Word 內容、表格欄位、頁首頁尾、追蹤修訂、docx轉md/pdf、週報docx改寫). Covers python-docx 程式化編輯、pywin32 + MS Word COM 高保真自動化、docx 表格結構導覽、與本機 Python 路徑陷阱。

license: MIT
---

# Word .docx 讀寫與編輯

本機已具備完整能力，**不需要再安裝任何東西**。兩條路線各有適用場景。

## 環境現況（已驗證）

| 元件 | 路徑 / 版本 | 用途 |
|---|---|---|
| 真實 Python | `<USERPROFILE>\AppData\Local\Programs\Python\Python313\python.exe` | 必須用這個完整路徑 |
| python-docx | 1.2.0 | 程式化讀寫 docx |
| lxml | 6.1.1 | python-docx 相依 |
| pywin32 | 312 | COM 自動化 |
| MS Word | 16.0 (Office16) | COM 後端，排版最忠實 |
| LibreOffice / pandoc | 未安裝 | 不需要 |

## ⚠️ 陷阱一：PATH 的 python 是空殼（最重要）

`python` 指向 `<USERPROFILE>\AppData\Local\Microsoft\WindowsApps\python.exe`，
是 Microsoft Store 的 **stub**：會**無聲失敗、沒有任何輸出、exit code 1**。

症狀：`pip install` 沒反應、`python script.py` 印不出東西、看起來像腳本壞掉。

**解法：永遠用完整路徑**
```powershell
$py="<USERPROFILE>\AppData\Local\Programs\Python\Python313\python.exe"
& $py script.py
```

## ⚠️ 陷阱二：不要在 Python 原始碼裡寫死中文路徑

透過 shell 傳檔案時，PowerShell 會把中文路徑轉成 CP950 破壞掉，
`glob` 會回傳 0 筆、`PackageNotFoundError` 看起來像「檔案不存在」。

**解法：Python 內用 `glob` 找檔，不要把中文檔名寫進原始碼。**
```python
R = r"<PROJECT_ROOT_A>\Projects\2026-09-news-review\01-REF"
p = sorted(glob.glob(os.path.join(R, "docx", "*.docx")))[-1]
```

## ⚠️ 陷阱三：先複製到暫存區再改

直接改原始檔若中途失敗會留下損壞檔案。實測流程：
```python
import shutil, tempfile, os
work = os.path.join(tempfile.gettempdir(), "edit.docx")
shutil.copy(src, work)
# ... 在 work 上操作，驗證成功後才覆蓋回 src
```

---

## 路線 A：python-docx（日常改文字、快、格式可控）

```python
import docx, glob, os
doc = docx.Document(path)

doc.paragraphs            # 頂層段落
p = doc.add_paragraph("新內容")
p.style = 'Heading 1'     # 內建樣式：Title / Heading 1..9 / Normal / List Bullet
p.add_run("粗體").bold = True

t = doc.tables[0]         # 表格
t.cell(row, col)          # 0-based；回傳 _Cell
t.cell(1, len(t.columns)-1).text = "REPLACED"   # 直接取代整格文字
len(t.rows), len(t.columns)

sec = doc.sections[0]
sec.header.paragraphs[0].text = "頁首"
sec.footer.paragraphs[0].text = "頁碼"

doc.add_picture("chart.png", width=docx.shared.Inches(6))
doc.save(path)
```

**限制（改用 COM）**
- 不支援「追蹤修訂」、內容控制項 (content control)
- 重新開檔後目錄/頁碼欄位不會更新
- 實測：編輯儲存後檔案由 67061 → 60008 bytes，**未使用的樣式/設定會被丟棄**

**已知坑**
- `cell.text = ...` 會**清掉該格所有段落與換行**，變成單一 run
- 合併儲存格 (merged cell) 會讓 `t.cell(r,c)` 的座標與視覺不符，用 `t.rows[r].cells[c]`
- 巢狀表格要用 `cell.tables`，不會出現在 `doc.tables`

## 路線 B：Word COM / pywin32（高保真、需 Word 功能時）

```python
import win32com.client as win32
app = win32.DispatchEx("Word.Application")   # DispatchEx = 獨立 instance
app.Visible = False
app.DisplayAlerts = False
try:
    doc = app.Documents.Open(path, ReadOnly=False)
    doc.Tables.Count
    doc.Tables(1).Rows.Count

    rng = doc.Content
    rng.Find.Text = "解析"
    rng.Find.Execute()          # 取代式搜尋

    c = doc.Tables(1).Cell(2, doc.Tables(1).Columns.Count)   # 1-based
    c.Range.Text = "新內容"

    doc.Fields.Update()         # 更新目錄/頁碼
    doc.TablesOfContents(1).Update()
    doc.SaveAs2("out.pdf", FileFormat=17)   # 17 = wdFormatPDF
    doc.Save()
    doc.Close(SaveChanges=0)
finally:
    app.Quit()                  # 務必在 finally，否則殘留 WINWORD.EXE
```

**實測結果：COM 存檔後 67061 bytes，與原檔完全相同 → 排版 100% 保留。**

**注意事項**
- `doc.Tables(i)` / `Cell(r,c)` / `Documents.Open` **全部 1-based**（與 python-docx 相反）
- 務必 `try/finally: app.Quit()`；也要確認沒有殘留 `WINWORD.EXE`
- `DisplayAlerts = False` 避免「存檔嗎」對話框卡住
- 開檔前先 `shutil.copy` 到暫存區

## 路線 C：純 XML（無相依套件、可精細控制）

docx 就是 zip + XML，不裝套件也能讀寫：
```python
import zipfile, xml.etree.ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(path) as z:
    root = ET.fromstring(z.read('word/document.xml'))
text = ''.join(n.text for n in root.iter(W+'t') if n.text)

for tbl in root.iter(W+'tbl'):
    for tr in tbl.findall(W+'tr'):
        for tc in tr.findall(W+'tc'):
            for p in tc.findall(W+'p'):
                s = ''.join(n.text for n in p.iter(W+'t') if n.text)
```
用法：`w:t`=文字、`w:tab`=`\t`、`w:br`/`w:cr`=換行、`w:p`=段落、`w:tc`=`w:tc`=儲存格。
適合「只抽文字不做格式」或 python-docx 壞掉時的後路。

---

## docx 表格結構怎麼看

`.docx` 內部：`word/document.xml`（內文）、`styles.xml`、`numbering.xml`、
`settings.xml`、`header*.xml` / `footer*.xml`。

**這批 SiC 週報的實測結構**（重要）：
- 內文全部包在 `w:tbl` 表格裡，**不是** `w:body/w:p` 頂層段落
  → 只用 `doc.paragraphs` 會拿到 1 段空白；必須 `doc.tables`
- 欄位：`項次 | 案號(技術資料編號) | 研開項目 | 負責人 | 工作日期(立案日期/預完日) | 執行結果及說明`
- 新聞內容在**最後一欄「執行結果及說明」**
- **表格會跨頁**：Word 會重複表頭列 (`w:tblHeader`)，且把句子**從中間截斷**成不同 `w:tr`
  （例如「…並計畫採」在一頁、「用結合SiC…」在下一頁）
  → 抽取時必須依結尾標點把斷句接回，否則文字破碎
- 同一份檔案可能有多個表格（進度追蹤表：序號/案號/題目/負責人/起案/進度/摘要），
  靠「該列是否含目標項目名」來篩選，不要無腦取最後一欄
- 判斷表頭列：該 `w:tr` 同時含 `執行結果及說明` 與 `研開項目`/`題目`/`案號`/`項次`

已驗證可用的抽取流程見 `scripts/extract_news_column.py`（從跨頁表格還原新聞＋解析）。

## 選哪一條

| 需求 | 用 |
|---|---|
| 改文字、填欄位、抽內容出 markdown | **python-docx** |
| 要保留原排版、更新目錄/頁碼、匯出 PDF、追蹤修訂 | **Word COM** |
| 只抽純文字、套件壞掉 | **zipfile + XML** |
| 大批檔案轉檔 | python-docx 讀 + 純檔案操作寫 |
