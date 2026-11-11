#!/usr/bin/env python3
"""淘寶訂單資料提取 / 補重量 / 裁切序号 的小工具。

子命令
------
extract  讀取淘寶訂單 Excel → 產生 R0（無重量）/ R2（含重量）markdown
weights  由既有 R0/R2 markdown 補上重量，另存新檔
trim     由第 N 筆（含）之後全部刪除，就地更新檔案

用法
----
python orders.py extract 订单数据-20260926.xlsx -o 订单数据整理-20260926-R0.md
python orders.py extract 订单数据-20260926.xlsx -o out-R0.md -w weights.txt
python orders.py weights 订单数据整理-20260926-R0.md -w weights.txt -o 订单数据整理-20260926-R2.md
python orders.py trim 订单数据整理-20260926-R0.md --from 19
"""
import argparse
import re
import sys
from pathlib import Path

import openpyxl

# CP950 主控台無法輸出中文，強制 UTF-8（與 notes_salary.py 一致）
sys.stdout.reconfigure(encoding='utf-8')

# 淘寶匯出欄位順序（含「（当前仅支持未完结订单）」等後綴時以位置為準）
COL_NO, COL_STATUS, COL_NAME, COL_PRICE, COL_LOGI_CO, COL_LOGI_NO = 0, 2, 4, 9, 11, 12
HEADER_TITLE = "# 訂單資料整理"
WEIGHT_RE = re.compile(r"(\S+)\s+台[灣湾]\s+([\d.]+)")
ORDER_RE = re.compile(r"^## #(\d+)", re.M)
LOGI_RE = re.compile(r"^(.+?)\s+(\S+)\s{2}$")

STATUS_LABEL = {
    "交易关闭": "(交易關閉)",
    "交易成功": "(交易成功)",
    "交易完成": "(交易成功)",
}


def load_orders(xlsx: str):
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    orders = []
    for r in list(ws.iter_rows(min_row=2, values_only=True)):
        if not r or r[COL_NO] is None or str(r[COL_NO]).strip() == "":
            # 訂單號為空 → 多款式子列，掛在上一筆訂單下
            if orders:
                orders[-1]["rows"].append(r)
            continue
        orders.append({"no": r[COL_NO], "status": r[COL_STATUS], "rows": [r]})
    wb.close()
    return orders


def money(v):
    """'￥182.00' / 182.0 / None → float（無法解析回傳 0.0）。"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"[\d.]+", str(v))
    return float(m.group()) if m else 0.0


def load_weights(path: str):
    if not path:
        return {}
    text = Path(path).read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in WEIGHT_RE.finditer(text)}


def render(orders, weights=None):
    """產生 markdown 內文；weights 為 None 時不輸出重量行。"""
    weights = weights or {}
    lines = [HEADER_TITLE, ""]
    for i, o in enumerate(orders, 1):
        h = o["rows"][0]
        logi, no = h[COL_LOGI_CO], h[COL_LOGI_NO]
        lines += [f"## #{i:02d}", "", f"{h[COL_NAME]}  ", f"實付金額 {h[COL_PRICE]}  "]
        if no:
            lines.append(f"{logi} {no}  ")
            if no in weights:
                lines.append(f"{no} 台灣 {weights[no]}")
        else:
            lines.append(STATUS_LABEL.get(o["status"], "(無物流單號)") + "  ")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def report(orders, weights):
    have = [o["rows"][0][COL_LOGI_NO] for o in orders if o["rows"][0][COL_LOGI_NO]]
    matched = [n for n in have if n in weights]
    missing = [n for n in have if n not in weights]
    extra = sorted(set(weights) - set(have))
    print(f"訂單 {len(orders)} 筆（其中有物流單號 {len(have)} 筆）")
    if weights:
        print(f"對應成功 {len(matched)} 筆 / 缺漏 {len(missing)} 筆")
        for n in missing:
            print(f"  缺重量: {n}")
        for n in extra:
            print(f"  重量清單多餘（無對應訂單）: {n}")
    multi = [o["no"] for o in orders if len(o["rows"]) > 1]
    for o in orders:
        if len(o["rows"]) > 1:
            sub = sum(money(r[8]) for r in o["rows"])
            total = money(o["rows"][0][COL_PRICE])
            flag = "OK" if abs(sub - total) < 0.01 else "!! 不一致"
            print(f"  多款式 {o['no']}: {len(o['rows'])} 列，各列商品金額合計 {sub:.2f} / 首列實付 {total:.2f} {flag}")


def cmd_extract(a):
    orders = load_orders(a.xlsx)
    weights = load_weights(a.weights)
    Path(a.output).write_text(render(orders, weights if weights else None), encoding="utf-8")
    print(f"已輸出 {a.output}")
    report(orders, weights)


def cmd_weights(a):
    orders = load_orders(a.xlsx) if a.xlsx else None
    weights = load_weights(a.weights)
    if orders is None:
        raise SystemExit("weights 模式需以 -x/--xlsx 指定來源 Excel（或直接改用 extract -w）")
    Path(a.output).write_text(render(orders, weights), encoding="utf-8")
    print(f"已輸出 {a.output}")
    report(orders, weights)


def cmd_trim(a):
    p = Path(a.file)
    keep, stop = [], False
    for line in p.read_text(encoding="utf-8").split("\n"):
        m = ORDER_RE.match(line)
        if m:
            stop = int(m.group(1)) >= a.start
        if not stop:
            keep.append(line)
    txt = "\n".join(keep).rstrip("\n") + "\n"
    p.write_text(txt, encoding="utf-8")
    print(f"{p} -> 保留 #01~#{(a.start - 1):02d}，共 {len(ORDER_RE.findall(txt))} 筆")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="Excel → markdown")
    e.add_argument("xlsx")
    e.add_argument("-o", "--output", required=True)
    e.add_argument("-w", "--weights", help="物流重量清單（純文字檔）")
    e.set_defaults(func=cmd_extract)

    w = sub.add_parser("weights", help="既有 markdown 補重量")
    w.add_argument("md")
    w.add_argument("-x", "--xlsx", help="來源 Excel")
    w.add_argument("-w", "--weights", required=True)
    w.add_argument("-o", "--output", required=True)
    w.set_defaults(func=cmd_weights)

    t = sub.add_parser("trim", help="由第 N 筆（含）之後刪除")
    t.add_argument("file")
    t.add_argument("--from", dest="start", type=int, required=True)
    t.set_defaults(func=cmd_trim)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
