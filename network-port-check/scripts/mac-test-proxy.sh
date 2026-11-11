#!/bin/bash
# macOS: 代理 / VPN / DNS / WiFi 頻段診斷
# 用法: ./mac-test-proxy.sh

echo "════════ 1. 系統 Proxy 設定 ════════"
scutil --proxy

echo ""
echo "════════ 2. VPN / 代理程式 ════════"
found=0
for p in tailscale cloudflare-warp warp-svc openvpn wireguard-go clash surge sing-box v2ray xray mihomo; do
  pids=$(pgrep -f "$p" 2>/dev/null)
  if [ -n "$pids" ]; then
    echo "  [執行中] $p (PID: $pids)"
    found=1
  fi
done
[ $found -eq 0 ] && echo "  無發現執行中的 VPN / 代理程式"

echo ""
echo "  Tailscale 狀態:"
if command -v tailscale >/dev/null 2>&1; then
  ts_state=$(tailscale status 2>&1 | head -1)
  echo "    $ts_state"
  echo "    Exit Node: $(tailscale debug prefs 2>/dev/null | grep -i ExitNodeID | cut -d'"' -f4)"
  [ -z "$(tailscale debug prefs 2>/dev/null | grep -i ExitNodeID | cut -d'"' -f4)" ] \
    && echo "    → 無 Exit Node，流量未經 Tailscale"
else
  echo "    未安裝"
fi

echo ""
echo "  utun 介面（殘留 tunnel）:"
ifconfig 2>/dev/null | grep -E "^utun" | while read -r line; do echo "    $line"; done

echo ""
echo "════════ 3. DNS 設定 ════════"
echo "  目前 nameserver:"
scutil --dns 2>/dev/null | grep "nameserver" | sort -u | sed 's/^/    /'
echo ""
echo "  各網路服務:"
networksetup -listallnetworkservices 2>/dev/null | tail -n +2 | while read -r svc; do
  [ -z "$svc" ] && continue
  dns=$(networksetup -getdnsservers "$svc" 2>/dev/null | tail -n +2 | tr '\n' ' ')
  printf "    %-20s %s\n" "$svc" "${dns:-（未指定）}"
done

echo ""
echo "════════ 4. WiFi 連線細節（頻段是速度關鍵）════════"
echo "  目前連線:"
system_profiler SPAirPortDataType 2>/dev/null | grep -A5 "Current Network Information" | grep -vE "^--|^$" | head -6 | sed 's/^/    /'

echo ""
echo "  附近 AP（看有沒有 5GHz 可切換）:"
system_profiler SPAirPortDataType 2>/dev/null | awk '
  /Other Local Wi-Fi Networks/,/Supported PHY/' | grep -E "Channel|PHY Mode" | paste - - 2>/dev/null | head -15 | sed 's/^/    /'

echo ""
echo "  本機支援頻段:"
system_profiler SPAirPortDataType 2>/dev/null | grep -m1 "Supported PHY Modes" | sed 's/^/    /'
if system_profiler SPAirPortDataType 2>/dev/null | grep -q "5GHz"; then
  echo "    ✅ 支援 5GHz — 若目前是 2GHz，切過去可大幅提升速度"
else
  echo "    ⚠️ 未偵測到 5GHz 支援"
fi

echo ""
echo "════════ 5. 路由與對外 IP ════════"
echo "  對外出口 IP 與位置:"
curl -sS -m 10 https://ipinfo.io/json 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print('    IP:  ', d.get('ip','?'))
    print('    城市:', d.get('city','?'))
    print('    國家:', d.get('country','?'))
    print('    ISP: ', d.get('org','?'))
except Exception as e:
    print('    取得失敗:', e)
"
echo ""
echo "  預設路由:"
netstat -rn -f inet 2>/dev/null | grep -E "^default|^0.0.0.0" | head -3 | sed 's/^/    /'
echo ""
echo "  CGNAT 判定（100.64.0.0/10 或 10.x 或 192.168.x = 私有位址）:"
gw_if=$(netstat -rn -f inet 2>/dev/null | grep "^default" | awk '{print $NF}')
local_ip=$(ipconfig getifaddr "$gw_if" 2>/dev/null)
echo "    本機 IP: $local_ip"
if echo "$local_ip" | grep -qE "^(100\.(6[4-9]|[7-9][0-9]|1[0-1][0-9]|12[0-7])|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)"; then
  echo "    → CGNAT/私有位址: 內網服務無法從外部直接連入"
fi