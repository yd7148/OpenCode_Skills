---
name: mate-engine-anim-patch
description: 擴充已編譯 Unity 的 Mate Engine X（MateEngineX，桌面虛擬伴侶/桌寵）的動作數量——把 AvatarAnimatorController 的 totalIdleAnimations / DANCE_CLIP_COUNT 常數提高，讓 BlendTree 中已存在但未輪播的 idle/舞蹈動畫全部啟用。流程：dnfile+dncil 反組譯 Assembly-CSharp.dll 定位 .ctor 常數、UnityPy 驗證 AnimatorController BlendTree 實際 clip 數、Mono.Cecil 重寫 IL、dnfile 全量驗證。Use when asked to 增加 Mate 動作 / 增加 idle 數量 / 增加舞蹈數量 / 擴充 mate 動作 / mate idle 輪播 / patch MateEngine 動畫計數 / mate engine anim patch。
---

# Mate Engine X 動作數量擴充（Idle / Dance）

針對已編譯 Unity（Mono）的 Mate Engine X（`MateEngineX.exe`）——**無原始碼**，只能改
`MateEngineX_Data\Managed\Assembly-CSharp.dll`。目標是把 BlendTree 中**已存在但被常數寫死而沒輪播**
的動畫全部啟用。

## 核心事實（X3.3.0，Unity 6000.2.6f2）

| 項目 | 值 |
|---|---|
| 動畫控制器 | `AvatarAnimatorControllerV2 1`（sharedassets0.assets，AnimatorController pathid **554**） |
| 類別 | `AvatarAnimatorController`（TypeDef 索引 **62**） |
| 欄位 token | `totalIdleAnimations` = **0x04000144**、`DANCE_CLIP_COUNT` = **0x04000147** |
| 預設值（.ctor） | `totalIdleAnimations` = `ldc.i4.s 10`；`DANCE_CLIP_COUNT` = `ldc.i4.5` |
| 誰寫入欄位 | **僅 .ctor**，場景/設定檔不覆寫 → patch ctor 即生效 |
| 未 patch 檔案大小 | 595,456 bytes（TypeDef 487 / MethodDef 2718） |

> **token 計算陷阱**：欄位 token 的 RID 是 **Field 表的全域列號**，不是 type-relative 索引。
> TypeDef 62 的欄位從 Field 表第 **321 (0x141)** 列起算，所以 `totalIdleAnimations` 是
> `0x04000000 | 321+3 = 0x04000144`。若用「TypeDef 索引 << 16 | 欄位序號」算出
> `0x043E0003` 是**錯的**，會完全對不上 IL。

## 環境工具（Temp 會被清理，必須能重建）

`%LOCALAPPDATA%\Temp\opencode` 底下的工具**會被系統 Temp 清理抹掉**，不能假設它還在。
工具鏈重建（一次搞定 pip + NuGet + csc）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\rebuild_tools.ps1
$env:MATE_TOOLS = "$env:LOCALAPPDATA\Temp\opencode"
```

| 工具 | 取得方式 |
|---|---|
| dnfile + dncil | `pip install --target=%TEMP%\opencode\matedlltools dnfile dncil` |
| UnityPy | `pip install --target=%TEMP%\opencode\unitypy UnityPy` |
| Mono.Cecil | NuGet `Mono.Cecil/0.11.4` 的 `lib\net40\Mono.Cecil.dll`（`.nupkg` 就是 zip，但 `Expand-Archive` 只認 `.zip` 副檔名） |
| PatchField.exe | `csc /target:exe /out:PatchField.exe /r:Mono.Cecil.dll scripts\PatchField.cs`（.NET Framework csc：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`） |
| Python | 3.10 可用 |

**`PatchField.cs` 原始碼在 `scripts/PatchField.cs`**，DLL 才是產物，不要只留 exe。

驗證腳本（皆吃 `MATE_TOOLS` 環境變數）：

| 腳本 | 用途 |
|---|---|
| `scripts/verify_ctor.py <dll>` | 反組譯 `.ctor`，印出兩個常數現值並判定是否已 patch |
| `scripts/verify_blendtree.py [assets]` | 驗證 BlendTree 葉子數，決定常數該設多大 |
| `scripts/sweep_dll.py <dll>` | 全量反組譯每支 MethodDef，確認重寫 IL 沒弄壞任何 method |

## 目標檔案位置

`Assembly-CSharp.dll` 位於 **解壓後資料夾**內，不同下載來源編號不同，請自行確認：

```
<解壓根目錄>\MateEngineX_Data\Managed\Assembly-CSharp.dll
<解壓根目錄>\MateEngineX_Data\Managed\Assembly-CSharp.dll.bak   (自己建立的備份)
<解壓根目錄>\MateEngineX_Data\sharedassets0.assets               (驗證 BlendTree 用)
<解壓根目錄>\MateEngineX_Data\StreamingAssets\CustomDances\       (外部 .unity3d 舞蹈，非本流程)
```

備份由本流程建立：把原檔複製成 `.bak`。**還原就是把 `.bak` 複製回 `Assembly-CSharp.dll`。**

## 流程

### 0. 先關掉程式

Unity 會鎖住 `Assembly-CSharp.dll`，寫入前必須先結束 `MateEngineX.exe`。

### 1. 反組譯 .ctor，確認現況

```powershell
python scripts\verify_ctor.py "<Managed>\Assembly-CSharp.dll"
```

實作方式：dnfile 找 `AvatarAnimatorController` 的 `.ctor`（TypeDef 62 的
`MethodList` 內 `Name == ".ctor"`），dncil `read_method_body_from_bytes` 反組譯。
RVA→檔案偏移：text section 內 `off = PointerToRawData + (rva - VirtualAddress)`。
`.ctor` 內共有 9 個欄位常數，其中兩個是要改的。

### 2. 用 UnityPy 驗證 BlendTree 真的有那麼多 clip（關鍵！）

```powershell
python scripts\verify_blendtree.py "<MateEngineX_Data>\sharedassets0.assets"
```

**X3.3.0 實測結果**（`AvatarAnimatorControllerV2 1`，26 個 StateConstant，115 個 clip）：

| State | 用途 | 依序葉子 | unique |
|---:|---|---|---:|
| **4** | IDLE | clipID `0..18`（前 19 個）→ 之後 `20..28` | 28 |
| **2** | DANCE | clipID `42..54`（前 13 個）→ 之後 `56..59` | 17 |

> ⚠️ **上限是「依序葉子的前 N 個」，不是 unique 總數。**
> IDLE 的 unique 是 28，但那 9 個 `20..28` 是 **HUS_IDLE（男性待機）**。
> 設 28 會讓男性待機混進女性預設輪播。**所以 19 才是正確值。**
> 迴圈是 `Random.Range(0, count)` / `% count`，即取節點索引 0..count-1。

### 3. 值能否用「同長度位元組」表示？

- 可（1 byte 定值 opcode）：直接 hex 改。例如 `ldc.i4.s 19`（`1F 13`）替換 `ldc.i4.s 10`（`1F 0A`）。
- 不可（`ldc.i4.5` 只有 1 byte，改 `ldc.i4.s 13` 會 +1 byte → 位移後續所有 method RVA）：
  **必須用 Mono.Cecil 重寫**。

```powershell
$pf = "$env:MATE_TOOLS\cecil\PatchField.exe"
$in  = "<Managed>\Assembly-CSharp.dll"
& $pf $in                          stage1.dll totalIdleAnimations 19
& $pf "$env:MATE_TOOLS\stage1.dll" stage2.dll DANCE_CLIP_COUNT    13
```

⚠️ 不要手工插入 byte（會讓整份檔 `.text` 之後所有 method RVA 錯位）。
⚠️ 兩個欄位要分兩次跑，串成 in → stage1 → stage2，不要同時改兩個常數。

### 4. 驗證（寫入前 → 新檔，確認後才覆蓋）

- `python scripts\sweep_dll.py stage2.dll` → 反組譯成功 2521 支、**失敗 0**
- `python scripts\verify_ctor.py stage2.dll` → `ldc.i4.s 19` / `ldc.i4.s 13`
- TypeDef / MethodDef 列數不變（487 / 2718）、`.ctor` 指令數不變（33）、檔案大小不變（595,456）
- 覆蓋前先備份 `.bak`

### 5. 還原

把 `Assembly-CSharp.dll.bak` 複製回 `Assembly-CSharp.dll` 即可。

## 已驗證實機結果（2026-10-03）

以下為實際套用並驗證過的案例，可作為「成功長什麼樣」的基準。
**路徑是該台機器的實際解壓位置，每台不同，套用時請自行替換。**

| 項目 | 值 |
|---|---|
| 版本 | `Public.Release.X3.3.0-HOTFIX`（GitHub 免費版） |
| 解壓位置 | `D:\2026-08-Vtuber\31-Public.Release.X3.3.0-HOTFIX\` |
| Unity | 6000.2.6f2 |
| patch 前 SHA256 | `C29522F2F86ECCC709CE71C18D07CD40AD35BC3DD5501F11FA2D789A39B83148` |
| patch 後 SHA256 | `9FA261E7742EE5FD…`（大小不變，仍 595,456 bytes） |

`verify_ctor.py` 輸出：

```
未 patch : ldc.i4.s 10 → totalIdleAnimations ; ldc.i4.5 → DANCE_CLIP_COUNT
已 patch : ldc.i4.s 19 → totalIdleAnimations ; ldc.i4.s 13 → DANCE_CLIP_COUNT
```

`verify_blendtree.py` 輸出（26 個 StateConstant、115 個 clip）：

```
IDLE  (State 4): 前 19 葉 = clipID 0..18 ; unique 28（20..28 是 HUS_IDLE）
DANCE (State 2): 前 13 葉 = clipID 42..54 ; unique 17
```

`sweep_dll.py` 輸出：

```
MethodDef 總數 : 2718
反組譯成功    : 2521   （差額 197 為無 method body 的抽象／extern 項）
失敗          : 0
TypeDef / MethodDef / Field / MemberRef = 487 / 2718 / 3597 / 2242（patch 前後一致）
```

`.ctor` 指令數 33、檔案大小 595,456 bytes 在 patch 前後皆未變 → Cecil 吸收了
`ldc.i4.5` → `ldc.i4.s` 的 +1 byte，**沒有造成後續 method RVA 位移**。

啟動驗證（`Player.log`，`%USERPROFILE%\AppData\LocalLow\Shinymoon\MateEngineX\`）：

```
[Receiver] Awake! Avatar: DEFAULT AVATAR      ← 角色正常載入
[Receiver] Aktiviert: DEFAULT AVATAR (VRMModel)
[Steamworks.NET] SteamAPI_Init() failed      ← 免費版正常，與 patch 無關
無任何 IL / JIT / TypeLoad 例外
```

⚠️ 遊戲更新後 `Assembly-CSharp.dll` 會被換掉，需重新套用並重新驗證
（常數與 clip 數有可能隨版本變動，務必先跑 `verify_blendtree.py` 確認上限）。

## 常見陷阱

- **UnityPy 的結構幾乎全是 `OffsetPtr` 包裝**，每層存取屬性前都要 `.data`：
  `cc.m_LayerArray[0].data`、`sp.data`、`blends[0].data.m_NodeArray`，
  **遞迴走 `m_ChildIndices` 時節點本身也要 unwrap**。
  忘記 unwrap 會**靜默得到 0 個 clip**（不是報錯），極易誤判成「沒有更多動畫」——
  所以這一步的輸出一定要人工確認 State 4 / State 2 的數量有意義。
  另外 clipID 的哨兵值是 `0xFFFFFFFF`，要排除。
- 先確認欄位「只被 .ctor 寫」：掃全 DLL 的 `stfld token(0x04000144/0x04000147)`。若 SaveLoadHandler 也寫
  就從設定面著手。
- 確認「場景沒有序列化覆寫」：用 UnityPy 掃所有 MonoBehaviour 原始位元組，若找不到
  特徵序列 `[int count][float 12.0][float 3.0][int 5][bool][bool][float 15.0][float 2.0]`，
  代表元件是執行期 AddComponent，ctor 預設才會生效。
- **不要用 PowerShell heredoc 跑 python**（5.1 不支援 `<<`）；寫成 `.py` 檔再 `python x.py`。
- **驗證完要重新開機程時，用完全 detached 的方式啟動**，否則前景 shell 被中止會連帶收掉子行程：
  ```powershell
  Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
                   -Arguments @{ CommandLine = '"<path>\MateEngineX.exe"' }
  ```
  用 `Start-Process` 再在同一個指令裡 `Start-Sleep` 會卡住，且工具逾時中止時
  Unity 會被一起殺掉，看起來像「patch 完就開不起來」——其實 log 裡是乾淨的 `Shutdown`。
- 免費版啟動時 `[Steamworks.NET] SteamAPI_Init() failed` 屬正常，與 patch 無關。
- 舞蹈的 13：clipID 42..54，`DANCE_CLIP_COUNT=13` 會讓 `Random.Range(0,13)` 與 `%13` 涵蓋所有舞步。
- Husbando 模式（isMale）只有 9 個 HUS_IDLE，IdleIndex≥8 會 clamp 到最後一個，屬正常行為。
