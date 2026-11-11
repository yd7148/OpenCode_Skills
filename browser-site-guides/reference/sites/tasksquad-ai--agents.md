> 改寫自 keon/browser-control（MIT, Om Labs）的 `skills/domain-skills/tasksquad-ai/agents.md`，內文保留原文。
> 本機對應指令請對照 `SKILL.md` 的〈指令對照表〉。
> 路徑對應：上游 `domain-skills/<site>/<file>` → 本機 `reference/sites/<site>--<file>`；上游 `interaction-skills/<file>` → 本機 `reference/interaction/<file>`。
> 同資料夾兄弟檔案已扁平化為：`auth.md` → `reference/sites/tasksquad-ai--auth.md`、`tasks.md` → `reference/sites/tasksquad-ai--tasks.md`。

# TaskSquad — Agents

Field-tested against tasksquad.ai on 2026-05-03 using a logged-in Chrome session.

## URL

```
https://tasksquad.ai/dashboard/agents       # Agents list for current project
```

## Agent list

Agents are the daemon workers that execute tasks. Each agent card shows:
- Name
- Status badge (`active` / `inactive` / `running` / `waiting_input` / `paused`)
- Role (optional label set by maintainer)
- Last-seen timestamp

Navigate to agents via the sidebar link "Agents".

## Creating an agent

Maintainer/owner only. Click **"New agent"** (or similar CTA in the agents view).

Provide:
- **Name** — display name for the agent
- **Role** (optional) — a freeform string describing the agent's specialty

After creation, a **token** is generated. Copy it immediately — it is shown only once. The daemon uses this token to authenticate.

```
tsq install --token <TOKEN>
```

Tokens are created via `POST /teams/:teamId/tokens` with `{ label, agent_id }`.

## Agent statuses

| Status          | Meaning                                            |
|-----------------|----------------------------------------------------|
| `active`        | Daemon connected, ready to accept tasks            |
| `inactive`      | Daemon not connected (no recent ping)              |
| `running`       | Currently executing a task                         |
| `waiting_input` | Paused mid-task, waiting for user reply            |
| `paused`        | Manually paused — will not pick up new tasks       |

## Agent actions (maintainer / owner)

| Action       | Trigger                  | Effect                                              |
|--------------|--------------------------|-----------------------------------------------------|
| Pause/Resume | Toggle button on card    | Sets `paused` flag — agent ignores new tasks        |
| Reset        | "Reset" button           | Clears the agent's running state (use if stuck)     |
| Delete       | Delete button / menu     | Permanently removes agent and its tokens            |
| Edit role    | Role edit control        | Updates the agent's role label                      |

## Token management

Tokens are per-agent credentials. Each token has a label. A maintainer can:
- **Generate a new token** — use when setting up a new machine or rotating credentials
- Tokens cannot be viewed after creation; only revoked implicitly by deleting the agent

## Gotchas

- **Status is driven by daemon pings**, not task state. An agent can be `active` while no task is running.
- **`inactive` ≠ paused.** Inactive means the daemon process is offline. Paused means a maintainer explicitly suspended it via the UI.
- **Only owners and maintainers can create agents or generate tokens.** Members see the list but cannot modify it.
- **Token is shown once.** If you miss copying it, you must generate a new one — there is no "reveal token" button.
- **Reset is for recovery only.** Use it when an agent is stuck in `running` after a daemon crash. Do not reset agents mid-task.
