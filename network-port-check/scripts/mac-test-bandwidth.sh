#!/bin/bash
# macOS: 頻寬 / 延遲 / 抖動 / IPv6 比較
# 用法: ./mac-test-bandwidth.sh

echo "════════ 1. 對外延遲（ping 10 發，間隔 0.2s）════════"
printf "%-14s %-10s %-9s %-9s %-9s %-9s\n" "目標" "成功率" "最小" "平均" "最大" "抖動"
printf -- "%.0s─" {1..66}; printf "\n"

for h in 168.95.1.1 8.8.8.8 1.1.1.1 223.5.5.5; do
  r=$(ping -c 10 -i 0.2 -q "$h" 2>/dev/null | tail -2)
  loss=$(echo "$r" | grep -oE '[0-9.]+% packet loss' | grep -oE '^[0-9.]+')
  stats=$(echo "$r" | grep -oE 'min/avg/max/stddev = [0-9./]+' | cut -d' ' -f3 | tr '/' ' ')
  [ -z "$stats" ] && { printf "%-14s %-10s\n" "$h" "無回應"; continue; }
  printf "%-14s %-10s %-9s %-9s %-9s %-9s\n" "$h" "${loss}%" $stats
done

echo ""
echo "════════ 2. DNS 伺服器比較 ════════"
printf "%-18s %s\n" "DNS 伺服器" "查詢時間"
printf -- "%.0s─" {1..40}; printf "\n"
for s in 168.95.1.1 1.1.1.1 8.8.8.8 223.5.5.5; do
  t=$(dig +tries=1 +time=3 @"$s" www.google.com 2>/dev/null | grep "Query time" | grep -oE '[0-9]+')
  [ -z "$t" ] && t="逾時"
  printf "%-18s %s ms\n" "$s" "$t"
done

echo ""
echo "════════ 3. IPv4 vs IPv6 ════════"
echo "IPv6 位址:"
ifconfig 2>/dev/null | awk '/^[a-z0-9]+:/{i=$1} /inet6 /{if($2!~/^fe80/ && $2!~/::1/) print "  "i" "$2}'
echo ""
for i in 1 2 3; do
  curl -sS -4 -o /dev/null -m 10 -w "  v4: conn=%{time_connect}s ttfb=%{time_starttransfer}s\n" https://www.google.com/ 2>/dev/null
  curl -sS -6 -o /dev/null -m 10 -w "  v6: conn=%{time_connect}s ttfb=%{time_starttransfer}s\n" https://www.google.com/ 2>/dev/null
done

echo ""
echo "════════ 4. 下載頻寬（Cloudflare，每段 5MB）════════"
echo "  觀察各段速度差異 → 差異大代表抖動，會造成影片卡頓"
for i in 1 2 3 4 5; do
  s=$(curl -sS -o /dev/null -m 15 -w "%{speed_download}" "https://speed.cloudflare.com/__down?bytes=5000000&r=$i" 2>/dev/null)
  [ -z "$s" ] && s=0
  printf "  段%d: %8.2f KB/s  (%.2f Mbps)\n" "$i" "$(echo "$s/1024"|bc -l)" "$(echo "$s*8/1048576"|bc -l)"
done

echo ""
echo "════════ 5. 上傳頻寬 ════════"
T=$(mktemp); head -c 8000000 /dev/urandom > "$T"
for i in 1 2; do
  s=$(curl -sS -o /dev/null -m 20 -X POST --data-binary @"$T" -w "%{speed_upload}" https://speed.cloudflare.com/__up 2>/dev/null)
  [ -z "$s" ] && s=0
  printf "  段%d: %8.2f KB/s  (%.2f Mbps)\n" "$i" "$(echo "$s/1024"|bc -l)" "$(echo "$s*8/1048576"|bc -l)"
done
rm -f "$T"

echo ""
echo "════════ 6. TCP 分段時間（延遲來源分析）════════"
curl -sS -o /dev/null -m 15 -w "  dns=%{time_namelookup}s conn=%{time_connect}s tls=%{time_appconnect}s ttfb=%{time_starttransfer}s total=%{time_total}s\n" https://speed.cloudflare.com/

echo ""
echo "════════ 7. 路由追蹤 ════════"
traceroute -n -w 1 -q 1 -m 10 8.8.8.8 2>/dev/null | tail -11