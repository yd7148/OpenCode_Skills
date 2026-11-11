"""執行 ComfyUI 工作流（API 格式）並等待結果。

用法:
    python run_wf.py <workflow.json> [port]

預設連 127.0.0.1:8188。輸出每個產生圖片的檔名。
注意: 工作流的 autogrow 插槽必須用扁平點號鍵，例如 "images.image_1"，
      用巢狀 dict 會被靜默丟棄（參考圖不會進入節點）。
"""
import json
import sys
import time
import urllib.request

PORT = "8188"
if len(sys.argv) > 1:
    WF_PATH = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = sys.argv[2]
else:
    WF_PATH = "workflow.json"

BASE = f"http://127.0.0.1:{PORT}"

with open(WF_PATH, "r", encoding="utf-8-sig") as f:
    prompt = json.load(f)

data = json.dumps({"prompt": prompt, "client_id": "opencode"}).encode("utf-8")
req = urllib.request.Request(
    f"{BASE}/prompt", data=data, headers={"Content-Type": "application/json"}
)
try:
    res = json.loads(urllib.request.urlopen(req, timeout=120).read())
except urllib.error.HTTPError as e:
    print("SUBMIT FAILED:", e.read().decode()[:500])
    sys.exit(1)

if res.get("node_errors"):
    print("NODE ERRORS:", json.dumps(res["node_errors"], ensure_ascii=False)[:800])
    sys.exit(1)

pid = res["prompt_id"]
print("queued:", pid)

deadline = time.time() + 3600
while time.time() < deadline:
    hist = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}", timeout=30).read())
    if pid in hist:
        h = hist[pid]
        print("completed:", h.get("status", {}).get("completed"))
        for out in h.get("outputs", {}).values():
            for img in out.get("images", []):
                print("IMAGE:", img.get("filename"), img.get("subfolder"), img.get("type"))
        break
    time.sleep(3)
else:
    print("TIMEOUT")
