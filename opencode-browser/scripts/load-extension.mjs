#!/usr/bin/env node
// 透過 CDP 把 OpenCode Browser 擴充功能載入到正在執行的 Chrome。
// Chrome 137+ 已移除 --load-extension，只能走 CDP 的 Extensions.loadUnpacked。
//
// usage: node load-extension.mjs [port] [extensionDir]
//   port         預設 9222（Chrome 需以 --remote-debugging-port=<port> 啟動）
//   extensionDir 預設 %USERPROFILE%\.opencode-browser\extension

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const port = process.argv[2] || "9222";
const extensionDir =
  process.argv[3] || path.join(os.homedir(), ".opencode-browser", "extension");

if (!fs.existsSync(path.join(extensionDir, "manifest.json"))) {
  console.error(`[opencode-browser] 找不到 manifest.json：${extensionDir}`);
  console.error("先執行：npx @different-ai/opencode-browser@latest install");
  process.exit(1);
}

async function waitForCdp(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) return await res.json();
    } catch {
      /* 尚未就緒 */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`CDP 端點未就緒：http://127.0.0.1:${port}/json/version`);
}

const version = await waitForCdp();
const ws = new WebSocket(version.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();

ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message);
    pending.delete(message.id);
  }
});
await new Promise((resolve) => ws.addEventListener("open", resolve));

function send(method, params = {}) {
  const message = { id: ++id, method, params };
  return new Promise((resolve) => {
    pending.set(message.id, resolve);
    ws.send(JSON.stringify(message));
  });
}

const result = await send("Extensions.loadUnpacked", { path: extensionDir });
if (result.error) {
  console.error(`[opencode-browser] 載入失敗：${result.error.message}`);
  process.exit(1);
}

console.log(`[opencode-browser] 擴充功能已載入，ID = ${result.result.id}`);
console.log(`[opencode-browser] 來源：${extensionDir}`);
console.log("[opencode-browser] 提醒：此載入方式僅在本次 Chrome 工作階段有效。");
ws.close();
