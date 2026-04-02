---
# school_menu-vks6
title: 'Fix CI workflow: self-hosted runner and auto-deploy via Coolify'
status: completed
type: task
priority: normal
created_at: 2026-04-02T05:35:47Z
updated_at: 2026-04-02T18:36:48Z
---

Issue #216 - Fix tests.yaml runner label and add deploy job on push to main

## Summary of Changes

- Fixed Forgejo runner on VPS: added group_add for Docker socket permissions, re-registered with new token
- Updated CI workflow runner label from ubuntu-22.04 to ubuntu-latest
- Added .gitea/workflows/deploy.yml for automatic Coolify deploy on push to main
- Added COOLIFY_WEBHOOK_URL and COOLIFY_WEBHOOK_TOKEN secrets to Codeberg
- Diagnosed and fixed production issue: Umami analytics script (analytics.local.webbografico.com) was blocking browser, causing htmx day buttons to appear unresponsive
