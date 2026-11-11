#!/usr/bin/env bash
# macOS 磁碟空間掃描（唯讀，不做任何刪除）
# 用法: ./scan-disk.sh [輸出目錄]

set -uo pipefail

OUT_DIR="${1:-$HOME/Desktop/mac清理紀錄}"
mkdir -p "$OUT_DIR"
REPORT="$OUT_DIR/scan-$(date +%Y%m%d-%H%M).txt"

exec > >(tee "$REPORT") 2>&1

echo "=============================================="
echo " macOS 磁碟空間掃描"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

echo
echo "## 1. 磁碟總覽"
echo "真實可用空間請看 /System/Volumes/Data"
df -h /System/Volumes/Data /

echo
echo "## 2. 家目錄各層"
du -sh ~/* ~/.[a-z]* 2>/dev/null | sort -rh | head -20

echo
echo "## 3. 使用者 Library"
du -sh ~/Library/* 2>/dev/null | sort -rh | head -18

echo
echo "## 4. 使用者 Application Support (常藏大魚)"
du -sh ~/Library/"Application Support"/* 2>/dev/null | sort -rh | head -15

echo
echo "## 5. 使用者 Caches"
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -15

echo
echo "## 6. 系統 Library"
du -sh /Library/* 2>/dev/null | sort -rh | head -12

echo
echo "## 7. /Library/Application Support (Adobe 常在此)"
du -sh "/Library/Application Support"/* 2>/dev/null | sort -rh | head -15

echo
echo "## 8. Adobe 細項"
du -sh "/Library/Application Support/Adobe"/* 2>/dev/null | sort -rh | head -12
echo
echo "--- Premiere Pro 版本目錄 (SpeechESL 語言模型常達 13G+)"
du -sh "/Library/Application Support/Adobe/Premiere Pro"/*/* 2>/dev/null | sort -rh | head -10

echo
echo "## 9. /private/var (勿手動處理 /private/var/db)"
du -sh /private/var/* 2>/dev/null | sort -rh | head -8

echo
echo "## 10. /Applications 前 25 名"
du -sh /Applications/* 2>/dev/null | sort -rh | head -25

echo
echo "## 11. CloudStorage (刪前務必驗證同步狀態)"
du -sh ~/Library/CloudStorage/* 2>/dev/null | sort -rh
echo
echo "同步程序檢查:"
ps aux | grep -iE "synology|onedrive|cloud-drive" | grep -v grep || echo "  (無同步程序執行中)"
echo
echo "FileProvider 掛載:"
mount | grep -iE "onedrive|clouddocs|fileprovider" || echo "  (無雲端掛載)"

echo
echo "## 12. 開發者工具 (可考慮移除)"
du -sh ~/.cache ~/.local ~/.npm ~/.docker ~/go ~/Library/Developer 2>/dev/null | sort -rh

echo
echo "=============================================="
echo "掃描完成: $REPORT"
echo "提醒: /private/var/db、/System、/private/var/vm 請勿手動操作"
echo "=============================================="