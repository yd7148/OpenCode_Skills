#!/usr/bin/env node
// 維持「單一 session」的 OpenCode Browser 工具執行器。
//
// 為什麼需要：每次 `npx @different-ai/opencode-browser tool ...` 都是新的外掛 session，
// 而分頁所有權（claim）是 per-session、租約 300 秒。多步驟作業若每步開新的 session，
// 會出現「分頁被別的 session 佔住」。此腳本讓外掛常駐，用檔案佇列收指令。
//
// 用法：
//   1) 啟動：node browser-session.mjs
//      （工作目錄下會出現 .ocb-session\ 資料夾）
//   2) 丟指令：把 JSON 寫進 .ocb-session\jobs\<任意檔名>.json
//      {"tool":"browser_get_tabs","args":{}}
//   3) 取結果：.ocb-session\results\<同一檔名>.json
//      {"ok":true,"tool":"...","result":"..."} 或 {"ok":false,"error":"..."}
//
// 停止：在工作目錄建立 .ocb-session\STOP 檔即可。

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const WORK = path.join(process.cwd(), ".ocb-session");
const JOBS = path.join(WORK, "jobs");
const RESULTS = path.join(WORK, "results");
const STOP = path.join(WORK, "STOP");

fs.mkdirSync(JOBS, { recursive: true });
fs.mkdirSync(RESULTS, { recursive: true });

/** 找出已安裝的外掛（OpenCode 會快取 npm 套件到 ~/.cache/opencode/npm）。 */
function findPlugin() {
  const roots = [
    path.join(os.homedir(), ".cache", "opencode", "npm"),
    path.join(os.homedir(), ".config", "opencode", "node_modules"),
  ];
  const candidates = [];
  const push = (dir) => {
    const entry = path.join(dir, "dist", "plugin.js");
    if (fs.existsSync(entry)) candidates.push(entry);
  };

  for (const root of roots) {
    if (!fs.existsSync(root)) continue;

    // 情況一：<root>/@different-ai/opencode-browser@<version>/<hash>/node_modules/@different-ai/opencode-browser
    const scopeDir = path.join(root, "@different-ai");
    if (fs.existsSync(scopeDir)) {
      for (const pkg of fs.readdirSync(scopeDir, { withFileTypes: true })) {
        if (!pkg.isDirectory()) continue;
        const pkgDir = path.join(scopeDir, pkg.name);
        for (const version of fs.readdirSync(pkgDir, { withFileTypes: true })) {
          if (!version.isDirectory()) continue;
          push(path.join(pkgDir, version.name, "node_modules", "@different-ai", "opencode-browser"));
        }
      }
    }

    // 情況二：<root>/@different-ai/opencode-browser（直接安裝）
    push(path.join(scopeDir, "opencode-browser"));
  }

  if (!candidates.length) return null;
  // 取最新修改的一個
  candidates.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return candidates[0];
}

const pluginPath = findPlugin();
if (!pluginPath) {
  console.error("[opencode-browser] 找不到外掛 dist/plugin.js，請先執行 opencode plugin add @different-ai/opencode-browser");
  process.exit(1);
}

const mod = await import(pathToFileURL(pluginPath).href);
const instance = await (mod.default)({});
const tools = instance?.tool ?? {};
console.log(`[opencode-browser] session 就緒，工具 ${Object.keys(tools).length} 支`);
console.log(`[opencode-browser] 指令目錄：${JOBS}`);

let busy = false;
async function pump() {
  if (busy) return;
  if (fs.existsSync(STOP)) {
    console.log("[opencode-browser] 收到 STOP，結束。");
    process.exit(0);
  }
  busy = true;
  try {
    const files = fs.readdirSync(JOBS).filter((f) => f.endsWith(".json")).sort();
    for (const file of files) {
      const jobPath = path.join(JOBS, file);
      let request;
      try {
        request = JSON.parse(fs.readFileSync(jobPath, "utf8"));
      } catch (error) {
        fs.writeFileSync(path.join(RESULTS, file), JSON.stringify({ ok: false, error: `bad json: ${error.message}` }));
        fs.unlinkSync(jobPath);
        continue;
      }
      const tool = tools[request.tool];
      let payload;
      if (!tool) {
        payload = { ok: false, error: `unknown tool ${request.tool}` };
      } else {
        try {
          const result = await tool.execute(request.args ?? {}, {});
          payload = {
            ok: true,
            tool: request.tool,
            result: typeof result === "string" ? result : JSON.stringify(result),
          };
        } catch (error) {
          payload = { ok: false, tool: request.tool, error: String(error?.message ?? error) };
        }
      }
      fs.writeFileSync(path.join(RESULTS, file), JSON.stringify(payload, null, 2));
      fs.unlinkSync(jobPath);
      console.log(`[${new Date().toISOString()}] ${request.tool} -> ${payload.ok ? "ok" : "ERR"}`);
    }
  } finally {
    busy = false;
  }
}

setInterval(pump, 250);
