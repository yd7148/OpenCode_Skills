#!/bin/bash
# 逐一連線到指定 WiFi 並實測速度排名
#
# ⚠️ 使用前請注意：
#   - 會切換 WiFi 連線，中斷當前網路
#   - 測完必須復原
#   - 只做唯讀測速，不發送任何資料
#   - 只測你擁有或已獲授權使用的網路；未經許可請勿連線他人網路
#
# 用法: ./mac-speedtest-networks.sh <ssid1> [ssid2 ...]
# 範例: ./mac-speedtest-networks.sh "Library_5G" "Guest_5G"

set -u

IFACE="en0"
BACKUP_SSID=$(ipconfig getsummary "$IFACE" 2>/dev/null | awk '/SSID/ {print $2; exit}')

if [ -z "$BACKUP_SSID" ]; then
  echo "❌ 無法讀取目前 SSID，中止（避免無法復原）"; exit 1
fi

restore() {
  echo ""
  echo "════════ 復原連線 ════════"
  if [ -n "$BACKUP_SSID" ]; then
    echo "切回 $BACKUP_SSID ..."
    networksetup -setairportnetwork "$IFACE" "$BACKUP_SSID" 2>&1 | sed 's/^/  /'
    sleep 4
    now=$(ipconfig getsummary "$IFACE" 2>/dev/null | awk '/SSID/ {print $2; exit}')
    if [ "$now" = "$BACKUP_SSID" ]; then
      echo "✅ 已復原至 $BACKUP_SSID"
    else
      echo "⚠️  請手動確認，目前 SSID: ${now:-未知}"
    fi
  fi
}
trap restore EXIT INT TERM

measure() {
  local name="$1"
  echo ""
  echo "════════ $name ════════"

  # 確認連上了
  local cur
  cur=$(ipconfig getsummary "$IFACE" 2>/dev/null | awk '/SSID/ {print $2; exit}')
  if [ "$cur" != "$name" ]; then
    echo "  ⚠️  未連上（可能需要密碼或訊號不足）"; return
  fi

  local ch
  ch=$(system_profiler SPAirPortDataType 2>/dev/null \
       | grep -A6 "Current Network Information" | grep Channel | head -1 | sed 's/.*: //')
  local ip
  ip=$(ipconfig getifaddr "$IFACE" 2>/dev/null)
  echo "  頻道: ${ch:-?}   IP: ${ip:-無（可能無 DHCP）}"

  # DNS 延遲
  local dt
  dt=$(dig +tries=1 +time=3 www.google.com 2>/dev/null | grep "Query time" | grep -oE '[0-9]+')
  echo "  DNS: ${dt:-?} ms"

  # 下載 3 段算抖動
  echo "  下載測試（3 × 5MB）:"
  local speeds=()
  for i in 1 2 3; do
    s=$(curl -sS -o /dev/null -m 15 -w "%{speed_download}" \
        "https://speed.cloudflare.com/__down?bytes=5000000&r=$RANDOM$i" 2>/dev/null)
    [ -z "$s" ] && s=0
    speeds+=("$s")
    printf "    段%d: %8.2f KB/s\n" "$i" "$(echo "$s/1024"|bc -l)"
  done

  local mx mn
  mx=$(printf '%s\n' "${speeds[@]}" | sort -rn | head -1)
  mn=$(printf '%s\n' "${speeds[@]}" | sort -n | head -1)
  echo "  峰值: $((mx/1024)) KB/s   谷值: $((mn/1024)) KB/s"
  if [ "$mn" -gt 0 ]; then
    echo "  抖動比: $(echo "scale=2; $mx/$mn" | bc -l)×"
  fi
  echo "  $mx|$mn|$dt"
}

echo "══════════════════════════════════════════"
echo " WiFi 網路實測速度排名"
echo " 目前網路: $BACKUP_SSID（將於結束時自動復原）"
echo "══════════════════════════════════════════"

RESULTS=""
for ssid in "$@"; do
  echo ""
  echo "──→ 嘗試連線: $ssid"
  out=$(networksetup -setairportnetwork "$IFACE" "$ssid" 2>&1)
  if echo "$out" | grep -qiE "fail|incorrect|error|未"; then
    echo "  ❌ 連線失敗: $(echo "$out" | head -1)"
    RESULTS="$RESULTS$ssid|FAIL|-|-|-\n"
    continue
  fi
  sleep 5
  r=$(measure "$ssid" | tail -1)
  RESULTS="$RESULTS$ssid|OK|$r\n"
done

echo ""
echo "══════════════════════════════════════════"
echo " 速度排名（峰值下載速度）
"
echo "══════════════════════════════════════════"
printf "%-26s %-6s %-12s %-10s %-10s %s\n" "SSID" "狀態" "峰值KB/s" "谷值KB/s" "抖動比" "DNS"
printf -- "%.0s─" {1..74}; printf "\n"

echo -e "$RESULTS" | while IFS='|' read -r name st mx mn dt; do
  [ -z "$name" ] && continue
  if [ "$st" = "OK" ] && [ "$mn" != "-" ] && [ "$mn" -gt 0 ]; then
    jit=$(echo "scale=2; $mx/$mn" | bc -l)
    printf "%-26s %-6s %-12s %-10s %-10s %s\n" "$name" "$st" \
      "$((mx/1024))" "$((mn/1024))" "${jit}×" "${dt}ms"
  else
    printf "%-26s %-6s %-12s %-10s %-10s %s\n" "$name" "FAIL" "-" "-" "-" "-"
  fi
done | sort -k3 -rn