---
name: cloudflare-platform
description: Use when building or deploying on Cloudflare's core platform — Workers, Pages, KV, R2, D1, AI, or networking primitives.
license: MIT
---

# Cloudflare Platform

## When to Use This Skill
- Creating a Cloudflare Worker for serverless compute
- Deploying a static site or full-stack app with Pages
- Using KV, R2, or D1 for storage and database needs
- Running ML inference with Workers AI or Vectorize for embeddings
- Configuring networking features (Routes, Custom Domains, Hyperdrive)

## Workflow
1. Determine the workload type: compute (Worker), static/full-stack (Pages), storage (KV/R2/D1), or AI (Workers AI/Vectorize)
2. Scaffold the project with `wrangler init` or create the resource via the Cloudflare dashboard
3. Configure `wrangler.toml` with bindings, routes, and environment variables
4. Implement the Worker or Pages function, referencing bindings from `env`
5. Run locally with `wrangler dev` and verify behavior
6. Deploy with `wrangler deploy` or connect the Pages repo for automatic deploys
7. Verify in the Cloudflare dashboard that the resource is active and metrics look correct

## Rules
- Use `wrangler.toml` for all configuration — never inline secrets in code
- Keep Worker scripts under the subrequest limit (50 subrequests per invocation)
- Prefer R2 over KV for large objects (>25 MB) and binary data
- Use D1 for relational queries; use KV for simple key-value lookups
- Never log sensitive request data — use `console.log` only for debugging in dev
