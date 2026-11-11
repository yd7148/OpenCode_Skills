# 判讀指南 — 對外網路連線檢查結果

本文件說明如何把 `network-port-check` 的輸出，轉成**可行動的結論**。

---

## 一、Port 矩陣怎麼看

輸出一張「目標 × Port」矩陣，`OK` = 可連線，`X` = 封鎖／拒絕／逾時。

### 判讀步驟

1. **先看「可連線的 Port」清單**——這就是這台機器的對外白名單。
2. **再看「被封鎖的 Port」**是否包含遠端管理協定。
3. **對照 LAN gateway 那列**——區網內的 port 常是開的，對外卻封，
   這個落差最能證明是**邊界防火牆**而不是服務本身沒開。

### 四種常見樣態

| 樣態 | 特徵 | 判定 |
|------|------|------|
| **白名單 ACL** | 只有 53/80/443 通，其餘全封 | 對外只放行 DNS + Web |
| **全開** | 大部分 port 都 OK | 無對外 port 過濾（或僅擋高危 port） |
| **鎖死** | 幾乎全封，連 80/443 都不通 | 完全離線，或需走 Proxy |
| **僅擋高危** | 80/443/53 + 22/3389 開，3306/6379 等資料庫 port 封 | 有選擇性過濾 |

### 注意

- 某些主機（如 `8.8.8.8`）**本來就不開**該 port，該格 `X` 不代表被擋。
  判讀時看**多個目標的一致性**：若所有目標在同一 port 都 `X`，才是真的封鎖。
- `<HOST_GATEWAY_IP>:22`（gateway 的 SSH）常是 `OK`——這是內網管理介面，
  **不代表對外 22 通**。兩者性質完全不同。

---

## 二、遠端服務（RDP/SSH）怎麼看

### 兩個獨立問題，必須分開回答

**問題 A：這台機器可以被別人 RDP 連入嗎？**
需要**同時**滿足三個條件，缺一不可：

| 條件 | 檢查方式 | 常見值 |
|------|----------|--------|
| 有 listener | `Get-NetTCPConnection -State Listen -LocalPort 3389` | 無 |
| 登錄機碼允許 | `HKLM:\...\Terminal Server` → `fDenyTSConnections` | `1` = 停用 |
| 防火牆規則 | `Get-NetFirewallRule -DisplayGroup 'Remote Desktop'` | `0` 條啟用 |

三者缺一即「不可被連入」。開啟需要**系統管理員權限**，一般使用者做不到。

**問題 B：可以從這台機器 RDP 連出去嗎？**
純粹看對外 3389 是否可連。企業環境幾乎都是封鎖的。

### 替代通道

RDP/SSH 被封時，判斷「該走哪條替代路」必須**實測**，不能憑記憶。
同樣只放行 443 的環境，`derp.tailscale.com` 可能通、`ssm.us-east-1.amazonaws.com` 不通。
`test-services.ps1` 第 3 節會逐一探測並只列出實際可用的。

### SSH over 443

若目標主機提供 443 版的 SSH（GitHub 即 `ssh.github.com:443`）：

```powershell
ssh -p 443 git@ssh.github.com
```

讓 Git 自動改寫：

```bash
git config --global url."https://ssh.github.com:443".insteadOf "git@github.com:"
```

---

## 三、網站封鎖怎麼看（最容易判錯的地方）

### 核心原則

```
HTTP 4xx / 5xx  →  伺服器有回應  →  網路可達  →  不是封鎖
沒有任何回應      →  需裸 TCP 複驗  →  才可能是封鎖
```

常見的**假陽性**：

| 看到的狀況 | 實際意義 |
|---|---|
| `api.openai.com` → 401 | **正常**，只是沒帶 API key |
| `api.anthropic.com` → 405 | **正常**，HTTP method 不符 |
| `registry-1.docker.io` → 401 | **正常**，Docker auth token 流程第一步 |
| `stackoverflow.com` → 403 | Cloudflare 機器人阻擋；瀏覽器開啟正常 |
| `claude.ai` / `chatgpt.com` → 403 | Cloudflare 或需登入 |
| 根路徑 → 404 | 伺服器有回應，只是該路徑不存在 |
| HEAD → 405/400 | 伺服器不支援 HEAD，**不代表 GET 也不通** |

### 三層驗證法

判定一個網站是否真被擋，必須通過三層：

```
第 1 層  DNS 解析          失敗 → [DNS!!] 網域可能不存在（不是被擋）
   ↓
第 2 層  TCP 443 握手       失敗 → 可能被擋 / 主機離線
   ↓
第 3 層  TLS + HTTP 回應    有 4xx/5xx → [REACH] 可達，非封鎖
```

`test-websites.ps1` 實作此流程：先 `Invoke-WebRequest`，
若**完全沒有** HTTP 回應才用裸 TCP 443 複驗。

### 什麼才算「真封鎖」

必須**同時**滿足：

1. DNS 能解析；
2. 裸 TCP 443 握手失敗（逾時或被 RST）；
3. 換其他目標站測試，該 port 一致不通（排除該站自己故障）。

三者都成立，才可判定為網路層封鎖。

### 補充

- 掃描成人／博弈網站可以判斷環境有無**內容層級**過濾；
  若它們也回 2xx，代表網路層沒有分類封鎖。
- 某些中國站（百度、163）在台灣 HiNet 可正常連線；
  反之亦然。區域性 DNS 污染會讓 DNS 解析到奇怪 IP。

---

## 四、TLS / MITM 怎麼看

看憑證的 **Issuer（簽發者）**：

| Issuer 範例 | 判定 |
|------------|------|
| `Google Trust Services`、`Let's Encrypt`（ISRG）、`DigiCert` | 原廠憑證，正常 |
| `Sectigo`、`Microsoft`、`Amazon`、`Apple`、`GlobalSign` | 原廠憑證，正常 |
| **自己公司的名稱**（如 `TW, O=ABC Corp`） | ⚠️ **SSL inspection**，TLS 已被解密 |
| `zscaler` / `paloalto` / `fortinet` | 資安產品的 SSL inspection |

若出現公司自簽 CA，代表該環境部署了 HTTPS 解密。
可到 `certmgr.msc` → 「受信任的根憑證發行機」確認。

**實務影響**：
- 憑證由原廠 CA 簽發 → 端對端加密未被監控，可正常使用。
- 憑證被公司解密 → 惡意網站理論上可被中間人攔截；
  且少數軟體（舊版 Java、部分 API client）會因 CA 不受信任而直接連線失敗。

---

## 五、頻寬 / 延遲怎麼看

| 指標 | 判讀 |
|------|------|
| 下載 ≥ 300 Mbps | 商業光纖 |
| 下載 100–300 Mbps | 一般寬頻 |
| 下載 < 100 Mbps | 頻寬偏低，大檔下載會明顯偏慢 |
| RTT < 10 ms | 在地／ peering 良好 |
| RTT > 150 ms | 跨國或绕遠路 |

### 注意事項

- **單次測速只是快照**，CDN 快取、當下負載都會影響。以中位數較準。
- 至少要有一個測速站成功；歐洲主機常不回應，不算異常。
- 若 TCP handshake 很快但 ICMP ping 不回應 → 正常，只是 ICMP 被過濾。
- `tracert` 中出現 `*`（逾時）不代表該節點有問題，
  只是該路由器不回應 ICMP。**要看最後能否抵達目的地**。

---

## 六、產出報告的建議結構

```markdown
# 對外網路連線檢查報告

## 1. 環境        本機 IP / Gateway / DNS / Proxy
## 2. Port 結論    開放清單 + 封鎖清單 + 白名單判定
## 3. 遠端服務     RDP 進/出 + 443 替代通道實測
## 4. 網站封鎖     正常 / 可達但非 2xx / 真封鎖
## 5. TLS          是否 MITM
## 6. 頻寬延遲     上/下載 + RTT + 路由
## 7. 實務建議     需求 → 能否 → 解方
```

**第 7 節最重要**——使用者要的是「那我該怎麼辦」，
不是一張 port 表。務必把每個受限需求對應到具體可用的替代方案。
