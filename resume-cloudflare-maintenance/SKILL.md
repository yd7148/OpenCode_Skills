---
name: resume-cloudflare-maintenance
description: 維護劉士禎的 Resume 01 個人履歷網站與 Cloudflare Workers 靜態部署；用於本專案更新中英內容、保留舊版、建立發布副本、調整 workers.dev 網址或還原。不是通用網站建置 Skill。
license: MIT
---

# Resume 01 maintenance

## Locate the project

Current Windows project root:
`<USERPROFILE>\Documents\Codex\2026-09-26\https-codotx-com-news-claude-code`

Read [references/project-state.md](references/project-state.md) for known paths and deployment state. Verify them before acting; the user may move the project or change the domain.

Current live URL is **https://cv.4pins.workers.dev/** (Worker `cv`, account subdomain `<USER_2>`).
Earlier records naming `resume01-trial` / `resume01-deploy-v1` are superseded; that subdomain no longer resolves and does not redirect.

For a full user-facing maintenance guide, read `outputs/Resume01-維護手冊與完整操作紀錄.md` under the project root. Do not copy authentication token contents into documents, tool output, archives or Git.

## Preserve the distinction between source and release

- Astro source lives in `work/personal-site`. Resume view is `src/components/ResumeInspired.astro`; shared profile is `src/data/profile.ts`.
- The live site's deployable snapshot lives in `work/cv-<USER_2>-deploy-v1/site`, with its own Wrangler config one level above. `work/resume01-deploy-v1` is a retained older snapshot and is no longer the release source.
- Source edits do not update the release snapshot or the live website. Direct snapshot edits do not update Astro source.
- **GitHub auto-deployment is active** via the Cloudflare GitHub integration, authorized for `yd7148/CV` only: branch `main`, root directory `work/cv-4pins-deploy-v1`, deploy command `npx --yes wrangler@4.142.0 deploy`, website directory `site/`. A push to `main` publishes whatever is in that `site/` folder — it does **not** build the Astro source.
- User prefers previous designs/files preserved. Create dated editing/release copies for new variants; do not overwrite earlier snapshots. Shared profile edits affect multiple previews: scope changes deliberately.
- Do not deploy from personal-site's old Wrangler configuration: it targets `cv` and all `dist` output, unlike the selected standalone resume.

## Update workflow

1. Establish whether the request is documentation, local preview, release, domain change or rollback. A maintenance question alone is not authorization to publish or change the domain.
2. Inspect applicable AGENTS.md and actual current files. Save a timestamped copy of the affected source, release `site`, and config before changing them.
3. Edit a separate source/preview copy when preservation is required. Keep English and Traditional Chinese consistent; leave unavailable certificates/project links pending instead of inventing them.
4. Build to a new output directory using `astro build --outDir <new-directory>`. Set ASTRO_TELEMETRY_DISABLED=1. Follow the project's background-mode dev-server instructions.
5. Extract only `previews/resume/index.html` as release `site/index.html` and its actual referenced assets. Follow CSS URLs/imports and any JS/image/font dependencies when present; today's single CSS is not a permanent assumption. Never upload the complete multi-template output or repository.
6. Adjust preview-gallery links to the published homepage in the release copy. Preserve robots.txt and _headers unless changing indexing was requested.
7. Preview the actual release bundle; check layout, anchors, theme toggle, mobile overflow, new asset links and print behavior when affected.
8. If deployment is requested, use the new release folder's intended Worker config. Run whoami, dry-run, then deploy. Record URL and version ID. Confirm HTML/CSS HTTPS responses and browser behavior.
9. Update the local deployment record with changed paths, scope, version, public URL and verified results. A successful upload alone does not prove the URL works.

## Cloudflare details that matter

- This project is **not** published on GitHub Pages. `yd7148/CV` is a private repository with Pages disabled, so `https://yd7148.github.io/CV/` always 404s and never has existed. A GitHub Pages path is derived from the repository name and is unrelated to the Worker URL. Do not offer it as an alternative entry point.
- Known working CLI: Wrangler 4.142.0. Check current official docs when changing commands, domains or hosting features.
- Known sufficient explicit login scopes for this static deployment: `account:read user:read workers:write workers_scripts:write`. `offline_access` was automatically added by OAuth; passing it explicitly to --scopes failed. Missing unrelated default scopes did not prevent deployment.
- If login is needed, start the official login flow, let the user sign in and grant authorization, then verify whoami. Expired flows need a fresh URL. Never preserve OAuth links as reusable instructions.
- First deployment auto-registered an account subdomain from the working directory. For future sites, inspect the account subdomain before publishing and do not assume an earlier proposed name was registered.
- URL format is `<worker-name>.<account-subdomain>.workers.dev`. Changing config `name` may deploy a different Worker; inspect collisions first. Changing account subdomain affects other Workers in the account. Never present it as merely editing page title.
- Keep the old Worker when creating a newly named trial unless user requests otherwise. Do not assume the old URL redirects.
- First HTTPS access briefly failed, then succeeded after propagation. Retry normally after a short interval; do not disable TLS verification or bypass security warnings. Persistent errors need diagnosis.
- robots/noindex do not make the site private. Publish only the selected public content; additional private attachments need their own intended publication scope.
- For restoration, redeploy a verified archived site with the intended same Worker config, or inspect Cloudflare's currently supported rollback options. Preserve the faulty release for diagnosis.

## Official references

- [Static Assets](https://developers.cloudflare.com/workers/static-assets/)
- [workers.dev naming](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/)
- [Pricing and limitations](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/)
- [Rollbacks](https://developers.cloudflare.com/workers/versions-and-deployments/rollbacks/)
