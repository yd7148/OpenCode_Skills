#!/bin/bash
# macOS: 一鍵跑完五項檢查
# 用法: ./mac-run-all.sh [輸出檔.md]

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HOME/network-check-$(date +%Y%m%d-%H%M%S).md}"

{
  echo "# 網路環境檢查報告"
  echo ""
  echo "- **產生時間**：$(date '+%Y-%m-%d %H:%M:%S')"
  echo "- **主機**：$(scutil --get ComputerName 2>/dev/null)"
  echo "- **macOS**：$(sw_vers -productVersion) ($(uname -m))"
  echo ""
  echo "---"
  echo ""
  echo "## 1. Proxy / VPN / WiFi 診斷"
  echo '```'
  bash "$DIR/mac-test-proxy.sh"
  echo '```'
  echo ""
  echo "## 2. 頻寬 / 延遲 / 抖動 / IPv6"
  echo '```'
  bash "$DIR/mac-test-bandwidth.sh"
  echo '```'
  echo ""
  echo "## 3. 對外 port 矩陣"
  echo '```'
  bash "$DIR/mac-test-ports.sh"
  echo '```'
  echo ""
  echo "## 4. 網站可達性"
  echo '```'
  bash "$DIR/mac-test-websites.sh"
  echo '```'
  echo ""
  echo "## 5. TLS / MITM"
  echo '```'
  bash "$DIR/mac-test-tls.sh"
  echo '```'
} > "$OUT" 2>&1

echo "報告已輸出：$OUT"
wc -l < "$OUT" | xargs echo "行數："