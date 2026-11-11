# 範例報告 — 商業網路環境實測

以下是某台 HiNet 商業光纖主機的實測結果，可作為輸出格式與判讀的參考範本。
（數據為實測值，僅供對照格式；請以自己機器的實際測試為準。）

---

# 對外網路連線測試報告

測試主機：`<HOST_IP>/24`（gateway `<HOST_GATEWAY_IP>`，DNS `168.95.1.1` HiNet）
測試工具：PowerShell 5.1 + `curl.exe`

---

## 1. 環境

| 項目 | 值 |
|---|---|
| 內網 IP | `<HOST_IP>/24` |
| 預設閘道 | `<HOST_GATEWAY_IP>` |
| DNS | `168.95.1.1` (HiNet) |
| 系統 Proxy | 未設定（ProxyEnable=0，無 PAC） |
| HTTP Proxy 環境變數 | 無（僅 `NO_PROXY`） |
| 上網路徑 | HiNet → <ISP_PEERING_IP> → <ISP_PEERING_IP> → <ISP_PEERING_IP> → ISP peering |

---

## 2. 對外 PORT 結論

### 只有 3 個 Port 通

| Port | 服務 | 狀態 |
|------|------|------|
| **53** | DNS | 通過 |
| **80** | HTTP | 通過 |
| **443** | HTTPS | 通過 |

### 全部被封鎖

```
21   22    25    110   123   143   389   445   587   636
993  995   1433  1521  3306  3389  5432  5900  5985  6379
8080 8443  8888  27017
```

> 典型的 **ACL 白名單型防火牆**：只放行 DNS + Web，
> 資料庫與遠端管理協定全封。
> 注意：區網 `<HOST_GATEWAY_IP>:22` 反而是開的（gateway SSH），但對外 22 不通。

---

## 3. RDP (3389) — 不通

### 對外 3389 全部封鎖

```
3389 -> 8.8.8.8, 1.1.1.1, 13.107.6.1  = BLOCKED
3389 -> <HOST_GATEWAY_IP> / <HOST_DNS_IP>      = BLOCKED
```

### 本機 RDP Server 狀態

| 項目 | 值 | 意義 |
|------|-----|------|
| 3389 listener | **無** | 未監聽 |
| `fDenyTSConnections` | `1` | **RDP 停用** |
| TermService 服務 | `Stopped` | 服務未啟動 |
| 防火牆 RDP 規則 | `0` 條啟用 | 規則不存在 |

> 結論：這台機器**不能當 RDP 主機被連入**（需管理員權限開啟）。

### 替代方案（走 443，實測皆通）

| 服務 | 443 | 用途 |
|------|-----|------|
| Tailscale DERP | ✅ | 推薦，可做 RDP 類似遠端桌面 |
| ZeroTier | ✅ | 虛擬區網 |
| Twingate | ✅ | 零信任通道 |
| ngrok | ✅ | 對外開放本機服務 |
| Cloudflare Tunnel | ✅ | 對外開放本機服務 |
| AWS SSM Session Manager | ✅ | 雲端主機免公開 3389 |
| Google Cloud IAP | ✅ | TCP forward 到內部服務 |

---

## 4. SSH / Git 傳輸

| Port | 目標 | 狀態 |
|------|------|------|
| 22 | github.com | ❌ 封鎖 |
| 22 | speed.hetzner.de | ❌ 封鎖 |
| **443** | **ssh.github.com** | ✅ **通** |
| 9418 | github.com (git://) | ❌ 封鎖 |

> **可行解**：
> ```bash
> git config --global url."https://ssh.github.com:443".insteadOf "git@github.com:"
> ```
> HTTPS clone（`https://github.com/...`）本來就可用。

---

## 5. 網站封鎖狀況

### ✅ 完全正常（2xx）

- **開發**：GitHub、GitLab、Bitbucket、npm、PyPI、HuggingFace、Docker Hub
- **Google**：Google、YouTube、Gmail、Drive、Translate
- **AI**：OpenAI、Anthropic、Claude.ai、OpenCode、Perplexity
- **生產力**：Notion、Figma、Slack、Zoom、Teams
- **社交**：LINE、Telegram、Discord、TikTok、Instagram、X、LinkedIn、Reddit、Wikipedia
- **其他**：M365、OneDrive、Cloudflare、Yahoo TW/JP、Naver、Baidu、163、Steam、Spotify

### ⚠️ 伺服器有回應，但非 2xx（**不是封鎖**）

| 站 | Code | 說明 |
|----|------|------|
| api.openai.com | 401 | 缺 API key（正常） |
| api.anthropic.com | 405 | HTTP method 不符（正常） |
| registry-1.docker.io | 401 | Docker auth 流程（正常） |
| claude.ai / chatgpt.com | 403 | Cloudflare / 需登入 |
| stackoverflow.com | 403 | Cloudflare 機器人阻擋 |
| canva.com | 403 | Cloudflare |

> 這些都完成了 TCP + TLS 握手，**不是網路層封鎖**。瀏覽器開啟通常正常。

### ❌ 唯一真問題

| 項目 | 狀態 | 影響 |
|------|------|------|
| `rdweb.westsus2.microsoft.com` | DNS 無 A 記錄 | 網域本身不存在，非封鎖 |

> **結論：沒有任何網站被政策性封鎖。**
> 掃描成人／博弈網站皆回 200，代表網路層沒有分類過濾。

---

## 6. TLS / 中間人檢查

無 TLS interception，憑證簽發者皆為原廠 CA：

| 主機 | 簽發者 |
|------|--------|
| www.google.com | Google Trust Services (WR2) |
| api.anthropic.com | Google Trust Services (WE1) |
| github.com | Sectigo DV E36 |
| www.microsoft.com | Microsoft TLS G2 RSA CA OCSP 04 |
| huggingface.co | Amazon RSA 2048 M01 |

> 無企業 MITM 根憑證 → **端對端加密未被監控**。

---

## 7. 頻寬 / 延遲

| 方向 | 速率 |
|------|------|
| **下載** | **~400–840 Mbps** |
| **上傳** | **~168 Mbps** |

| 目標 | RTT |
|------|-----|
| 1.1.1.1 | **1.3 ms** |
| 8.8.8.8 | 3.7 ms |
| www.google.com | 2.3 ms |
| github.com | 31.7 ms |

> 商業光纖水準。延遲極低，ISP peering 正常。

---

## 8. 實務建議

| 需求 | 狀態 | 解方 |
|------|------|------|
| 遠端桌面連入本機 | ❌ 不行 | 需 IT 開啟 RDP；或用 Tailscale（443 已通） |
| 遠端桌面連出到別台 | ❌ | Tailscale / ZeroTier / AWS SSM / IAP 走 443 |
| SSH 到外部主機 | ❌ | 走 443：`ssh -p 443 user@ssh.github.com` |
| Git push over SSH | ❌ | 改 HTTPS，或 `insteadOf` 轉 443 |
| 裝套件 / 拉 image | ✅ 可以 | npm / PyPI / Docker Hub 全通 |
| 對外開放本機服務 | ❌ | ngrok / Cloudflare Tunnel / Twingate |
