#!/bin/bash
# macOS: 掃描附近 WiFi（SSID 名稱 + 頻段 + 訊號），並分出 5GHz 清單
# 需要「定位服務」授權才能讀到 SSID 名稱
# 用法: ./mac-scan-wifi.sh

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/mac-wifi-scan.swift"
BIN=/tmp/opencode-wifi-scan

if [ ! -f "$SRC" ]; then
  echo "找不到 $SRC"; exit 1
fi

if ! swiftc "$SRC" -o "$BIN" 2>/dev/null; then
  echo "編譯失敗"; exit 1
fi

OUT=$("$BIN")

if echo "$OUT" | head -1 | grep -q "(hidden)"; then
  echo "⚠️  SSID 名稱全部顯示為 (hidden)"
  echo ""
  echo "原因：macOS 自  Catalina 起，讀取附近 WiFi 名稱需要「定位服務」授權。"
  echo ""
  echo "開啟方式："
  echo "  系統設定 › 隱私權與安全性 › 定位服務"
  echo "  找到你使用的終端機（Terminal / iTerm / Warp）"
  echo "  開啟開關 → 選「使用期間」"
  echo ""
  echo "授權後重新執行本腳本即可看到名稱。"
  echo ""
  echo "（即使沒有名稱，以下頻段與訊號資訊仍完整可用）"
  echo "══════════════════════════════════════════════"
fi

echo ""
echo "══════════ 全部可見網路（依訊號強度）══════════"
printf "%-28s %-7s %-6s %-8s %s\n" "SSID" "頻段" "頻道" "頻寬" "訊號"
printf -- "%.0s─" {1..62}; printf "\n"
echo "$OUT" | sort -t'|' -k5 -rn | while IFS='|' read -r ssid band ch width rssi; do
  quality="▓▓▓▓▓"
  [ "${rssi//[^0-9]/}" -ge 80 ] && quality="▓▓▓▓"
  [ "${rssi//[^0-9]/}" -ge 90 ] && quality="▓▓"
  printf "%-28s %-7s %-6s %-8s %s\n" "$ssid" "$band" "$ch" "$width" "$rssi $quality"
done

echo ""
echo "══════════ 5GHz 網路清單（可切換的目標）══════════"
COUNT=$(echo "$OUT" | grep -c "|5GHz|")
TOTAL=$(echo "$OUT" | wc -l | tr -d ' ')
echo "  共掃描 $TOTAL 個，其中 5GHz 有 $COUNT 個"
echo ""
printf "%-28s %-6s %-8s %s\n" "SSID" "頻道" "頻寬" "訊號"
printf -- "%.0s─" {1..50}; printf "\n"
echo "$OUT" | grep "|5GHz|" | sort -t'|' -k5 -rn | while IFS='|' read -r ssid band ch width rssi; do
  printf "%-28s %-6s %-8s %s\n" "$ssid" "$ch" "$width" "$rssi"
done

echo ""
echo "══════════ 頻段分布 ══════════"
echo "$OUT" | awk -F'|' '{print $2}' | sort | uniq -c | sed 's/^/  /'
echo ""
echo "══════════ 訊號強度對照 ══════════"
echo "  -50 ~ -60 dBm  極佳  ← 目標區間"
echo "  -60 ~ -70 dBm  良好"
echo "  -70 ~ -80 dBm  普通"
echo "  -80 ~ -90 dBm  微弱"
echo ""
echo "  RSSI 數值越接近 0（或絕對值越小）越好。"