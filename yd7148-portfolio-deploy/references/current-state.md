# Verified state — 2026-10-04

Machine used for verification: Windows, user `admin`, drives `C:` and `D:` only
(no `<PROJECT_ROOT_B>`). Local clones: `<USERPROFILE>\cv1`, `<USERPROFILE>\cv2`.
`cv3` is **not** present on this machine.

## Live URLs (all HTTP 200)

| Repo | Root | Language prefixes |
|---|---|---|
| `yd7148/cv1` | https://yd7148.github.io/cv1/ | none — root is Chinese |
| `yd7148/cv2` | https://yd7148.github.io/cv2/ | none — root is Chinese |
| `yd7148/cv3` | https://yd7148.github.io/cv3/ | `/zh/` and `/en/` still live |

Verified route responses for cv1 and cv2 (both 200): `/`, `/works/`, `/resume/`,
`/about/`, `/notes/`, `/contact/`, `/en/`, `/en/works/`.

For cv3: `/` 200 (redirect page), `/zh/` 200, `/en/` 200, `/works/` 404, `/resume/` 404.

## Internal link audit (live)

- cv1: 19 internal links crawled, all 200
- cv2: 20 internal links crawled, all 200
- No `/zh/` links remain in cv1 or cv2

## Deployment

All three repos deploy through **GitHub Actions on push to `main`**:

```
workflow name : Deploy to GitHub Pages
event         : push
conclusion    : success
```

`gh-pages` manual deploy still exists in the scripts but Pages source is Actions,
so it does not publish.

## Stack

Astro `^7.0.3`, Tailwind CSS `^4.3.2`, Node `>=22.12.0` (cv1 and cv2).

## Repo rename history

| Old | New | Renamed |
|---|---|---|
| `yd7148` | `cv1` | 2026-09-28 |
| `yd7148-v2` | `cv2` | 2026-09-28 |
| `yd7148-v3` | `cv3` | 2026-09-28 |

The GitHub API follows the rename, but **GitHub Pages URLs do not** — the old
`/yd7148-v2/` style paths are gone with no redirect.

## Related repositories

- `yd7148/CV` — **private**, `has_pages = false`. This is the Resume 01 site
  (`work/personal-site`, `work/cv-<USER_2>-deploy-v1`), published to Cloudflare
  Workers at https://cv.4pins.workers.dev/ — **not** GitHub Pages. See the
  `resume-cloudflare-maintenance` skill.
- `yd7148/yd7148` — the GitHub **profile** repository (name must equal the
  username for the README to render on the Overview tab). Created 2026-10-02;
  contains only the profile README plus a contribution-snake workflow.
- `yd7148/OpenCode_skill` — **private**. Skill library; 35 skills, in sync with
  the local `~/.config/opencode/skills/` directory.

## Privacy posture

`/resume/` is the only page that exposes personal data and it is `noindex`.
Public HTML passes the `npm run verify:build` privacy gate (0 leaks).
