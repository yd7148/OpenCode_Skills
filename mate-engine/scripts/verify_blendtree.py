"""驗證 MateEngineX_Data/sharedassets0.assets 中 AvatarAnimatorController
(pathid 554) 的 BlendTree 實際 clip 數，決定 totalIdleAnimations /
DANCE_CLIP_COUNT 該設多大。

用法:
    set MATE_TOOLS=<工具根目錄>
    python verify_blendtree.py [sharedassets0.assets]

X3.3.0 實測結果:
    IDLE  = State 4，依序葉子前 19 個 = clipID 0..18  (19 個 PET_IDLE)
                              第 20 個起 = clipID 20..28 (9 個 HUS_IDLE)
    DANCE = State 2，依序葉子前 13 個 = clipID 42..54  (13 個 PET_DANCING)
                              第 14 個起 = clipID 56..59 (4 個額外)
=> 安全上限是「依序葉子的前 N 個」，不是 unique 總數。
   IDLE 設 28 會讓男性 HUS_IDLE 混進女性預設輪播，所以要設 19。
"""
import os
import sys

BASE = os.environ.get(
    "MATE_TOOLS", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "opencode"))
sys.path.insert(0, os.path.join(BASE, "unitypy"))
import UnityPy

# 預設 cp950 主控台無法輸出非 ASCII，強制 UTF-8 並降級錯誤字串
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_ASSETS = (r"D:\2026-08-Vtuber\31-Public.Release.X3.3.0-HOTFIX"
                  r"\MateEngineX_Data\sharedassets0.assets")
ASSETS = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ASSETS
PATHID = 554

# UnityPy 的 AnimatorController 相關結構幾乎全部是 OffsetPtr 包裝，
# 每層存取屬性前都要 unwrap，遞迴時也要 unwrap，否則會靜默得到空結果。
def unwrap(o):
    return o.data if hasattr(o, "data") else o


env = UnityPy.load(ASSETS)
obj = next(o for o in env.objects
           if o.type.name == "AnimatorController" and o.path_id == PATHID)
d = obj.read()
cc = d.m_Controller

clip_names = []
for c in getattr(d, "m_AnimationClips", None) or []:
    try:
        clip_names.append(c.m_Name)
    except Exception:
        clip_names.append("?")

print("=== AnimatorController pathid %d ===" % PATHID)
print("  name                :", d.m_Name)
print("  m_AnimationClips    :", len(clip_names))
print("  m_StateConstant     :", len(cc.m_StateMachineArray[0].data.m_StateConstantArray))

states = cc.m_StateMachineArray[0].data.m_StateConstantArray


def ordered_leaves(nodes):
    """回傳『依節點索引順序』的葉子 clipID（不去重）。"""
    out = []

    def walk(n):
        n = unwrap(n)
        kids = getattr(n, "m_ChildIndices", None)
        if kids is not None and len(kids) > 0:
            for k in kids:
                walk(nodes[int(k)])
            return
        cid = getattr(n, "m_ClipID", None)
        if cid is not None and int(cid) != 0xFFFFFFFF:
            out.append(int(cid))

    for n in nodes:
        walk(n)
    return out


info = {}
print()
print("=== 含 BlendTree 的 State ===")
for si, sp in enumerate(states):
    st = unwrap(sp)
    blends = getattr(st, "m_BlendTreeConstantArray", None)
    if not blends:
        continue
    leaves = []
    for bp in blends:
        leaves += ordered_leaves(unwrap(bp).m_NodeArray)
    if leaves:
        info[si] = (leaves, sorted(set(leaves)))
        print("  State %-3d leaves=%-4d unique=%-4d %s"
              % (si, len(leaves), len(info[si][1]), info[si][1]))

print()
print("=== IDLE (State 4) ===")
if 4 in info:
    lv, uq = info[4]
    print("  依序 leaves 前 25:", lv[:25])
    print("  unique 數量       :", len(uq))
    print("  count=19 會取到   :", lv[18], "(預期 18)")
    print("  count=28 會多取到 :", sorted(set(lv[19:])) or "(無)", "→ 這是 HUS_IDLE，不可加")

print()
print("=== DANCE (State 2) ===")
if 2 in info:
    lv, uq = info[2]
    print("  依序 leaves 前 25:", lv[:25])
    print("  unique 數量       :", len(uq))
    print("  count=13 會取到   :", lv[12], "(預期 54)")
else:
    print("  !! State 2 無 BlendTree，State 編號可能變動，需重新定位")

print()
print("=== 結論 ===")
if 4 in info and 2 in info:
    print("  totalIdleAnimations -> 19  (目前 10)")
    print("  DANCE_CLIP_COUNT    -> 13  (目前  5)")
