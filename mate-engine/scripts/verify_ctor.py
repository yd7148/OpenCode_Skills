"""驗證 MateEngineX_Data/Managed/Assembly-CSharp.dll 中 AvatarAnimatorController
的 totalIdleAnimations / DANCE_CLIP_COUNT 現值。

用法:
    set MATE_TOOLS=<工具根目錄>            # 含 matedlltools/ 與 unitypy/ 子目錄
    python verify_ctor.py <Assembly-CSharp.dll>

未 patch 預期:  totalIdleAnimations <- ldc.i4.s 10 , DANCE_CLIP_COUNT <- ldc.i4.5
已 patch 預期:  totalIdleAnimations <- ldc.i4.s 19 , DANCE_CLIP_COUNT <- ldc.i4.s 13
"""
import os
import sys

BASE = os.environ.get(
    "MATE_TOOLS", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "opencode"))
sys.path.insert(0, os.path.join(BASE, "matedlltools"))

import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
from dncil.clr.token import Token, StringToken

# 預設 cp950 主控台無法輸出非 ASCII，強制 UTF-8 並降級錯誤字串
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

if len(sys.argv) < 2:
    sys.exit(__doc__)

DLL = sys.argv[1]
print("=== 目標檔案 ===")
print(" ", DLL)
print()

pe = dnfile.dnPE(DLL)
td = pe.net.mdtables.TypeDef
md = pe.net.mdtables.MethodDef

print("=== 表格總數 ===")
print("TypeDef rows  :", len(td.rows))
print("MethodDef rows:", len(md.rows))

tidx = trow = None
for i, row in enumerate(td.rows, start=1):
    if "AvatarAnimatorController" in str(row.TypeName):
        tidx, trow = i, row
        print("=== TypeDef ===")
        print("  index(1-based):", tidx)
        print("  full name     : %s.%s" % (row.TypeNamespace, row.TypeName))
        break

if trow is None:
    sys.exit("!! 找不到 AvatarAnimatorController")


def rows_of(lst):
    return [e.row if hasattr(e, "row") else e for e in lst]


# ---- 欄位 token 是「全域 RID」，不是 type-relative ----
# token = 0x04000000 | <Field 表全域列號(1-based)>
# TypeDef 62 的欄位起始於 Field 表第 321(0x141) 列，因此
#   totalIdleAnimations = 0x04000144 (第 324 列)
#   DANCE_CLIP_COUNT    = 0x04000147 (第 327 列)
GIDX = {id(r): i for i, r in enumerate(pe.net.mdtables.Field.rows, start=1)}

FT = {}
for f in rows_of(trow.FieldList):
    FT[0x04000000 | (GIDX.get(id(f), 0) & 0x00FFFFFF)] = str(f.Name)

IDLE = next((t for t, n in FT.items() if n == "totalIdleAnimations"), None)
DANCE = next((t for t, n in FT.items() if n == "DANCE_CLIP_COUNT"), None)
print("=== 目標欄位 token ===")
print("  totalIdleAnimations  0x%08X" % (IDLE or 0))
print("  DANCE_CLIP_COUNT     0x%08X" % (DANCE or 0))

methods = rows_of(trow.MethodList)
ctor = next((m for m in methods if str(m.Name) == ".ctor"), None)
if ctor is None:
    sys.exit("!! 找不到 .ctor")
print("=== TypeDef 方法數 ===", len(methods))

rva = ctor.Rva
off = None
for s in pe.sections:
    if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
        off = s.PointerToRawData + (rva - s.VirtualAddress)
        print("=== .ctor ===")
        print("  RVA         : 0x%X" % rva)
        print("  section     : %s" % s.Name.rstrip(b"\x00").decode())
        print("  file offset : 0x%X" % off)
        break
if off is None:
    sys.exit("!! 找不到對應 section")

with open(DLL, "rb") as f:
    f.seek(off)
    body = CilMethodBody(CilMethodBodyReaderBytes(f.read(8192)))
print("  instructions: %d" % len(body.instructions))
print()

print("=== .ctor IL：ldc.* 與 stfld ===")
pairs = {}
prev = None
for ins in body.instructions:
    op, operand = ins.opcode.name, ins.operand
    val = None
    txt = ""
    if isinstance(operand, Token):
        val = operand.value
        txt = "0x%08X" % val
        if val in FT:
            txt += "  (%s)" % FT[val]
    elif isinstance(operand, StringToken):
        txt = str(operand)
    elif operand is not None:
        txt = repr(operand)
    if op.startswith("ldc.i4") or op == "stfld":
        print("   %-12s %s" % (op, txt))
        if op == "stfld" and val in (IDLE, DANCE):
            pairs[val] = prev
    prev = (op, txt)

print()
print("=== 目前寫入值 ===")
got = {}
for label, tok in (("totalIdleAnimations", IDLE), ("DANCE_CLIP_COUNT", DANCE)):
    p = pairs.get(tok)
    got[label] = p[0] if p else None
    print("  %-20s <- %s" % (label, (p[0] + " " + p[1]).strip() if p else "NOT FOUND"))

print()
print("=== 判定 ===")
if got["totalIdleAnimations"] == "ldc.i4.s" and got["DANCE_CLIP_COUNT"] == "ldc.i4.s":
    print("  已 patch (19 / 13)")
elif got["totalIdleAnimations"] == "ldc.i4.s" and got["DANCE_CLIP_COUNT"] == "ldc.i4.5":
    print("  未 patch (10 / 5)")
else:
    print("  非預期組合，請人工確認")
