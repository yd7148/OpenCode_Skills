---
name: twii-excel-fill
description: Use when the user wants to fill in 台股加權指數（發行量加權股價指數）每日漲跌點數 into an Excel 活頁簿（例如「2026-10-02-股價+加密+藥.xlsx」的分頁「1-股價」），或說「把 9/21~10/1 的漲跌填上」「股價那欄補一下」。涵蓋 Yahoo Finance `^TWII` 與 <CORP_DOMAIN_SHORT> 官方 MI_INDEX 抓取、跨 5 欄一組的欄位版面（項次/日期/星期/增減點數/漲跌判斷）定位、休市日判斷、openpyxl 寫回與驗證。
license: MIT
---

# 台股指數漲跌填入 Excel

## 適用場景

`~/Downloads/YYYY-MM-DD-股價+加密+藥.xlsx` 的 `1-股價` 分頁，每 5 欄（間距 6 欄，中間 1 欄空白）一組：

| 相對欄 | 內容 |
|---|---|
| +0 | 項次 |
| +1 | 日期（datetime） |
| +2 | 星期（`=IF(...>0,WEEKDAY(...,1),"")` 公式） |
| +3 | 增減點數（**要填的欄**） |
| +4 | 漲跌判斷（公式） |

第 20~22 列為該組統計（`COUNTIF` / `SUMIF` / 起始-結束），**不要動**。

## 流程

### 1. 定位目標欄組

```python
import openpyxl
from openpyxl.utils import get_column_letter, column_index_from_string as ci
ws = wb["1-股價"]
# 掃第 2 列找 == "日期" 的欄，該欄即「日期」欄
```

**絕對不要用數字欄號硬編碼**（本 skill 實測踩過：`MD` 實際是 index 342，不是 341）。一律用 `ci("MD")` / `get_column_letter()` 換算。

找目標組：日期欄等於使用者指定的最後一日期（例如 2026-10-02）。

### 2. 抓指數資料

Yahoo（主）：

```bash
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?period1=<epoch>&period2=<epoch>&interval=1d" \
  -H "User-Agent: Mozilla/5.0"
```

漲跌 = `close[i] - close[i-1]`，四捨五入 2 檔。**注意 Yahoo 會漏掉假期前一交易日**（實測 2026 中秋連假漏 9/25），所以單獨用 Yahoo 會算錯跨假期的漲跌。

<CORP_DOMAIN_SHORT> 官方（校驗 + 補漏）：

```bash
curl -s "https://www.<CORP_DOMAIN_SHORT>.com.tw/rwd/zh/afterTrading/MI_INDEX?date=YYYYMMDD&type=IND&response=json" \
  -H "User-Agent: Mozilla/5.0"
```

`tables[0].data` 找 `['發行量加權股價指數', 收盤, 漲跌符號, 漲跌點數, 漲跌幅]`。

### 3. 交叉驗證

用表內「已填好且非空」的最近 5~10 筆（例如 LU 組 9/14~9/18）比對 Yahoo 算出的漲跌，**必須完全一致**才繼續。差異代表抓錯指標或欄位。

### 4. 填值規則

- 只寫使用者指定的日期範圍內、非交易日的儲存格留 `None`（保持空白，讓 `漲跌判斷` 顯示 `-`）。
- **不要寫 0**。寫 0 會被 `COUNTIF(...,">0")` 算成上漲天數，統計全錯。
- 保留小數點 2 位（例如 `538.09`、`439.1` 依原資料精度）。
- 假日（週六日、國定假日）不填。判斷依據：Yahoo 該日無資料 **且** <CORP_DOMAIN_SHORT> 該日回傳空 `data`。

### 5. 寫回與驗證

```python
# 寫回前先備份到暫存目錄
wb.save(path)
# 重開驗證
```

驗證檢查：
1. 目標列日期與漲跌一覽表逐筆對照。
2. 公式欄（星期、漲跌判斷、統計列）仍為公式字串。
3. `wb.sheetnames` 未減少（此活頁簿有 `Chart1` 等多個分頁）。

### 6. 收尾

- Excel 若開著會留 `.~檔名.xlsx` 鎖定檔，提醒使用者關閉後再開，避免覆蓋。
- **另存新檔給使用者對照**（實測需求：使用者說「我沒看到檔案」）。原檔在 Excel 已開著時，
  更新後對方往往看不到；除填值到原檔外，另存一份 `原檔名_R1.xlsx` 到同一目錄並驗證：

```bash
cp "<原檔>" "<原檔>_R1.xlsx"
```

  版本遞增規則：`2026-10-10-股價+加密+藥.xlsx` → `_R1` → `_R2`（已存在就再往上加）。
  另存後重開 `_R1` 逐筆驗證日期與漲跌。
- 依全域 AGENTS.md 產出 Markdown 說明檔。

## 注意事項

| 坑 | 處理 |
|---|---|
| openpyxl 不計算公式 | 統計列顯示舊值屬正常，Excel 開啟才重算 |
| 欄號手算錯誤 | 一律 `column_index_from_string` |
| Yahoo 漏假期前一日 | 用 <CORP_DOMAIN_SHORT> 官方補 |
| 10/1~10/2 連假期間 Yahoo 無最新資料 | 以 <CORP_DOMAIN_SHORT> 當日收盤為準 |
| **填錯欄組（實測踩過）** | 「日期」欄可能是 `MH`（index 346）而不是直覺的 `MG`/`MJ`；`MJ` 實際屬於**上一組**，寫錯會污染已填好的資料。**務必以定位到的日期欄 `c` 為基準推導 `c+1`/`c+2`，不要自己猜欄號**；寫入前先用列印該組的統計列（`=MIN(c3:c18)`）確認欄號對得上，並先備份 |
| <CORP_DOMAIN_SHORT> MI_INDEX 對近期日期回傳 HTML 錯誤頁（JSON parse fail） | 退 Yahoo `range=1mo` 取 close 差值；漲跌 = `close[i]-close[i-1]` 四捨五入 2 檔。若使用者已填當日值，可用該值反推交叉驗證 |
| Yahoo 用 `period1/period2` epoch 算錯會拿舊年份 | 直接用 `range=1mo&interval=1d`，並檢印出日期確認年份 |
| 活頁簿有圖表分頁 | openpyxl 來回會遺失不支援的圖表物件，寫回前務必備份 |