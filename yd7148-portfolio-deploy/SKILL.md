---
name: yd7148-portfolio-deploy
description: Use when 維護／部署／改網址／改路由／處理個資 for 劉士禎的三個個人網站（Astro 7 + Tailwind v4 + GitHub Pages + Actions 自動部署）—— repo `cv1`（v1）、`cv2`（v2）、`cv3`（v3），線上分別是 https://yd7148.github.io/cv1/ 、/cv2/ 、/cv3/ 。Covers GitHub Pages 專案頁的 base 路徑修補、個資搬進 `.env` + Actions secrets、移除語系前綴（`prefixDefaultLocale` + `lp()`）、repo 改名後要跟著改的檔案清單、路由煙霧測試。
license: MIT
compatibility: opencode
metadata:
  audience: opencode agents
  workflow: yd7148-portfolio-deploy
  languages: zh-TW
---

# yd7148 個人網站維運（v1 / v2 / v3）

三個獨立的 Astro 靜態站，部署在 GitHub Pages。**同一份履歷內容、三種版面。**

> **路徑注意**：本 skill 原始碼撰寫於 `<PROJECT_ROOT_B>\01-Project\2026-09-CV\04-Pages\`。
> 該磁碟機在部分機器上不存在（例如 2026-10-04 驗證的機器只有 C: 與 D:，且無 `<PROJECT_ROOT_B>`）。
> 動手前先確認專案根目錄；找不到就從 GitHub clone 对應的 repo（見下表 repo 欄）。

Read [references/current-state.md](references/current-state.md) for machine-verified
URLs, deployment state and rename history. Re-verify before acting.

---

## 一、三個站台

| 版本 | 本機埠 | 線上 | GitHub repo | 版型 | 語系前綴 |
|---|---|---|---|---|---|
| v1 | 4321 | https://yd7148.github.io/cv1/ | yd7148/cv1 | 捲動式長頁面 | **已移除**（根路徑即中文） |
| v2 | 4322 | https://yd7148.github.io/cv2/ | yd7148/cv2 | astro-resume-01（sticky 側欄、periwinkle） | **已移除**（根路徑即中文） |
| v3 | 4323 | https://yd7148.github.io/cv3/ | yd7148/cv3 | astro-portfolio-theme（深色玻璃、indigo/sky） | 仍有 `/zh/`、`/en/` |

**repo 改名歷史**：`yd7148` → `cv1`、`yd7148-v2` → `cv2`、`yd7148-v3` → `cv3`（2026-09-28 改名，2026-10-02 確認）。
GitHub 對改名會保留 API 轉址，但 **Pages 網址不會自動轉**——舊的 `/yd7148-v2/` 之類已失效。

**v3 是主力**，v1／v2 是同一內容的另兩種版面。三個 repo 各自獨立版控，改一個不影響另外兩個。

技術棧（2026-10-04 實測）：Astro `^7.0.3`、Tailwind CSS `^4.3.2`、Node `>=22.12.0`。

---

## 二、命令速查

在對應的 repo 目錄執行（例：`<專案根>/cv3/`）：

```bash
npm run dev              # 本機開發 http://localhost:4323/
npm run check            # astro check，必須 0 errors
npm run build            # astro build + scripts/fix-base.mjs
npm run verify:build     # 隱私閘關：公開頁有個資就 exit 1
npm run deploy           # 舊的 gh-pages 路徑（Pages 來源已改 Actions，通常不需要）
node scripts/verify:pages  # 本機模擬 Pages 路徑跑路由煙霧測試
node scripts/verify:live   # 對線上三站各跑路由煙霧測試
node verify.cjs            # 截圖 + console/溢出/PII 遮罩（需 dev 伺服器）
```

**改完內容上線的最短路徑**：`npm run build`（本機驗證）→ commit + `git push` → 等 Actions。

---

## 三、個資處理（最重要）

### 現況

| 資料 | 放哪 | 是否進版控 |
|---|---|---|
| 學歷、經歷、證照、關鍵字 | `src/data/resume.ts` | ✅ 可（本就公開） |
| 作品集／筆記 | `src/content/{works,notes}/*.md` | ✅ 可 |
| 手機、兩個信箱、分機、完整地址、出生年月 | `.env`（gitignored） | ❌ 絕對不可 |
| Actions 建置用 | GitHub repository secrets | ❌ 不可（但已加密） |
| `01-原始資料/`、`03-中華電信/.pw-profile/` | 在 `2026-09-CV/` 下，**不在任何 git repo** | ❌ 絕對不可 |

`2026-09-CV/` 本身刻意**不是** git repo——底下有身分證字樣的 PDF 與瀏覽器憑證。

### 環境變數

`.env`（7 個 key，三個 repo 各一份，**都要填**）：

```
PUBLIC_BIRTH=            出生年月 YYYY-MM
PUBLIC_MOBILE=           手機
PUBLIC_EMAIL=            個人信箱（也是 Web3Forms 收件信箱）
PUBLIC_EMAIL_WORK=       公司信箱
PUBLIC_TEL_OFFICE=       辦公室電話 + 分機
PUBLIC_ADDRESS_ZH=       完整地址（中文）
PUBLIC_ADDRESS_EN=       完整地址（英文）
```

`src/data/contact.ts` 透過 `import.meta.env` 讀，**不寫死任何值**。

**換手機／信箱／搬家：只改 `.env`，不要動任何 `.ts` 檔。**

### 設定 Actions secrets

```bash
node set-secrets.mjs              # 三個 repo 一次設完（腳本在專案根目錄）
node set-secrets.mjs cv3          # 或只設一個
```

已於 2026-09-28 設定完成（三 repo × 7 keys = 21 個）。

---

## 四、GitHub Pages 專案頁的兩個必踩坑

### 坑 1：base 路徑

站台在子路徑 `/cv3/`，但原始碼裡 `href="/works/"`、`src="/images/…"` 都是根路徑。

**不要**去改 50 多處模板。`scripts/fix-base.mjs` 會在建置後統一改寫 `dist` 的：
`href` / `src` / `action` / `poster` / `data-src` 屬性、`<meta http-equiv="refresh">` 的 `url=`、`robots.txt` 的 `Disallow:`／`Allow:`。

> 為什麼要這樣：Astro 的 `base` 只管它自己產生的路徑，寫死的字串不會被處理。
> 建置後改寫比改模板安全，而且可重複執行（已加前綴的不會被改兩次）。

`astro.config.mjs` 的 base 只在 production 生效：

```js
const isProd = process.env.NODE_ENV === "production";
export const BASE = isProd ? "/" + REPO : "";
```

所以 `npm run dev` 的網址維持 `http://localhost:4323/zh/`，`verify.cjs` 之類的腳本不用改。

### 坑 2：Jekyll 吃掉 `_astro/`

**症狀**：頁面 HTTP 200、沒有任何錯誤訊息，但**完全沒套版型**（白板），瀏覽器 console 顯示
`GET /yd7148/_astro/xxx.css 404`。

**原因**：`gh-pages` 分支部署時 GitHub Pages 預設用 Jekyll 建置，而 Jekyll 會安靜丟棄所有底線開頭的目錄。

**解法**：`gh-pages` 根目錄放一個空的 `.nojekyll` 檔。`scripts/publish-ghpages.mjs` 已經會放。

> 這個坑特別陰險——HTTP 全部 200，只是視覺壞掉。`scripts/smoke-live.mjs` 就是為了抓這種狀況。

---

## 五、部署方式

### 現行：GitHub Actions（自動，已啟用）

`.github/workflows/deploy.yml` 已生效：**push 到 `main` 自動建置並發布**（2026-10-04 實測確認，三個 repo 的 Actions run event 皆為 `push`、conclusion `success`）。

流程：`npm ci` → 檢查 7 個 `PUBLIC_*` secrets 是否齊全（缺任一就 `exit 1`）→ 產生 `.env` → `npm run build` → `npm run verify:build` 隱私閘關 → `rm -f .env` → 上傳 Pages artifact。

兩道保護是刻意設計的：

- 缺任何一個 `PUBLIC_*` secret 就失敗——寧可部署失敗，也不要送出個資空白的履歷頁
- 上傳前跑隱私閘關，公開頁含個資就擋下

**改完內容上線的最短路徑**：`npm run build`（本機驗證）→ commit + `git push` → 等 Actions。

### 舊方式：gh-pages 分支（已非主流）

`npm run deploy` → `publish-ghpages.mjs` 組 orphan `gh-pages` 分支仍可用，但 Pages 來源已改成 **GitHub Actions**，走這條路不會生效。

若要改回分支發布：`gh api -X PUT "repos/yd7148/<repo>/pages" -f build_type=legacy`。

> ⚠️ 不要在主工作目錄 `git checkout --orphan`——會讓整個工作樹變成 untracked，很容易出事。
> 腳本用獨立 clone 就是為了避開這個坑。

---

## 六、gh token 的 workflow scope（最容易卡住的地方）

### 症狀

```
! [remote rejected] HEAD -> main
  (refusing to allow an OAuth App to create or update workflow
   `.github/workflows/deploy.yml` without `workflow` scope)
```

### 原因

`gh` CLI 的 OAuth token 預設只有 `gist, read:org, repo`，沒有 `workflow`。

### 解法（必須使用者親自做）

```powershell
gh auth refresh -h github.com -s workflow
```

接著照它印的指示：

1. 它會顯示 `First copy your one-time code: XXXX-XXXX`
2. 開 <https://github.com/login/device>
3. 貼上那組碼 → Continue → Authorize github

**⚠️ 給 AI 代理的注意事項**：

- 這是 **device flow**，授權碼只印在執行 `gh` 的那個終端機上，而且那個程序必須活著等使用者輸入
- 前景執行會被工具的 timeout 砍掉；背景執行（`Start-Process` + 轉輸出到檔案）**可行**，
  做法是：重導向 stderr 到檔案 → 睡幾秒 → 讀檔拿碼 → **立刻回報給使用者** → 輪詢檔案等完成
- 授權碼 **15 分鐘**過期。第一次嘗試就是因為中途插去做別的事而逾時（`context deadline exceeded`）
- `gh secret set` **不需要** `workflow` scope，用現有 token 就能跑

### 授權完成後

```powershell
# 1. 確認 scope 有加上去
gh auth status          # 應該看到 'gist', 'read:org', 'repo', 'workflow'

# 2. 推送三個 repo 被擋下的 commit（資料夾名＝repo 名）
foreach ($d in 'cv1','cv2','cv3') {
  Push-Location $d; git push origin main; Pop-Location
}

# 3. Pages 來源改成 GitHub Actions
foreach ($r in 'cv1','cv2','cv3') {
  gh api -X PUT "repos/yd7148/$r/pages" -f build_type=workflow
}
```

> 第 3 步不做，Actions 會建置成功但**不會發布**（Pages 還指著 `gh-pages` 分支）。

**✅ 狀態：已於 2026-09-28 完成授權並啟用。** 2026-10-04 實測三個 repo 的 Actions
run event 皆為 `push`、conclusion `success`。本節保留作為**日後新增 repo**時的操作參考。

---

## 七、改網址（repo 改名）

repo 名稱同時決定 Pages 子路徑，所以改名要動幾個地方：

```js
// astro.config.mjs
export const REPO = "新名稱";        // 舊值
export const SITE_URL = "https://yd7148.github.io/" + REPO;
export const BASE = isProd ? "/" + REPO : "";
```

外加：

- `gh repo rename <新名稱>` ＋ `git remote set-url origin ...`
- **本機資料夾也要改名**——`fix-base.mjs` 是用 `path.basename()` 推斷 repo 名來加 base 前綴。本機資料夾沒跟著改的話，`fix-base.mjs` 會寫入錯誤前綴（例如資料夾叫 `work-cv1` 就會產生 `/work-cv1/`），症狀是本機 build 過但線上資源 404
- 重新 `npm run build` 確認 base 前綴正確，再 push
- 確認 Pages 來源仍為 GitHub Actions

> 已完成的改名：`yd7148`→`cv1`、`yd7148-v2`→`cv2`、`yd7148-v3`→`cv3`。
> 改名後舊網址（`/yd7148-v2/` 等）**沒有自動轉址**，已失效。

**不要**改成 `yd7148.github.io`（保留名稱，會衝突）。

綁自有網域：DNS 加 CNAME（`www` → `yd7148.github.io`），GitHub Pages Custom domain 填網域，
並在 `public/` 放一個 `CNAME` 檔（內容是網域名稱）。

---

## 七之二、移除語系前綴（cv1 / cv2 已完成）

原本 `astro.config.mjs` 是 `prefixDefaultLocale: true`，**強制預設語言（中文）也帶 `/zh/`**，
所以入口網址是 `/cv1/zh/`。要讓根路徑直接是中文，改成：

```js
i18n: {
  locales: ["zh", "en"],
  defaultLocale: "zh",
  routing: { prefixDefaultLocale: false },   // 中文在根路徑，只有英文帶 /en/
}
```

三個步驟：

1. **搬檔案**：`src/pages/zh/*` 往上移一層到 `src/pages/*`（`works/`、`notes/` 整個目錄一起移，`zh/index.astro` 刪掉）。搬完**所有相對 import 都要少一層**（`../../layouts/` → `../layouts/`）
2. **加 `lp()` 當單一決策點**，不要到處手寫前綴：

```ts
// src/lib/i18n.ts
export function lp(locale: Locale, path = "/"): string {
  const clean = path === "/" ? "/" : path.startsWith("/") ? path : `/${path}`;
  if (locale === DEFAULT_LOCALE) return clean;   // 中文 → /works/
  return clean === "/" ? "/en/" : `/en${clean}`; // 英文 → /en/works/
}
```

把全部 `` `/${locale}/works/` `` 換成 `` `${lp(locale, "/works/")}` ``，並讓 `altPath()` 建立在 `lp()` 上。

3. 更新 `verify.cjs` 的路由清單

**v3 尚未改**（仍有 `/zh/`、`/en/`）。要改請照上面流程，並注意 v3 是中英並列首頁、改動範圍要另外評估。

---

## 八、路由清單

### cv1 / cv2（2026-10-04 起，無語系前綴）

```
/                      中文首頁（正式入口，canonical）
/works/                作品集
/works/sic-wafer-yolo/ 專案詳情
/about/                學歷頁
/notes/edge-vs-cloud/  技術筆記
/contact/              Web3Forms 表單
/resume/               A4 列印履歷（唯一公開個資的頁，noindex）
/en/                   英文首頁
/en/works/  …          英文版其餘頁面
/robots.txt
/sitemap-0.xml
```

`/zh/*` 舊網址**已 404，沒有轉址相容層**。靜態建置的 catch-all 必須在 `getStaticPaths`
列舉每一條舊路徑，維護成本高；若日後需要相容層再補。

### cv3（仍有語系前綴）

```
/                      302 → /zh/
/zh/  /en/             首頁
/zh/works/             作品集
/…
```

`smoke-pages.mjs` 在本機用 `/<repo>/` 路徑模擬 Pages；`smoke-live.mjs` 打線上三站。
兩者都檢查：HTTP 狀態、橫向溢出、失敗請求。

---

## 九、踩過的坑（不要重蹈）

| 坑 | 後果 | 現在怎麼防 |
|---|---|---|
| **用 PowerShell `Get-Content`/`Set-Content` 改 UTF-8 原始碼** | 中文全毀且不可逆 | 永遠不要用 PowerShell 改原始碼。用 VS Code，或讓 AI 用 Node script 寫回（`fs.writeFileSync(p, s, 'utf8')`）。**注意**：PowerShell 的 `Set-Content -Encoding UTF8` 會寫入 BOM，markdown 開頭多一個 BOM 會讓 `#` 標題失效 |
| **Astro frontmatter 的 `---` 沒放檔案最前面** | `---` 之前寫的註解被當成模板解析，`<repo>` 之類被當 HTML 標籤 → `Unexpected token` | frontmatter 必須是檔案第一行；說明用 JS 註解寫在 `---` **內部** |
| **正則 `(?m)^(---)` 想插 import，結果 opening 與 closing fence 都中招** | import 被重複插入，第二次落在 frontmatter 之外變成畫面上的可見文字 | 用 `IndexOf("---`n")` 只定位第一個 fence，或 regex 加次數限制；插入後立刻檢查 `---` 出現次數是否仍為 2 |
| **regex 用非捕獲群組 `(?:\.\./)+` 卻取 `$m.Groups[2]`** | 路徑變成空字串 `from ""` → `The specifiers must be a non-empty string` | 要重用路徑就得用捕獲群組 `((?:\.\./)+)`；更穩的做法是**不要**從舊 import 取路徑，改用檔案在 `src/` 下的深度重算 |
| **用 `astro.config.mjs` export 的 `BASE` 當 base 前綴** | `BASE` 是 `/cv1`（**無**尾斜線），`slice` 切錯位置 | 用 `import.meta.env.BASE_URL`（是 `/cv1/`，有尾斜線） |
| **CSS/樣式放在元件的 `<style is:global>` 裡** | 只有用到該元件的頁面有樣式，其他頁失控（巨大箭頭、不模糊） | 共用樣式一律放 `src/styles/global.css` |
| **把 `text-backdrop` 之類 media query 沒限定範圍** | 套到所有頁面，grid 被撐爆 | 這類頁面專屬樣式加 `#home` 前綴 |
| **`background:` 簡寫覆蓋 `background-clip`** | 淺色模式下漸層標題變成色塊 | 用 `background-image:` 而非 `background:` |
| **`Astro.url.pathname` 含 base 前綴，但 `altPath` 只認 locale 前綴** | 根路徑算出的語言切換連結變成 `/en/cv1/` | 先 `stripBase(pathname, import.meta.env.BASE_URL)` 再餵給 `altPath()` |
| **hreflang 的 zh 與 en 指向同一個 `alt` 變數** | 中文頁的 `hreflang="zh-Hant-TW"` 指向英文頁 | 拆成 `altZh` / `altEn` 各自算 |
| **`Astro.redirect()` 的目標沒補 base** | 從 `/<repo>/` 進來被彈到主機根目錄 | `fix-base.mjs` 處理 meta refresh |
| **`<script is:inline>` 在 `<head>` 的 header 裡就執行** | 觀察到還沒 parse 的 `<main>`，hero 永遠 opacity 0 | 包在 `DOMContentLoaded` 裡 |
| **驗證腳本裡寫死個資探針** | 個資被寫進 repo 兩次 | 探針從 `.env` 讀（`scripts/pii.cjs`） |
| **不用 `wc -l`／`robocopy`** | Windows 上不存在 | Node `fs`／`split('\n').length` |
| **`verify.cjs` 的 light 方案其實沒切到淺色** | 截圖名稱 `slug`=light、`slug-dark`=dark，但 `colorScheme` 不會改網站主題 | 要真的驗淺色得先 `localStorage.setItem` 再 reload |
| **多個 agent／工作階段同時改同一個 repo** | push 被拒（non-fast-forward），rebase 後 `en/` 檔案殘留 conflict marker 並被 commit 進去 | push 前先 `git fetch`；rebase 後必跑 `npm run build` + `astro check`，並用 `grep '<<<<<<<'` 掃殘留 |

---

## 十、目前狀態（2026-10-04 實測）

| 項目 | 狀態 |
|---|---|
| 三站線上 | ✅ 200（cv1／cv2／cv3） |
| repo 名稱 | ✅ 已改名為 `cv1`／`cv2`／`cv3` |
| Actions 自動部署 | ✅ 已啟用，三 repo event 皆為 `push`、conclusion `success` |
| 現行部署 | GitHub Actions（`deploy.yml`）；`gh-pages` 手動路徑保留但非主流 |
| 語系前綴 | ✅ cv1／cv2 已移除（`prefixDefaultLocale: false` + `lp()`）；⏳ cv3 仍是 `/zh/` |
| 內部連結 | ✅ cv1 19 條、cv2 20 條線上全 200，無壞連結 |
| `astro check` | ✅ 0 errors / 0 warnings |
| 個資 | ✅ 已從原始碼與 git 歷程移除；`.env` + Actions secrets（3 repo × 7 keys = 21 個） |
| 舊 `/zh/*` 網址 | ⚠️ 已 404，無轉址相容層（需時再補） |

### 本機環境差異

本 skill 的路徑撰寫於 `<PROJECT_ROOT_B>\...`。在沒有該磁碟機的機器上：

- `cv1`／`cv2` 可直接 `git clone https://github.com/yd7148/cv1.git`（**資料夾名必須是 `cv1`／`cv2`**，否則 `fix-base.mjs` 會算錯 base 前綴）
- `cv3` 在該機器上不存在
- 建置前需自備 `.env`（7 個 `PUBLIC_*` key），CI 上則由 repository secrets 產生
