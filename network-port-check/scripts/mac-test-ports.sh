#!/bin/bash
# macOS: 對外 TCP port 連通性矩陣（並行，避免 Test-NetConnection 式逐個等待）
# 用法: ./mac-test-ports.sh [ports] [hosts]

PORTS="${1:-22,53,80,443,3389,5900,8080,9418}"
HOSTS="${2:-www.google.com,github.com,speed.cloudflare.com,1.1.1.1,168.95.1.1,<CORP_DOMAIN_SHORT>.com.tw,tptc.com.tw}"

IFS=',' read -ra P <<< "$PORTS"
IFS=',' read -ra H <<< "$HOSTS"

printf "%-24s" "HOST"
for p in "${P[@]}"; do printf "%-7s" "$p"; done
printf "\n"
printf -- "%.0s─" {1..90}; printf "\n"

for host in "${H[@]}"; do
  ip=$(dig +short +tries=1 +time=2 "$host" A 2>/dev/null | tail -1)
  [ -z "$ip" ] && ip="$host"
  printf "%-24s" "$host"

  for port in "${P[@]}"; do
    if nc -z -G 3 -w 3 "$ip" "$port" >/dev/null 2>&1; then
      printf "%-7s" "開"
    else
      printf "%-7s" "封"
    fi
  done
  printf "\n"
done

printf -- "%.0s─" {1..90}; printf "\n"
echo "圖例: 開=TCP 可連線  封=逾時或拒絕  開=白名單 ACL 防火牆的典型特徵"
echo "注意: 4xx/5xx 不算封鎖，只要 TCP 連得上就代表網路可達。"