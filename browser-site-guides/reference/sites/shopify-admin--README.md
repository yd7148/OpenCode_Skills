> 改寫自 keon/browser-control（MIT, Om Labs）的 `skills/domain-skills/shopify-admin/README.md`，內文保留原文。
> 本機對應指令請對照 `SKILL.md` 的〈指令對照表〉。
> 路徑對應：上游 `domain-skills/<site>/<file>` → 本機 `reference/sites/<site>--<file>`；上游 `interaction-skills/<file>` → 本機 `reference/interaction/<file>`。
> 同資料夾兄弟檔案已扁平化為：`embedded-apps.md` → `reference/sites/shopify-admin--embedded-apps.md`、`knowledge-base.md` → `reference/sites/shopify-admin--knowledge-base.md`、`polaris-inputs.md` → `reference/sites/shopify-admin--polaris-inputs.md`。

# shopify-admin

browser-control patterns for `admin.shopify.com` and embedded Shopify apps.

## Files in this folder

- `embedded-apps.md` — every Shopify app runs in an iframe; how to target it
- `polaris-inputs.md` — Polaris React inputs reject synthetic value setters; use CDP type_text
- `knowledge-base.md` — automating the Shopify Knowledge Base App for FAQ entries

## When to use these

You're driving Shopify admin and need to add / edit / configure something. The Shopify admin UI is large and many surfaces are embedded apps — first check whether what you need is in an embedded app (most apps under `admin.shopify.com/store/<store>/apps/<app-slug>/...` are).

## When to skip

- If the operation is read-only product / inventory data → use the **Storefront API** (HTTP) instead, much faster
- If the store has a custom admin app with API token provisioned → use the **Admin API** (GraphQL or REST) instead, no UI scraping
- If you're editing theme code → use the **Shopify CLI** (`shopify theme push`) — don't touch the theme editor UI

The browser is the right tool only when:
- The setting / app exposes no API
- The change is one-time or rare enough not to justify scripting
- You're discovering / exploring the admin (e.g., finding selectors for a future automation)

## Authentication

Mike (or the human owner) must be logged into `admin.shopify.com` in the Chrome session that browser-control attaches to. browser-control does NOT log in — it inherits the human's session.

If you hit `accounts.shopify.com` redirect, stop and ask the human to log in. Don't type credentials.

## Polaris is in transition (Jan 2026 onward)

Shopify is migrating its design system from React-based Polaris to Web-Components-based Polaris. Most legacy admin surfaces are still React. Newer surfaces (Catalog Mapping, parts of Settings) may be web components.

Screenshot first. If you see `<s-text-field>` or `<s-button>` web component tags → use the web component pattern. If you see `[class*="Polaris-"]` React class names → use the CDP keystrokes pattern in `polaris-inputs.md`.
