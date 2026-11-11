#!/bin/bash
# macOS: 網路加速設定輔助（安全、可逆）
# 用法: ./mac-tune-network.sh [檢查|套用|還原]

MODE="${1:-檢查}"
BACKUP="$HOME/.network-port-check/dns-backup.txt"

set_dns() {
  local svc="$1"; shift
  echo "  設定 $svc DNS 為: $*"
  networksetup -setdnsservers "$svc" "$@"
}

get_svc() { networksetup -listallnetworkservices 2>/dev/null | tail -n +2 | head -1; }

case "$MODE" in
  檢查)
    echo "════════ 目前設定 ════════"
    svc=$(get_svc)
    echo "  網路服務: $svc"
    echo "  DNS: $(networksetup -getdnsservers "$svc" 2>/dev/null | tail -n +2 | tr '\n' ' ')"
    echo ""
    echo "════════ 建議值 ════════"
    echo "  1. DNS       → 8.8.8.8 + 168.95.1.1 (fallback)"
    echo "  2. 搜尋網域  → 留白（圖書館內網服務可能需解析）"
    echo "  3. WiFi 頻段 → 需手動在「系統設定 › 網路 › Wi-Fi › 詳細資料 › 硬體」勾 5GHz"
    echo ""
    echo "用法: $0 套用   或   $0 還原"
    ;;

  套用)
    mkdir -p "$(dirname "$BACKUP")"
    svc=$(get_svc)
    networksetup -getdnsservers "$svc" 2>/dev/null | tail -n +2 > "$BACKUP"
    echo "已備份目前 DNS 到 $BACKUP"
    set_dns "$svc" 8.8.8.8 8.8.4.4 168.95.1.1
    echo ""
    echo "完成。驗證:"
    networksetup -getdnsservers "$svc"
    echo ""
    echo "⚠️ 提醒: 這只改善首次 DNS 查詢，不會提升下載頻寬。"
    echo "⚠️ 若連到需要內網 DNS 的環境（如校園/公司），請把該 DNS 加回去。"
    ;;

  還原)
    if [ ! -f "$BACKUP" ]; then echo "找不到備份檔 $BACKUP"; exit 1; fi
    svc=$(get_svc)
    mapfile -t olddns < "$BACKUP"
    echo "還原為: ${olddns[*]}"
    if [ ${#olddns[@]} -eq 0 ]; then
      networksetup -setdnsservers "$svc" empty
    else
      set_dns "$svc" "${olddns[@]}"
    fi
    networksetup -getdnsservers "$svc"
    ;;
  *)
    echo "用法: $0 [檢查|套用|還原]"; exit 1;;
esac