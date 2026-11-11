> 改寫自 keon/browser-control（MIT, Om Labs）的 `skills/domain-skills/google-flights/scraping.md`，內文保留原文。
> 本機對應指令請對照 `SKILL.md` 的〈指令對照表〉。
> 路徑對應：上游 `domain-skills/<site>/<file>` → 本機 `reference/sites/<site>--<file>`；上游 `interaction-skills/<file>` → 本機 `reference/interaction/<file>`。
> 同資料夾兄弟檔案已扁平化為：`flight-search.md` → `reference/sites/google-flights--flight-search.md`。

# Google Flights — CLI interaction guide

Google Flights is an SPA. Use `inspect`/`observe` for refs, then batch clicks and
small DOM checks.

Useful pattern:

```sh
browser-control open "https://www.google.com/travel/flights/"
browser-control inspect | head -120
```

For form state verification, query visible buttons/inputs rather than dumping the
whole page:

```sh
browser-control eval "JSON.stringify(Array.from(document.querySelectorAll('button,input,[role=button],[role=combobox]')).slice(0,80).map(e=>({text:(e.innerText||e.value||e.ariaLabel||e.placeholder||'').trim(), aria:e.getAttribute('aria-label'), role:e.getAttribute('role')})))"
```

Batch related actions with `--from-stdin`; verify the final state with one compact
`eval` or `inspect --query` before answering.
