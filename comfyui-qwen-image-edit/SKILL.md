---
name: comfyui-qwen-image-edit
description: 用 ComfyUI + Qwen-Image-2.1 做圖像編輯（改圖／換裝／服裝轉移／多圖參考）與文生圖，產出可直接拖入 ComfyUI 的工作流 JSON，並用 /prompt API 批次執行。涵蓋兩個會「不報錯但結果全錯」的無聲陷阱：(1) 文字編碼器選錯——`qwen3.5_9b_..._pe_i2i` 會被偵測成 QWEN35_9B 而繞過 QwenImage21Tokenizer，缺少 keep_vision／image_slots，輸出滿版雜訊；(2) V3 autogrow 插槽（`TextEncodeQwenImage21` 的 image_1~image_16）在 API 必須用扁平點號鍵 `"images.image_1"`，用巢狀 dict 會被靜默丟棄、整條流程退化成純文生圖、保留度全失。另含官方參數對齊（cfg=1、resolution=0、prompt 內以 `<image1>` 指代參考圖）。Use when asked to ComfyUI 改圖 / Qwen-Image-2.1 / Qwen Image 2.1 改圖 / image edit / 圖像編輯 / 換衣服 / 服裝轉移 / 虛擬試穿 / 多圖參考 / ComfyUI 工作流 / comfy workflow JSON / ComfyUI API 執行 / 輸出滿版雜訊 / noise output / 改圖沒保留 / 參考圖沒作用。
license: MIT
---

# comfyui-qwen-image-edit — ComfyUI + Qwen-Image-2.1 改圖

用 ComfyUI 的 Qwen-Image-2.1 做圖像編輯與文生圖，重點在**兩個會靜默失敗的陷阱**（不報錯、照樣出圖，但結果全錯）。

## 觸發情境

- 要用 ComfyUI 改圖、換裝、服裝轉移、虛擬試穿、抠背景、風格轉換。
- 要產出可拖進 ComfyUI 的工作流 JSON。
- 要用腳本批次跑工作流（不開瀏覽器）。
- **輸出滿版彩色雜訊**，或參考圖完全沒作用（改圖變成重新生成）。
- 「Qwen-Image-2.1 是不是要另外下 edit 版權重？」→ 不用，統一模型。

## 前置：環境定位

ComfyUI Desktop 的實際路徑**會變**（版本更新後目錄可能從 `ComfyUI` 變成 `ComfyUI (2)`），不要寫死：

```powershell
Get-ChildItem "D:\Comfy-Desktop\ComfyUI-Installs" -Directory
```

模型庫是**跨版本共用**的，穩定路徑 `ComfyUI-Shared`：

| 類型 | 路徑 |
|---|---|
| diffusion_models | `D:\Comfy-Desktop\ComfyUI-Shared\models\diffusion_models` |
| text_encoders | `D:\Comfy-Desktop\ComfyUI-Shared\models\text_encoders` |
| vae | `D:\Comfy-Desktop\ComfyUI-Shared\models\vae` |
| input / output | `D:\Comfy-Desktop\ComfyUI-Shared\input` / `output` |

**torch 在 `.venv`，不在 `standalone-env`**。`standalone-env\python.exe` 跑 `main.py` 會 `ModuleNotFoundError: No module named 'torch'`：

```powershell
$c = "<ComfyUI-Installs路徑>\<版本>\ComfyUI"
& "$c\.venv\Scripts\python.exe" -c "import torch;print(torch.__version__)"
```

ComfyUI 的預設 API port 是 8188（Comfy Desktop 自己佔用）。開自己的實例除錯時換 port：

```powershell
Start-Process -FilePath "$c\.venv\Scripts\python.exe" `
  -ArgumentList "-s","main.py","--port","8189","--windows-standalone-build" `
  -WorkingDirectory $c -RedirectStandardOutput "$env:TEMP\dbg.log" `
  -RedirectStandardError "$env:TEMP\dbg.err" -WindowStyle Hidden
```

> 關除錯實例時務必比對 `CommandLine` 精確指定 Port，**不要用寬鬆的 PID 條件**；誤殺會讓 Comfy Desktop 自動重啟並可能換到新的版本目錄。

## 模型配置（Qwen-Image-2.1）

**2.1 是統一模型** — 同一份權重同時做 t2i 與 edit，**不需要另外找 edit 版權重**。

| 角色 | 檔案 | 備註 |
|---|---|---|
| diffusion | `qwen_image_2.1_int8_convrot.safetensors` | 6.76 GB，int8 convrot，適合小 VRAM |
| text encoder | **`qwen3vl_8b_int8_convrot.safetensors`** | 必須是這個，見陷阱 1 |
| vae | `qwen_image_2.1_vae_bf16.safetensors` | 644 MB，64 通道 RGBA，16× 壓縮 |

`qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors` 是 **prompt enhancer（PE）**，
用途是在改圖前先改寫指令，**不是主編碼器**。誤用會輸出雜訊（陷阱 1）。

## 陷阱 1：文字編碼器選錯 → 滿版雜訊

`TextEncodeQwenImage21` 依賴 `QwenImage21Tokenizer`，它會處理 `keep_vision` 與 `image_slots`。
但 `comfy/sd.py` 對文字編碼器的分支是**先看偵測到的架構、再看 clip type**：

- `qwen3vl_8b_*` → 偵測為 `QWEN3VL_8B` → 走 `CLIPType.QWEN_IMAGE` 分支 → 拿到 `QwenImage21Tokenizer` ✔
- `qwen3.5_9b_*` → 偵測為 `QWEN35_9B` → **在更早的分支就被攔截**，永遠拿不到 `QwenImage21Tokenizer` ✘

少了 `image_slots`，`comfy/ldm/qwen_image21/model.py` 的 `build_sequence()`
在拼接參考圖 latent 時位置全錯 → **跑完不報錯，直接輸出滿版雜訊**。

驗證方式（不要靠猜）：

```python
import comfy.sd
from comfy.utils import load_torch_file
sd = load_torch_file(path)
print(comfy.sd.detect_te_model(sd))
st = comfy.sd.load_text_encoder_state_dicts([sd], clip_type=comfy.sd.CLIPType.QWEN_IMAGE)
print(type(st.tokenizer).__name__)
print("keep_vision" in st.tokenizer.tokenize_with_weights.__code__.co_varnames)
```

期望 `QwenImage21Tokenizer` + `True`。若得到 `Qwen35ImageTokenizer_` / `False` 就是錯的。

> 載入 8B 級 TE 做這類探測在 CPU 上可能觸發存取違規（`-1073741819`）。
> 改用輸出圖尺寸當探針（見陷阱 2），或在有 GPU 的 server 環境下做。

## 陷阱 2：autogrow 插槽用巢狀 dict → 參考圖被丟棄

`TextEncodeQwenImage21` 的參考圖是 **V3 autogrow 插槽**（`image_1`~`image_16`）。
API 提交時必須用**扁平點號鍵**，因為 `comfy_api/latest/_io.py` 的 `finalize_prefix()`
以 `".".join(...)` 組出鍵名，`build_nested_inputs()` 再用 `values.pop(key)` 取值：

```jsonc
// ✗ 錯：會被靜默丟棄，節點仍執行、仍出圖，但參考圖從未進入
"images": { "image_1": ["4", 0] }

// ✓ 對
"images.image_1": ["4", 0]
"images.image_2": ["5", 0]
```

**症狀**：節點不報錯、圖有出，但改圖變成「照 prompt 重新生成」，臉部姿勢背景全失；
而且 `resolution` 怎麼調都沒反應。

**診斷法：用輸出尺寸反推**。`nodes_qwen.py` 的
`latent_w = latent_h = resolution or 1024` 是初值，只有在參考圖真的進入迴圈時
才會被原圖尺寸覆寫：

| 輸入 | 輸出尺寸 | 結論 |
|---|---|---|
| 扁平鍵 + `resolution: 0` | 跟隨原圖（如 896×1152） | 圖進來了 ✔ |
| 無圖 + `resolution: 0` | 1024×1024 | 停在初值，圖沒進來 ✘ |

原圖是直幅、輸出卻是 1024×1024 → 幾乎可以確定 autogrow 沒接上。
這個「尺寸不變」比看圖更早、更可靠地暴露問題。

## 官方參數對齊

| 參數 | 值 | 說明 |
|---|---|---|
| `cfg` | **1** | 2.1 官方路徑要 1。調高會偏離參考圖 |
| `resolution` | **0** | 0 = 沿用 image_1 原尺寸（不縮放）。設數字會重算尺寸、可能讓構圖偏移 |
| `steps` | 25 | 官方 40–50，25 是模板起始值。進階 sampler 可再少 |
| `sampler` / `scheduler` | `euler` / `simple` | 官方路徑 |
| `denoise` | 1.0 | 由全零 latent 從頭生成，參考圖只當條件 |
| `negative_prompt` | 空 | `cfg=1` 時不生效 |

**prompt 必須用 `<image1>` / `<image2>` 指代參考圖**：

```
讓 <image1> 中的人物穿上 <image2> 的淺藍色牛仔襯衫，保留 <image1> 的臉部、姿勢、背景與構圖
```

`image_1` 是編輯目標，其餘是參考來源。不寫 `<image1>` 模型不知道要改哪張。

## 節點串接

`TextEncodeQwenImage21` 一個節點同時產出 **positive / negative / latent**，
所以不需要另外接 `EmptySD3LatentImage` 或 `VAEEncode`：

```
UNETLoader ─┐
            ├→ QwenImage21Cache → KSampler → VAEDecode → SaveImage
CLIPLoader ─┼→ TextEncodeQwenImage21 ┤(positive)   ↑
VAELoader ──┤        (vae)           ├(negative)   │
LoadImage ──┴───────(images.image_1)  └(latent) ────┘
```

`QwenImage21Cache` 開 `auto` 會把 prefix KV cache 放在空閒 VRAM 再退 RAM，
記憶體吃緊時可加速；設 `off` 則每步重算（較慢，但可用來排除 cache 干擾）。

## 執行工作流（腳本化）

ComfyUI API 在 8188。`prompt` 欄位就是那個扁平鍵格式的工作流 JSON：

```python
import json, time, urllib.request

with open("wf.json", encoding="utf-8") as f:
    prompt = json.load(f)

data = json.dumps({"prompt": prompt, "client_id": "opencode"}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data,
                             headers={"Content-Type": "application/json"})
pid = json.loads(urllib.request.urlopen(req, timeout=120).read())["prompt_id"]

while True:
    h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}", timeout=30).read())
    if pid in h:
        for out in h[pid].get("outputs", {}).values():
            for img in out.get("images", []):
                print(img["filename"])
        break
    time.sleep(3)
```

實測腳本見 `scripts/run_wf.py`。

## 排查順序

出問題時照這個順序查，**先驗證尺寸再來看圖**：

1. **輸出是 1024×1024 但原圖不是？** → autogrow 沒接上（陷阱 2）。先修格式。
2. **輸出滿版雜訊？** → 文字編碼器選錯（陷阱 1）。用上面的探針腳本確認 tokenizer。
3. **改圖變成重新生成、保留度全失？** → 多半是 1 的連鎖（圖沒進來 = 沒條件 = 純 t2i）。
4. **構圖偏移、比例不對？** → `resolution` 沒設 0，被強制重算尺寸。
5. **整體偏離原圖、風格變了？** → `cfg` 沒設 1。
6. **模型不知道改哪張？** → prompt 沒寫 `<image1>`。

`/object_info/<NodeName>` 可直接查節點實際接受的輸入鍵，是最快的確認方式：

```powershell
$o = Invoke-RestMethod "http://127.0.0.1:8188/object_info/TextEncodeQwenImage21"
$o.TextEncodeQwenImage21.input.required.PSObject.Properties.Name
```

## 產出物

工作流 JSON 兩種格式用途不同：

- **UI 格式**（有 `nodes`/`links`/`widgets_values`）— 可直接拖進 ComfyUI 操作。
- **API 格式**（`{"1": {"class_type":..., "inputs":...}}`）— 給腳本跑。

兩者要各自維護；從 UI 格式匯出 API 格式最保險（避免手刻節點漏欄位）。

## 已知限制

- 單張 896×1152 約 3.5 分鐘（RTX A2000 12GB 跑 int8）；1.0 MP 內尚可，2K 會明顯變慢。
- `resolution` 上限 4096，但 2.1 原生 2K；超過 VRAM 極限會 OOM。
- PE（prompt enhancer）模型可選，能讓指令更完整、代名詞彙更好，但每次多跑一輪改寫。
  本 skill 的工作流預設關閉，需要時再接 `Qwen35` 節點並開 `refine_prompt`。
