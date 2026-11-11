#!/bin/bash
# macOS: 網站可達性 + 真封鎖判定（兩層驗證，區分 4xx 與真封鎖）
# 用法: ./mac-test-websites.sh [檔案.json]

FILE="${1:-}"

if [ -n "$FILE" ]; then
  SITES=$(python3 -c "
import json,sys
for x in json.load(open('$FILE')):
    print(x['u'])
")
else
  SITES="https://www.google.com
https://www.youtube.com
https://github.com
https://pypi.org
https://registry.npmjs.org
https://www.apple.com
https://<CORP_DOMAIN_SHORT>.com.tw
https://www.tpc.gov.tw
https://speed.cloudflare.com
https://1.1.1.1"
fi

printf "%-42s %-8s %-9s %-9s\n" "URL" "狀態" "總時間" "TCP"
printf -- "%.0s─" {1..72}; printf "\n"

echo "$SITES" | while read -r url; do
  [ -z "$url" ] && continue
  out=$(curl -sS -o /dev/null -m 10 \
    -w "%{http_code} %{time_total} %{time_connect}" "$url" 2>/dev/null)

  if [ -z "$out" ]; then
    # 第一層失敗 → 裸 TCP 443 複驗，排除 PowerShell/UA 語意假陽性
    host=$(echo "$url" | sed -E 's|https?://([^/]+).*|\1|')
    if nc -z -G 4 -w 4 "$host" 443 >/dev/null 2>&1; then
      printf "%-42s %-8s %-9s %-9s\n" "$url" "[REACH]" "n/a" "443通"
    else
      printf "%-42s %-8s %-9s %-9s\n" "$url" "[BLOCK]" "n/a" "443死"
    fi
    continue
  fi

  code=$(echo "$out" | cut -d' ' -f1)
  total=$(echo "$out" | cut -d' ' -f2)
  conn=$(echo "$out" | cut -d' ' -f3)

  case "$code" in
    2*) tag="[ OK ]" ;;
    3*) tag="[REACH]" ;;
    4*|5*) tag="[REACH]" ;;
    000) tag="[BLOCK]" ;;
    *) tag="[$code]" ;;
  esac
  printf "%-42s %-8s %-9s %-9s\n" "$url" "$tag" "${total}s" "${conn}s"
done

printf -- "%.0s─" {1..72}; printf "\n"
cat <<'EOF'
狀態說明:
  [ OK ]    2xx，完全正常
  [REACH]  伺服器有回應(4xx/5xx)，網路可達，非封鎖
  [BLOCK]  真的連不上(裸 TCP 443 也失敗)
  [DNS]    網域無法解析(可能網域本來就不存在)

判讀: 只有單一網站失敗幾乎都是服務端問題，不是防火牆。
EOF