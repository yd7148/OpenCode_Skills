"""全量驗證 Assembly-CSharp.dll：對每支有 method body 的 MethodDef 反組譯，
確保 patch 後沒有任何 method 損毀（重寫 IL 最怕的就是位移錯誤）。

用法:
    set MATE_TOOLS=<工具根目錄>
    python sweep_dll.py <Assembly-CSharp.dll>

通過標準: 反組譯成功數 > 0 且 失敗 == 0，且
TypeDef=487 / MethodDef=2718（X3.3.0 未 patch 與已 patch 皆應相同）。
"""
import os
import sys

BASE = os.environ.get(
    "MATE_TOOLS", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "opencode"))
sys.path.insert(0, os.path.join(BASE, "matedlltools"))

# 預設 cp950 主控台無法輸出非 ASCII，強制 UTF-8 並降級錯誤字串
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes

if len(sys.argv) < 2:
    sys.exit(__doc__)

DLL = sys.argv[1]
pe = dnfile.dnPE(DLL)
rows = pe.net.mdtables.MethodDef.rows

print("=== 全量 sweep ===")
print("  檔案 :", DLL)
print("  MethodDef 總數:", len(rows))

sections = [(s.VirtualAddress, s.Misc_VirtualSize,
             s.PointerToRawData) for s in pe.sections]


def read_at(rva, size=16384):
    for va, vsize, praw in sections:
        if va <= rva < va + vsize:
            with open(DLL, "rb") as f:
                f.seek(praw + (rva - va))
                return f.read(size)
    return None


ok = fail = 0
fails = []
for i, m in enumerate(rows, start=1):
    rva = getattr(m, "Rva", 0)
    if not rva:
        continue
    data = read_at(rva)
    if data is None:
        fail += 1
        fails.append((i, str(m.Name), "no section"))
        continue
    try:
        CilMethodBody(CilMethodBodyReaderBytes(data))
        ok += 1
    except Exception as e:
        fail += 1
        fails.append((i, str(m.Name), "%s: %s" % (type(e).__name__, e)))

print("  反組譯成功:", ok)
print("  失敗      :", fail)
if fails:
    print()
    print("  失敗明細 (前 20):")
    for i, nm, err in fails[:20]:
        print("    [%d] %s -> %s" % (i, nm, err))

print()
print("=== 表格列數 ===")
for t in ("TypeDef", "MethodDef", "Field", "MemberRef"):
    print("  %-10s: %d" % (t, len(getattr(pe.net.mdtables, t).rows)))

print()
print("=== 判定 ===")
print("  結果:", "[OK] 通過 (0 失敗)" if fail == 0 and ok > 0
      else "[FAIL] 有失敗，勿覆蓋原檔")
