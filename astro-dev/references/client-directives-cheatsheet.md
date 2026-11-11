# Client Directives — Quick Lookup

| Directive | Hydrates when | Use for |
|---|---|---|
| `client:load` | immediately | above-the-fold, needed-instantly UI (hero search box) |
| `client:idle` | main thread is idle | secondary widgets, non-critical interactivity |
| `client:visible` | scrolls into viewport | below-the-fold components, long pages |
| `client:media={query}` | media query matches | components only relevant at certain breakpoints |
| `client:only="framework"` | client-side only, no SSR | components that can't render server-side (browser-only APIs) |

## Decision shortcut

1. Does it need to work the instant the page loads? → `client:load`
2. Is it below the fold or non-critical? → `client:visible` or `client:idle`
3. Does it only make sense on one breakpoint? → `client:media`
4. Does it depend on `window`/browser APIs at render time? → `client:only`

## Symptom → likely cause

- "The component renders but clicking does nothing" → missing client
  directive entirely; it shipped as static HTML
- "It works after I scroll, not before" → `client:visible` is working
  as intended — switch to `client:load` if it must be interactive
  immediately
- "It throws `window is not defined` during build" → it's trying to
  hydrate during the server render pass; add `client:only` instead of
  a directive that still does an initial server render
