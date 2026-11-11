# comfyui-qwen-image-edit

ComfyUI + Qwen-Image-2.1 改圖工作流。完整說明見 [SKILL.md](SKILL.md)。

## 內容

| 檔案 | 用途 |
|---|---|
| `workflows/qwen21_image_edit_UI.json` | **UI 格式**，直接拖進 ComfyUI（附使用說明 Notes 節點） |
| `workflows/qwen21_image_edit_api.json` | API 格式，單圖改圖（腳本用） |
| `workflows/qwen21_multiref_api.json` | API 格式，多圖參考／服裝轉移（腳本用） |
| `scripts/run_wf.py` | 執行 API 格式工作流並等待結果 |

## 快速開始

ComfyUI 啟動後（預設 8188）：

```powershell
python scripts\run_wf.py workflows\qwen21_image_edit_api.json
```

輸出圖在 `ComfyUI-Shared\output\`。

UI 格式則是把 `workflows\qwen21_image_edit_UI.json` 拖進 ComfyUI 視窗。

## 兩個必要設定

1. 文字編碼器必須是 `qwen3vl_8b_int8_convrot.safetensors`
2. `cfg` = 1、`resolution` = 0、prompt 內以 `<image1>` 指代參考圖

詳見 SKILL.md 的「陷阱 1」與「陷阱 2」。
