#!/bin/bash
# macOS: TLS 憑證 / MITM 偵測
# 用法: ./mac-test-tls.sh [hosts]

HOSTS="${1:-www.google.com,github.com,www.youtube.com,speed.cloudflare.com,<CORP_DOMAIN_SHORT>.com.tw}"

IFS=',' read -ra H <<< "$HOSTS"

echo "════════ TLS 憑證簽發者 ════════"
printf "%-26s %-10s %-34s %s\n" "主機" "TLS 版本" "簽發者 (Issuer)" "狀態"
printf -- "%.0s─" {1..100}; printf "\n"

for h in "${H[@]}"; do
  out=$(echo | openssl s_client -connect "$h:443" -servername "$h" 2>/dev/null)
  [ -z "$out" ] && { printf "%-26s %-10s %-34s %s\n" "$h" "-" "連線失敗" "❌"; continue; }

  ver=$(echo "$out" | grep -E "^\s+Protocol\s*:" | head -1 | awk '{print $2}')
  issuer=$(echo "$out" | openssl x509 -noout -issuer 2>/dev/null | sed 's/^issuer=//')
  subj=$(echo "$out" | openssl x509 -noout -subject 2>/dev/null | sed 's/^subject=//')

  # 判定是否為企業/本機簽發（非公共 CA）→ SSL inspection 嫌疑
  status="✅ 正常"
  echo "$issuer" | grep -qiE "mitm|proxy|squid|netskope|zscaler|fortinet|palo|cisco|bluecoat|F5|China .*Technology|GlobalSign.*Company" \
    && status="⚠️ 疑似 MITM"
  # CN 不符網域
  echo "$subj" | grep -qiE "CN *= *[a-zA-Z0-9.-]*Warg" && status="⚠️ 憑證網域不符"

  printf "%-26s %-10s %-34s %s\n" "$h" "${ver:--}" "${issuer:0:34}" "$status"
done

printf -- "%.0s─" {1..100}; printf "\n"
cat <<'EOF'
判讀:
  ✅ 正常           = 公共 CA 簽發，TLS 未被解密
  ⚠️ 疑似 MITM      = Issuer 出現公司名/Proxy 工具，代表有 SSL inspection
  ⚠️ 憑證網域不符  = 連到的不是真正的該站點
EOF