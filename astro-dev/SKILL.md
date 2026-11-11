---
name: astro-dev
description: |-
  Build and debug Astro sites: content collections, islands architecture,
  rendering modes, and image/SEO basics. Use when creating Astro pages or
  layouts, defining or querying a content collection, choosing between
  static/server/hybrid rendering, adding a React/Vue/Svelte island, or a
  component isn't interactive, isn't appearing in the sitemap, or content
  collection entries aren't showing up.
  Examples:
  - user: "add a blog section" → set up a content collection with the
    glob loader and a dynamic [slug] route
  - user: "this button doesn't do anything" → check for a missing
    client: directive on the framework component
  - user: "make this page fetch fresh data on every request" → switch
    that route to server rendering
  - user: "my new markdown file isn't showing up" → check the loader
    glob pattern and the collection schema
license: MIT
---

# Astro Development

Help the user build Astro sites that ship the right amount of
JavaScript — which for most pages is none — and that use the content
layer and rendering model correctly rather than fighting it.

## Content collections (Content Layer API)

Collections are defined in `src/content.config.ts` at the project root,
not inside `src/content/`:

```ts
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishDate: z.coerce.date(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { posts };
```

Query and render entries:

```astro
---
import { getCollection, render } from 'astro:content';

const posts = await getCollection('posts', ({ data }) => !data.draft);
const post = posts[0];
const { Content } = await render(post);
---
<Content />
```

**Common failure modes:**
- A new markdown file doesn't show up → the `glob` pattern or `base`
  path doesn't actually match it, or frontmatter fails the zod schema
  (check the build error, it names the offending field)
- `render()` throws → you're calling it on a collection entry object
  directly instead of awaiting `getCollection`/`getEntry` first
- Slugs look wrong → with the glob loader, the entry `id` is derived
  from the file path; rename the file rather than adding a separate
  `slug` field unless you need them to differ

## Rendering modes

Set per-project in `astro.config.mjs` (`output: 'static' | 'server'`),
and per-route when `output: 'server'` is the default but a route should
behave differently, using `export const prerender = true` (or `false`)
in that page's frontmatter.

- **Static**: built once at deploy time. Use for marketing pages,
  docs, blogs — anything that doesn't need per-request data. Best for
  SEO and Core Web Vitals because there's no server round-trip.
- **Server**: rendered on each request. Use when a page needs
  request-specific data (auth state, search params hitting a live
  API) that can't be known at build time.
- **Hybrid**: default to one mode, override specific routes with
  `prerender`. Common pattern: static marketing site with one
  server-rendered API route or personalized page.

Don't reach for `server` output just because a component fetches data —
if that data is the same for every visitor, fetch it at build time in
the frontmatter instead and keep the page static.

## Islands architecture & client directives

Framework components (React, Vue, Svelte, etc.) render to static HTML
by default and ship **no JavaScript** unless given a client directive:

| Directive | Hydrates |
|---|---|
| `client:load` | immediately on page load |
| `client:idle` | when the main thread is idle |
| `client:visible` | when the component scrolls into view |
| `client:media={query}` | when a media query matches |
| `client:only="react"` | skip server render, client-render only |

If a component "isn't interactive," the missing client directive is the
first thing to check — Astro is doing exactly what was asked (static
HTML) by default. Pick the laziest directive that still feels
responsive: `client:visible` for below-the-fold widgets, `client:idle`
for non-critical interactivity, `client:load` only for things needed
immediately (e.g. a search box in the hero).

Don't wrap an entire page in one big hydrated component to make one
small part interactive — isolate the interactive piece into its own
small component and hydrate only that.

## Images

Use the built-in `Image` component rather than a raw `<img>` for
anything that benefits from optimization:

```astro
---
import { Image } from 'astro:assets';
import hero from '../assets/hero.jpg';
---
<Image src={hero} alt="Description a screen reader needs" width={1200} height={630} />
```

`width`/`height` (or `inferSize` for remote images) are required so
Astro can prevent layout shift. Local images in `src/assets/` get
automatic format conversion and responsive sizing; remote images need
an explicit allowlist in `astro.config.mjs` under `image.domains` or
`image.remotePatterns`.

## SEO basics that depend on configuration, not just markup

- `site` must be set in `astro.config.mjs` to an absolute URL — without
  it, the sitemap integration and any `Astro.url`-based canonical tags
  silently produce wrong or relative URLs.
- The `@astrojs/sitemap` integration only includes routes that actually
  get built — a page excluded by `prerender = false` in a static build
  won't appear in `dist/`, so it won't appear in the sitemap either.
- Put `<title>`, meta description, and Open Graph tags in a shared
  `Layout.astro` that every page passes props into, rather than
  duplicating the `<head>` per page.

See `references/content-collections-quickstart.md` and
`references/client-directives-cheatsheet.md` for condensed lookups.
