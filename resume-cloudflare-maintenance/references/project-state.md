# Verified project state — 2026-10-04

Root: `<USERPROFILE>\Documents\Codex\2026-09-26\https-codotx-com-news-claude-code`
（此路徑已於本機驗證存在。skill 早期版本提到的 `<PROJECT_ROOT_C>\2026-09-CV` 不存在。）

## Live release

- Worker: `cv`
- Account subdomain: `<USER_2>`
- URL: **https://cv.4pins.workers.dev/**
- Verified 2026-10-04: HTTPS 200，`<title>` = `Shih-Chen Liu · Personal Resume`
- **沒有語系前綴**：`/zh/` 與 `/en/` 都回 404，根路徑直接是中文履歷
- Actual config: `work/cv-<USER_2>-deploy-v1/wrangler.jsonc`
- Actual assets: `work/cv-<USER_2>-deploy-v1/site`
- Wrangler CLI: 4.142.0
- robots/noindex 仍保留（noindex 不等於私有，站台本身是公開的）

### 已失效 / 已淘汰

| 項目 | 狀態 |
|---|---|
| Worker `resume01-trial` | 保留但已非現行 |
| subdomain `resume01-deploy-v1` | `resume01-trial.resume01-deploy-v1.workers.dev` 已失效，**不會自動轉址** |
| `work/resume01-deploy-v1` | 保留為舊快照，現行部署不再讀它 |

## GitHub 自動部署（2026-09-29 已完成）

Cloudflare GitHub 整合已安裝，**只授權 `yd7148/CV`**。

| 設定 | 值 |
|---|---|
| 儲存庫 | `yd7148/CV` |
| 正式分支 | `main` |
| 根目錄 | `work/cv-<USER_2>-deploy-v1` |
| 組建命令 | 留空（發布副本已是靜態網站） |
| 部署命令 | `npx --yes wrangler@4.142.0 deploy` |
| 網站檔案 | `site/` |

- 已用實際 push 驗證自動觸發（耗時約 21 秒）
- 監看路徑為 `*`，`main` 的推送皆可能觸發發布
- **發布內容只來自 `site/`**。改 `work/personal-site` 的 Astro 元件不會自動上線

## 這個 repo 沒有 GitHub Pages（重要）

`yd7148/CV` 是 **private**，且 `has_pages = false`。

- 因此 `https://yd7148.github.io/CV/`（或 `/cv/`）**必定 404**，而且從來沒有上線過
- GitHub Pages 路徑 `yd7148.github.io/<repo>/` 是 GitHub 依 repo 名自動產生的，與 Worker 網址無關
- 私有 repo 的 GitHub Pages 需要付費方案（Pro／Team／Enterprise）
- 履歷站對外只有 `https://cv.4pins.workers.dev/` 這一個入口

## Source and preserved variants

- 主要 Astro 專案：`work/personal-site`
- 履歷元件：`work/personal-site/src/components/ResumeInspired.astro`
- 共用履歷資料：`work/personal-site/src/data/profile.ts`
- 版型預覽：`work/personal-site/src/pages/previews/[layout].astro`
- 現行發布副本：`work/cv-<USER_2>-deploy-v1`
- 保留快照：`work/resume01-deploy-v1`
- 參考模板來源：`work/original-astro-cv`、`work/original-portfolio-cv`、`work/original-portfolio-theme`

本機預覽路徑：`/previews/resume/`、`/design-lab-v1/`、`/design-images-v1/`

## Backups and records

- 三版本備份：`outputs/website-backups/2026-09-28T01-18-56-600Z`
- 九種版面：`outputs/design-lab-backups/2026-09-28-100637/Nine-Designs-v1.zip`
- 網址與自動部署紀錄：`outputs/cv-<USER_2>-網址與自動部署紀錄-20260928.md`
- 首次部署紀錄：`outputs/Resume01-Cloudflare-部署紀錄-20260928.md`
- 詳細手冊：`outputs/Resume01-維護手冊與完整操作紀錄.md`

Do not archive `secrets`, `.env*`, OAuth configuration, or raw tool authentication logs. Historical original-template project includes a secrets folder; it is not part of public website content.
