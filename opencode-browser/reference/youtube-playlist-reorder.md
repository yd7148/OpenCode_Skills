# 重排 YouTube 播放清單 — 機制與演算法

## 先搞懂 YouTube 的兩種「順序」

| 順序 | 說明 | 改變方式 |
|---|---|---|
| **排序模式（sort）** | 顯示時依「發布日期」「加入日期」「最熱門」重排 | 公開播放清單頁頂端 chip 下拉 |
| **手動順序（manual）** | 實際儲存的清單順序 | 拖曳、或每列動作選單的「移至頂端／移至底部」 |

兩者互動，**最容易踩的坑**：

> 對一個「非手動」排序模式的播放清單做手動搬移時，YouTube 會切換成手動模式，
> 但畫面顯示的順序與你預期的可能不同（未搬移的項目順序會改變）。
> **每次搬移後都要重讀清單順序**，不要假設「移到頂端」等於「其他項目順序不變」。

## 排序下拉（chip）

新版公開播放清單頁（`https://www.youtube.com/playlist?list=<ID>`）頂端有一個 chip，
顯示目前的排序模式（「手動」／「發布日期 (最舊)」…）。點它會展開選單：

| 選項 | 意義 |
|---|---|
| 手動 | 使用儲存的手動順序 |
| 新增日期 (最新) / (最舊) | 依加入播放清單的時間 |
| 最熱門 | 依觀看次數 |
| 發布日期 (最新) / (最舊) | 依影片發布時間 |

> 「發布日期 (最舊)」**不一定等於**你想要的順序。YouTube 的發布日期與影片標題裡的
> 日期可能不同（例如先設為不公開再改為公開），實測有影片的發布順序與標示日期不一致。
> 把它當成「快速取得近似順序」的一鍵功能，最終仍要驗證。

**技術重點**：chip 是新版 view model（`chip-view-model` → `button.ytChipShapeButtonReset`），
舊版的 `yt-dropdown-menu` / `tp-yt-paper-menu-button` 在 DOM 裡但尺寸為 0（不可見）。
程式化 `.click()` 對 chip **有效**，但對舊版 paper 元件常無效。

## 每列動作選單（重新排列的主力）

每一列右側的 ⋮ → `ytd-menu-renderer`：

| 選項 | 用途 |
|---|---|
| 移至頂端 | 把該片移到清單最前面 |
| 移至底部 | 把該片移到清單最後面 |
| 設為播放清單縮圖 | 指定縮圖 |
| 下載／分享／儲存至播放清單 | 其他 |

技術上：

```js
// 找到目標列
const row = [...document.querySelectorAll("ytd-playlist-video-renderer")]
  .find((r) => (r.querySelector("#video-title")?.getAttribute("title") || "").includes("<TITLE_TOKEN>"));
// 每列的 ⋮ 按鈕（aria-label = 動作選單）
const menu = [...row.querySelectorAll("button")]
  .find((b) => (b.getAttribute("aria-label") || "").includes("動作選單"));
// 選單項目（點擊前先確認可見且座標正確）
[...document.querySelectorAll("ytd-menu-service-item-renderer")]
  .find((e) => (e.textContent || "").trim() === "移至頂端");
```

> 選單開啟後是浮動層，**必須用真實滑鼠事件**（CDP `Input.dispatchMouseEvent`），
> 座標取自 `getBoundingClientRect()`。程式化 `.click()` 常對 paper 元件無效。

## 重排演算法（反向搬移）

目標順序 `T1, T2, …, Tn`。做法：**依目標順序的相反順序**逐筆「移至頂端」。

```text
目標：T1 T2 T3 T4
搬移順序：T4 → T3 → T2 → T1

T4 移至頂端 → T4 T1 T2 T3
T3 移至頂端 → T3 T4 T1 T2
T2 移至頂端 → T2 T3 T4 T1
T1 移至頂端 → T1 T2 T3 T4   ✓
```

因為每次「移至頂端」都會把其餘項目往後推一格，所以**後搬的會排在先搬的前面**，
反向搬完自然就是目標順序。

優點：每次只需 1 次搬移，總搬移次數 = 項目數，不需要算插入點。

## 實作骨架（Node + CDP）

```js
// 每一輪：開列的動作選單 → 點「移至頂端」→ 重讀順序
for (const token of tokens.reverse()) {
  const btn = await findMenuButton(token);      // 取得 ⋮ 的視口座標
  await clickAt(btn.x, btn.y);                   // 真實滑鼠事件
  const item = await findMenuItem("移至頂端");   // 選單項目的視口座標
  await clickAt(item.x, item.y);
  const order = await readOrder();              // 重讀驗證
  console.log(order);
}
```

注意事項：

1. **每輪都要重讀順序**，失敗時要能看出是哪一步壞掉。
2. **開選單前先 `scrollIntoView`**，否則目標列可能在視窗外，座標會點到別列。
3. **比對標題用 token**（例如 `Class07-` 或 `Part-1`），不要用完整標題，
   完整標題含日期與括號，容易因全形／半形差異而比對失敗。
4. **同名影片**：有 Part-1 / Part-2 時，`Part-1` 這種 token 才唯一。
5. **選單項目文字**要拿 DOM 實際值（簡體/繁體、括號寬度都可能不同），
   先 dump 出清單再比對，不要硬編碼。

## 完成後的雙重驗證

重排只是「顯示順序」，真正要確認的是**伺服器端儲存的順序**。兩個頁面都要重載後再看：

| 頁面 | 檢查 |
|---|---|
| 公開播放清單頁 `youtube.com/playlist?list=<ID>` | 重載後讀 `ytd-playlist-video-renderer` 順序 |
| Studio 編輯器 `studio.youtube.com/playlist/<ID>/videos` | 重載後讀 `ytcp-video-row` 順序（`#video-title` 的 `aria-label`） |

兩邊順序一致才算完成。順便確認排序 chip 已回到「手動」模式。

## 相關限制

- 新版 Studio（`/playlist/<ID>/videos`）**沒有**排序或搬移功能，只有每列的
  「從這個播放清單中移除／永久刪除」。
- 舊版 Studio 編輯器（`studio.youtube.com/playlist?list=<ID>`）已停用，會顯示錯誤頁。
- 排序功能位於**公開**播放清單頁，不是 Studio。
