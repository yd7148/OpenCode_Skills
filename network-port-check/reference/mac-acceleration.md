# macOS 網路加速完整攻略

適用於「覺得網路慢、影音卡頓、想加速」的情境。
所有指令皆為唯讀診斷；破壞性設定都附還原方式。

---

## 一、先分清三件事

| 現象 | 本質 | 誰能解決 |
|------|------|---------|
| **頻寬不足**（下載天花板低） | 鏈路容量問題 | 只能升級網路（頻段/有線/熱點） |
| **延遲高**（開网页慢、ping 高） | 路由繞遠或塞車 | 改 DNS 幫不上；可能要 VPN |
| **抖動**（忽快忽慢、影音卡） | 遺失/干擾/QoS | 多半只能換連線方式 |

**影音卡頓幾乎都是第三種（抖動）**，而抖動用設定改善不了，只能換環境。

---

## 二、診斷順序（照這個跑）

```bash
cd ~/.config/opencode/skills/network-port-check/scripts

# 1️⃣ 先看連線環境（WiFi 頻段、有沒有 VPN 在偷跑）
./mac-test-proxy.sh

# 2️⃣ 再量頻寬與抖動
./mac-test-bandwidth.sh

# 3️⃣ 一次跑完並出報告
./mac-run-all.sh ~/桌面/網路報告.md
```

### 讀 2️⃣ 的輸出

第四段「下載頻寬」會連續下載 5 次各 5 MB：

```
  段1:   297.93 KB/s  (2.33 Mbps)   ← 慢
  段2:   796.29 KB/s  (6.23 Mbps)
  段3:  1157.08 KB/s  (9.05 Mbps)   ← 快
  段4:   932.75 KB/s  (7.29 Mbps)
  段5:   899.00 KB/s  (7.03 Mbps)
```

| 最大/最小比值 | 判定 |
|---------------|------|
| < 1.5× | 穩定 |
| 1.5–3× | 輕微抖動 |
| **> 3×** | **抖動嚴重 → 影音必卡** |

---

## 三、有效的加速手段

### ⭐⭐⭐⭐⭐ 切換到 5GHz / 6GHz

**實測案例**：某公共圖書館 WiFi 使用者在 2GHz 802.11n 下載只有 8 Mbps，
檢查後發現環境中有大量 5GHz 80MHz AP。切換後通常可提升數倍。

```bash
# 看目前狀態
system_profiler SPAirPortDataType | grep -A5 "Current Network Information"

# 看附近有無 5GHz
system_profiler SPAirPortDataType | grep -E "Channel.*5GHz"

# 本機是否支援
system_profiler SPAirPortDataType | grep "Supported PHY Modes"
```

切換步驟（GUI）：
> 系統設定 › 網路 › Wi‑Fi › 詳細資料 › 硬體 › Wi‑Fi 選項 › 勾選「5 GHz Wi‑Fi」

⚠️ 若 SSID 合併且 AP 沒開 band steering，macOS 可能仍黏在 2GHz。

### ⭐⭐⭐⭐⭐ 改用有線網路

公共圖書館／機場／飯店多有免費有線。走有線通常直接解決問題。

### ⭐⭐⭐⭐⭐ 改用行動熱點

需大量下載／傳檔時最快。

### ⭐⭐⭐ 避開尖峰

公共場所 19–21 點、下雨天最壅塞。

### ⭐⭐ 檢查 ISP 方案

```bash
curl -sS https://ipinfo.io/json | python3 -m json.tool
```
確認實際 ISP 與速率方案是否相符。

---

## 四、無效或要慎用的手段

### ❌ 改 DNS 8.8.8.8 / 1.1.1.1

**只影響 DNS 查詢，不改變頻寬。**

```bash
# 實測：DNS 從 2.1 秒降到 1.1 秒，但下載速度一樣 1 MB/s
```

仍值得做的理由：首次開網頁少等 0.5–1 秒，體感略順。
不值得做的理由：以為能「加速下載」而調高期待。

安全做法（有備份與還原）：

```bash
./mac-tune-network.sh 檢查
./mac-tune-network.sh 套用   # 8.8.8.8 8.8.4.4 168.95.1.1
./mac-tune-network.sh 還原
```

⚠️ 校園/公司網路需保留內網 DNS 作 fallback。

### ⚠️ 掛 VPN / 代理

鏈路已飽和時，VPN 的加密開銷會**更慢**。

```bash
# 先確認有沒有 VPN 在偷跑
./mac-test-proxy.sh   # 看 Tailscale ExitNode、utun 介面
```

只有在「需要繞 geo 限制」時才值得。

### ⚠️ 關閉 IPv6

只在 IPv6 明顯較差時才試，且多數情況 v4/v6 相近。

```bash
curl -sS -4 -o /dev/null -m 10 -w "v4: %{time_starttransfer}\n" https://www.google.com/
curl -sS -6 -o /dev/null -m 10 -w "v6: %{time_starttransfer}\n" https://www.google.com/
```

### ❌ YouTube 網頁端畫質調高

降低畫質是**應急**（避免卡頓），不是加速。
且降低畫質會降低所需頻寊，反而能順暢播放——兩者方向相反。

---

## 五、無線環境優化

### 讓 AP 優先選 5GHz

```bash
# 檢查是否有 5GHz 同名 SSID 可直接連
system_profiler SPAirPortDataType | awk '/Other Local Wi-Fi/,0' | grep -B2 "5GHz"
```

若圖書館 SSID 是合併的，連線後檢查實際頻段：

```bash
system_profiler SPAirPortDataType | grep -A3 "Current Network Information" | grep Channel
```

看到 `2GHz` 就代表還是走 2.4G，需要找館方確認是否有獨立 5GHz SSID。

### 減少周邊干擾

- 避開微波爐、藍牙裝置密集處
- 2.4GHz 只有 1/6/11 三個不重疊信道，鄰居多時互相干擾
- 5GHz 干擾少但涵蓋小，離 AP 近一點

---

## 六、安全提醒

公共 WiFi（尤其 Open / 無密碼）：

- 不要進行網銀、登入重要帳號
- 需要的話用自己的行動熱點
- TLS 有 MITM 就不要輸入密碼

檢查：

```bash
./mac-test-tls.sh "www.google.com,www.youtube.com"
```

若 Issuer 出現公司名 / Proxy 工具，即代表有 SSL inspection，**不要輸入任何密碼**。

---

## 七、速查表

| 症狀 | 先跑什麼 | 通常答案 |
|------|---------|---------|
| 網頁開很慢 | `./mac-test-bandwidth.sh` | 看 dns/conn/ttfb 哪段大 |
| 影片一直卡 | 同上，看第四段抖動 | 抖動大 → 換網路 |
| 下載很慢 | 看頻寬 MB/s | 切 5GHz / 有線 |
| 覺得被代理 | `./mac-test-proxy.sh` | 確認 VPN/Proxy 狀態 |
| 懷疑被監聽 | `./mac-test-tls.sh` | Issuer 是否為公共 CA |
| 網站開不了 | `./mac-test-websites.sh` | 單站失敗 = 服務端問題 |