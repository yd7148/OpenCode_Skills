---
name: news-weekly-docx-move
description: Use when the user asks to bulk-move, copy, collect, or sync the weekly news review .docx files (個人週報 新聞(OK).docx) from the SiC project network share (\\<CORP_SERVER_IP>\03_SiC專案\SiC立案資料\個人週報) into a local review folder such as <PROJECT_ROOT_A>\Projects\<YYYY-MM>-news-review. Covers recursive wildcard discovery, Move-Item -Force, moving the already-hand-copied demo file too, and the count/integrity verification pass.

license: MIT
---

# 個人週報「新聞(OK).docx」批次搬移

把 SiC 專案網路分享上「個人週報」底下**所有** `*新聞(OK).docx` 移到本機的每月審閱資料夾。
一次實測（2026-09-28）搬 62 個檔案（2025年6月 ~ 2026年9月第三週），0 失敗。

## 固定路徑

- 來源（遞迴根目錄）：`\\<CORP_SERVER_IP>\03_SiC專案\SiC立案資料\個人週報`
  - 結構：`個人週報\<年>週報\<月>\<週次(日期範圍)>\<年月>_<週次>-新聞(OK).docx`
  - 檔名含全形括號、中文字，**不要**用 `-Filter` 以外的方式硬編碼檔名。
- 目的地：`<PROJECT_ROOT_A>\Projects\<YYYY-MM>-news-review`（目錄不存在時先 `New-Item -ItemType Directory -Force`）。

## 關鍵做法

1. **先列出再搬**：`Get-ChildItem -Path $src -Recurse -Filter "*新聞(OK).docx"`，
   `Select-Object -ExpandProperty FullName` 讓使用者確認範圍與數量。
2. **用 `Move-Item -LiteralPath ... -Force`**，不要用 `Copy-Item`+`Remove-Item`（避免搬一半失敗留下副本）。
   `-LiteralPath` 很重要：檔名含 `(`、`~`、`(` 等字面，`-Path` 會被當成 wildcard。
3. **連同「已示範的那一顆」一起搬**。使用者通常會先手動複製一個當範例，那顆在分享上仍是存在的；
   分享是唯一真實來源（single source of truth），留在分享只會造成雙份與後續不同步，所以要用
   `-Force` 覆寫本機那顆並把分享上的一併移走。
4. **不要搬其他檔案**（週報本文、附件、資料夾本身），遞迴結果只挑 `新聞(OK).docx`。
5. **錯誤不要靜默**：用 `$ErrorActionPreference='Continue'` + try/catch 收集失敗清單，最後一次印出。
   網路分享偶爾會鎖檔或斷線，必須回報哪些沒搬成。
6. **不要用電腦操作**：這是純檔案系統操作，PowerShell 直接做即可，開瀏覽器/Explorer 反而更慢更不可靠。

## PowerShell 範本

```powershell
$ErrorActionPreference='Continue'
$dst='<PROJECT_ROOT_A>\Projects\2026-09-news-review'
$src='\\<CORP_SERVER_IP>\03_SiC專案\SiC立案資料\個人週報'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$files=Get-ChildItem -Path $src -Recurse -Filter "*新聞(OK).docx" -ErrorAction SilentlyContinue
$ok=0;$fail=@()
foreach($f in $files){
  try{ Move-Item -LiteralPath $f.FullName -Destination $dst -Force -ErrorAction Stop; $ok++ }
  catch{ $fail+=$f.FullName + " :: " + $_.Exception.Message }
}
"total=$($files.Count) moved=$ok failed=$($fail.Count)"
$fail
```

## 驗證（必做，搬完一定要跑）

```powershell
$d=Get-ChildItem -LiteralPath $dst -Filter "*新聞(OK).docx"
"local_count=$($d.Count)"
$left=Get-ChildItem -Path $src -Recurse -Filter "*新聞(OK).docx" -ErrorAction SilentlyContinue
"share_remaining=$($left.Count)"
($d | Measure-Object Length -Sum).Sum

# docx 完整性：能當 zip 開 = 未損毀
Add-Type -A System.IO.Compression.FileSystem
$bad=@()
Get-ChildItem $dst -Filter "*新聞(OK).docx" | ForEach-Object {
  try{ $z=[IO.Compression.ZipFile]::OpenRead($_.FullName); $n=$z.Entries.Count; $z.Dispose() } catch { $bad+=$_.Name }
}
"invalid=$($bad.Count)"; $bad
```

通過條件：`local_count == 原本搜尋到的數量`、`share_remaining = 0`、`invalid = 0`。

## 環境陷阱

- **PowerShell 主控台會把中文顯示成亂碼**（CP950 vs UTF-8）。這只是顯示問題，檔名處理本身正確；
  不要因此以為搜尋結果有問題，也不要為了避開亂碼而改用別的工具。
  使用者看到的 `新聞` 會變成 `�s�D`，仍可正常比對。
- `Get-ChildItem -Recurse` 掃整棵 `個人週報`（多年資料）需要數十秒，timeout 給 180s 以上。
- UNC 路徑含中文資料夾名時，`-LiteralPath` 對 `Move-Item` 必要；`Get-ChildItem -Filter` 可用 wildcard。
- 若之後要延伸到其他副檔名（`週報(OK).docx`、附件），只要改 `-Filter` 與驗證的副檔名即可，流程不變。
