> 改寫自 keon/browser-control（MIT, Om Labs）的 `skills/interaction-skills/scrolling.md`，內文保留原文。
> 本機對應指令請對照 `SKILL.md` 的〈指令對照表〉。
> 路徑對應：本目錄檔名與上游一致，文中提到的 `interaction-skills/<file>.md` 即本目錄的 `<file>.md`。

# Scrolling

Prefer deterministic scroll commands and compact checks.

```sh
browser-control scroll -600     # down; negative dy matches mouse-wheel convention
browser-control scroll 600      # up
browser-control eval "window.scrollTo(0, document.body.scrollHeight); 'bottom'"
browser-control eval "JSON.stringify({y: scrollY, h: innerHeight, total: document.body.scrollHeight})"
```

After scrolling, verify with `observe | head -80` or a targeted `eval`; avoid repeated
full-page dumps.
