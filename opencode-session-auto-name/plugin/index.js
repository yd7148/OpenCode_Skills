/**
 * opencode-auto-name — OpenCode V2 plugin
 *
 * 讓 session 標題自動取自「第一次使用者 prompt 的總結」或「進行中 todo」。
 * 純規則式、0 Token、與模型無關。
 *
 * 設計說明（V1 → V2 移植要點）
 * ---------------------------------------------------------------------------
 * V1（opencode-auto-name v0.1.x，@opencode-ai/plugin ^1.x）
 *   export default function sessionNamePlugin(opts) {
 *     return async ({ client, project, directory }) => ({ event, dispose })
 *   }
 *   - 事件來自 V1 的 `hooks.event`
 *   - 更新標題：`client.session.update({ path: { id }, body: { title } })`
 *   - 第一則 user 訊息：`message.updated` 事件的 `msg.role === 'user'` + `msg.summary.title`
 *   - todo 來源：`todo.updated` 事件的 `props.todos`（找 `status === 'in_progress'`）
 *
 * V2（OpenCode 2.x，@opencode/plugin ^2.x）
 *   export default { id, setup(ctx) }
 *   - 事件：`ctx.event.subscribe({ signal })`（AsyncIterable，cleanup 時 abort）
 *   - 更新標題：`ctx.session.update({ sessionID, title })`
 *   - 第一則 user 訊息：`ctx.session.hook('prompt')` 的 `event.prompt.text`
 *   - todo 來源：V2 沒有 `todo.updated` 事件。改由 `session.tool.called` 事件觀察
 *     `todowrite` 工具呼叫的 `input.todos`（僅在 todowrite 工具可用時才有；本機未啟用）
 *
 * 實測限制（V2 runtime，2026-11-11 於 OpenCode v2.0.16 驗證）
 *   - `ctx.session.list` 型別定義存在但 runtime 不存在 → 本插件不使用
 *   - `ctx.session.remove` 同上 → 本插件不使用
 *   - `ctx.id` 為 undefined → plugin 自己的 id 需由 default export 提供
 *   - `ctx.options` 在未以物件格式宣告 options 時為 `{}`
 *
 * 本插件刻意**不 import `@opencode/plugin`**：實測純物件 default export（帶 id 與 setup）
 * 即可被 V2 載入，零相依可避免版本綁定與安裝失敗風險。
 *
 * 安裝位置與載入方式
 * ---------------------------------------------------------------------------
 * 放在 `~/.config/opencode/plugins/opencode-auto-name/` 即可被全域自動載入，
 * **不需要**在 `opencode.jsonc` 的 `plugins` 陣列宣告。
 *
 * 原因（實測 2026-11-11）：本機的 `~/.config/opencode/opencode.jsonc` 與
 * `D:\80-Opnecode\.opencode\opencode.jsonc` 是指向同一實體檔的**兩個 symlink**。
 * 在 `plugins` 陣列宣告相對路徑（如 `"./plugins/opencode-auto-name"`）時，
 * OpenCode 會依「宣告該條目的設定檔所在目錄」分別解析路徑，
 * 於是同一個 plugin 被載入兩次（一次路徑不存在、一次正常），
 * `opencode plugin list` 會出現重複列，且 options 只在其中一份生效。
 *
 * 因此：options 改由 `DEFAULT_CONFIG` 內建（`template: "{firstMessage}"`、
 * `maxLength: 50`，與原本 V1 設定一致）；仍可用 `ctx.options` 覆寫。
 *
 * 若確實需要以 options 覆寫，請改用**絕對路徑**宣告，避免 symlink 重複解析。
 */

const DEFAULT_CONFIG = {
  /**
   * 標題樣板。變數：{project} {task} {firstMessage} {messageCount} {model} {date} {time}
   *
   * 預設為 `{firstMessage}`：標題只取第一個訊息的總結（符合「第一 prompt 總結」需求）。
   * 若想要「有進行中 todo 時優先顯示 todo」，改回 `"{task || firstMessage}"`。
   *
   * 註：{task} 需要 opencode 啟用 todowrite 工具（experimental flag）才有來源，
   *     否則該變數恆為空，會自動 fallback 到 {firstMessage}。
   */
  template: "{firstMessage}",
  /** 摘要最大長度（字元） */
  maxLength: 50,
  /** 變更後延遲套用的去抖動毫秒數 */
  debounceMs: 10_000,
  /** 定期檢查間隔毫秒數；0 表示停用 */
  intervalMs: 60_000,
}

/** 去除開頭贅詞 */
const FILLER =
  /^(?:(?:i\s+)?(?:want\s+(?:to\s+)?|need\s+(?:to\s+)?|would\s+(?:like\s+)?to\s+|am\s+trying\s+to\s+)|can\s+(?:you\s+)?(?:please\s+)?|could\s+(?:you\s+)?(?:please\s+)?|hey\s+|hi\s+|hello\s+|please\s+)/i

/**
 * 智慧摘要：去贅詞 → 取首句 → 去尾標點 → 截斷
 * @param {string} text 原始文字
 * @param {number} maxLength 最大長度
 * @returns {string} 摘要
 */
function summarize(text, maxLength = 50) {
  let s = String(text || "").trim()
  s = s.replace(FILLER, "").trim()
  const match = s.match(/^.*?[.!?\n]|^[^.!?\n]+/)
  if (match) s = match[0].trim()
  s = s.replace(/[.!?]+$/, "").trim()
  if (s.length <= maxLength) return s
  return s.slice(0, maxLength).replace(/\s+\S*$/, "") + "…"
}

/**
 * 簡易樣板引擎：{var} 取代與 || 備援
 * @param {string} template 樣板
 * @param {Record<string, unknown>} vars 變數
 * @param {string} defaultValue 全部變數皆空時的預設值
 * @returns {string} 渲染結果
 */
function render(template, vars, defaultValue = "session") {
  return String(template).replace(/\{(\w+(?:\s*\|\|\s*\w+)*)\}/g, (_match, expr) => {
    const alternatives = expr.split(/\s*\|\|\s*/)
    for (const key of alternatives) {
      const val = vars[key]
      if (val !== undefined && val !== null && val !== "") return String(val)
    }
    return defaultValue
  })
}

/**
 * 由 todowrite 工具呼叫的 input 取出進行中的 todo 內容
 * @param {unknown} input 工具 input
 * @returns {string} 進行中 todo 的內容；無則空字串
 */
function currentTaskFromTodoInput(input) {
  if (!input || typeof input !== "object") return ""
  const todos = /** @type {{ todos?: unknown }} */ (input).todos
  if (!Array.isArray(todos)) return ""
  const active = todos.find((t) => t && typeof t === "object" && /** @type {{status?: string}} */ (t).status === "in_progress")
  return active ? String(/** @type {{content?: unknown}} */ (active).content || "") : ""
}

export default {
  id: "opencode-auto-name",

  /**
   * @param {any} ctx V2 plugin context
   */
  async setup(ctx) {
    const cfg = { ...DEFAULT_CONFIG, ...(ctx.options || {}) }

    // 專案名：V1 用 project.worktree 的最後一段
    const projectName =
      (ctx.location?.project?.canonical || ctx.location?.project?.directory || ctx.location?.directory || "")
        .split(/[\\/]/)
        .filter(Boolean)
        .pop() || "session"

    /** @type {Map<string, { firstMessage: string, task: string, messageCount: number, lastTitle: string, timer?: any }>} */
    const state = new Map()

    // ── 重要：V2 會為「每個專案/location」各啟動一份 plugin 實例 ──
    // 實測同一個 plugin 在 4~5 個專案各跑一次 setup，且每個實例都訂閱到「全域」事件。
    // 若不篩選 session，所���實例會競爭同一個 session 的標題，最後寫入者勝出，
    // 且用的是錯誤的 projectName fallback。
    // 因此只在 ctx.location 對應的 session 上動作。
    const myProjectID = ctx.location?.project?.id || ""
    const myDirectory = ctx.location?.directory || ""

    /**
     * 判斷某 session 是否屬於本實例的 location
     * @param {any} data 事件 data
     * @returns {boolean} 是否屬於本實例
     */
    function isMine(data) {
      if (!data) return false
      if (myProjectID && data.projectID) return data.projectID === myProjectID
      if (myDirectory && data.location?.directory) return data.location.directory === myDirectory
      return false
    }

    /** 取得（或建立）某 session 的狀態 */
    function slot(sessionID) {
      let s = state.get(sessionID)
      if (!s) {
        s = { firstMessage: "", task: "", messageCount: 0, lastTitle: "", timer: undefined }
        state.set(sessionID, s)
      }
      return s
    }

    /** 計算標題 */
    function buildTitle(s) {
      const vars = {
        project: projectName,
        task: s.task ? summarize(s.task, cfg.maxLength) : "",
        firstMessage: summarize(s.firstMessage, cfg.maxLength),
        messageCount: s.messageCount,
        model: "",
        date: new Date().toLocaleDateString("en-US", { month: "2-digit", day: "2-digit" }),
        time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }),
      }
      return render(cfg.template, vars, projectName)
    }

    /** 套用標題 */
    async function applyTitle(sessionID) {
      const s = state.get(sessionID)
      if (!s) return
      const title = buildTitle(s)
      if (!title || title === s.lastTitle) return
      try {
        await ctx.session.update({ sessionID, title })
        s.lastTitle = title
      } catch {
        // 靜默失敗：標題命名不應中斷主流程
      }
    }

    /** 去抖動排程 */
    function schedule(sessionID) {
      const s = slot(sessionID)
      if (s.timer) clearTimeout(s.timer)
      s.timer = setTimeout(() => {
        s.timer = undefined
        void applyTitle(sessionID)
      }, cfg.debounceMs)
    }

    // ── 第一則使用者訊息：prompt hook 是最直接可靠的來源 ──
    // V1 靠 message.updated 事件 + msg.summary.title；V2 直接用 prompt admission hook。
    // 註：prompt hook 只會送到「該 session 所屬 location」的 plugin 實例，
    //     但仍以 session 狀態表為準，避免重複排程。
    try {
      await ctx.session.hook("prompt", (event) => {
        const sessionID = event.sessionID
        const s = slot(sessionID)
        s.messageCount += 1
        if (!s.firstMessage) {
          const text = event.prompt?.text || ""
          if (text.trim()) s.firstMessage = text
        }
        schedule(sessionID)
      })
    } catch {
      // hook 註冊失敗不影響其他功能
    }

    // ── 事件訂閱：追蹤 session 建立、todo 寫入、閒置 ──
    const controller = new AbortController()
    void (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        const data = event.data || {}
        try {
          if (event.type === "session.created") {
            // 只處理本實例 location 的 session（見上方 isMine 說明）
            if (!isMine(data)) continue
            const s = slot(data.sessionID)
            s.lastTitle = data.title || ""
            s.firstMessage = ""
            s.task = ""
            s.messageCount = 0
          } else if (event.type === "session.tool.called") {
            // todowrite 工具的 input 含 todos（僅在該工具啟用時才會出現）
            const task = currentTaskFromTodoInput(data.input)
            if (task !== undefined && data.sessionID && state.has(data.sessionID)) {
              const s = slot(data.sessionID)
              s.task = task
              schedule(data.sessionID)
            }
          } else if (event.type === "session.idle" || event.type === "session.step.ended") {
            // 只對本實例已追蹤的 session 動作
            if (data.sessionID && state.has(data.sessionID)) schedule(data.sessionID)
          }
        } catch {
          // 單一事件處理失敗不應中斷訂閱
        }
      }
    })()

    // ── 定期檢查：保證最終一定套用（與 V1 的 intervalId 行為一致）──
    let intervalId
    if (cfg.intervalMs > 0) {
      intervalId = setInterval(() => {
        for (const sessionID of state.keys()) void applyTitle(sessionID)
      }, cfg.intervalMs)
      // 讓 Node 事件迴圈存活
      if (typeof intervalId.unref === "function") intervalId.unref()
    }

    // ── cleanup：對應 V1 的 dispose ──
    return () => {
      controller.abort()
      if (intervalId) clearInterval(intervalId)
      for (const s of state.values()) if (s.timer) clearTimeout(s.timer)
      state.clear()
    }
  },
}
